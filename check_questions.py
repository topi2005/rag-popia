import json
import sys
from pathlib import Path

import pandas as pd

CHUNKS = Path("data/chunks.jsonl")
QUESTIONS = Path("eval/questions.csv")


def main() -> int:
    df = pd.read_csv(QUESTIONS, dtype=str, keep_default_na=False)
    missing = [c for c in ("question", "pages", "in_scope") if c not in df.columns]
    if missing:
        print(f"Missing columns {missing}; found {list(df.columns)}. "
              "If a question contains a comma, wrap it in double quotes.")
        return 1

    with open(CHUNKS, encoding="utf-8") as f:
        kept_pages = {json.loads(line)["page"] for line in f}

    problems, multi_page, covered = [], 0, set()
    for i, r in df.iterrows():
        row = i + 2                                   # +1 for the header, +1 for 1-based rows
        question, pages, scope = r["question"].strip(), r["pages"].strip(), r["in_scope"].strip().lower()
        if not question:
            problems.append(f"row {row}: empty question")
        if scope not in {"yes", "no"}:
            problems.append(f"row {row}: in_scope must be 'yes' or 'no', got '{r['in_scope']}'")

        nums = []
        for tok in filter(None, (t.strip() for t in pages.split(";"))):
            try:
                nums.append(int(tok))
            except ValueError:
                problems.append(f"row {row}: page '{tok}' is not a whole number")
        if scope == "yes" and not nums:
            problems.append(f"row {row}: in-scope question has no page")
        if scope == "no" and nums:
            problems.append(f"row {row}: out-of-scope question should have an empty pages column")
        for n in nums:
            if n not in kept_pages:
                problems.append(f"row {row}: page {n} has no chunks (skipped page, Afrikaans page, or out of range)")
        if scope == "yes":
            multi_page += len(nums) > 1
            covered.update(nums)

    duplicates = df["question"].str.strip().str.lower().duplicated()
    for i in df.index[duplicates]:
        problems.append(f"row {i + 2}: duplicate question")

    scopes = df["in_scope"].str.strip().str.lower()
    n_yes, n_no = int((scopes == "yes").sum()), int((scopes == "no").sum())
    print(f"{len(df)} questions: {n_yes} in scope, {n_no} out of scope; "
          f"{multi_page} need more than one page; in-scope answers spread over {len(covered)} distinct pages")
    if n_yes < 25:
        print(f"Note: aim for about 30 in-scope questions (you have {n_yes}).")
    if n_no < 6:
        print(f"Note: aim for 6 to 8 out-of-scope questions (you have {n_no}).")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(" -", p)
        return 1
    print("No format problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
