import json
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

PDF = Path("data/raw/popia.pdf")
OUT = Path("data/chunks.jsonl")
CHUNK_WORDS, OVERLAP = 180, 40
SKIP_PAGES = {1}   # PDF page numbers to leave out (publisher's notice / cover); check the first pages

# The Gazette repeats a running header on every page, often preceded by the printed page number.
# Spacing in the extracted text varies (sometimes none), hence \s* between the pieces.
HEADER = re.compile(
    r"(?:\d{1,3}\s*)?No\.\s*37067\s*GOVERNMENT GAZETTE,\s*26 November 2013\s*"
    r"Act No\.\s*4 of 2013\s*Protection of Personal Information Act,\s*2013",
    re.IGNORECASE,
)
# The PDF also contains Afrikaans pages; their running header is in Afrikaans. English questions
# cannot be answered from them, so they are excluded.
AFRIKAANS_HEADER = re.compile(r"Wet\s*No\.\s*4\s*van\s*2013", re.IGNORECASE)
# The printed Gazette page number is the digits just before "No. 37067" in the running header
PRINTED_PAGE = re.compile(r"(?<!\d)(\d{1,3})\s*No\.\s*37067\s*GOVERNMENT GAZETTE", re.IGNORECASE)

AFRIKAANS_WORDS = {"die", "en", "wat", "moet", "nie", "vir", "deur", "sal", "word", "kan", "dat",
                   "wanneer", "verantwoordelike", "inligting", "persoonlike", "reguleerder"}
ENGLISH_WORDS = {"the", "and", "that", "shall", "which", "with", "any", "such", "be", "by", "must"}


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)  # turns ligatures such as "ﬁ" back into "fi"
    text = re.sub(r"-\n(?=\w)", "", text)       # re-join words hyphenated across lines
    return re.sub(r"\s+", " ", text).strip()


def clean(text: str) -> str:
    return HEADER.sub("", normalise(text)).strip()   # drop the English running page header


def printed_page(text: str) -> int | None:
    m = PRINTED_PAGE.search(normalise(text))
    return int(m.group(1)) if m else None


def looks_afrikaans(text: str) -> bool:
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return sum(w in AFRIKAANS_WORDS for w in words) > sum(w in ENGLISH_WORDS for w in words)


def page_texts(path: Path) -> tuple[list[tuple[int, int | None, str]], list[int]]:
    """Return ([(pdf_page, printed_page, text)], [afrikaans pages that were skipped])."""
    reader = PdfReader(str(path))
    pages, afrikaans = [], []
    for i, p in enumerate(reader.pages):
        number = i + 1
        if number in SKIP_PAGES:
            continue
        raw = p.extract_text() or ""
        text = clean(raw)
        if AFRIKAANS_HEADER.search(text):
            afrikaans.append(number)
            continue
        pages.append((number, printed_page(raw), text))
    return pages, afrikaans


def split_words(words: list[str], size: int, overlap: int):
    """Overlapping windows of `size` words; consecutive windows share `overlap` words."""
    for start in range(0, max(len(words) - overlap, 1), size - overlap):
        yield words[start:start + size]


def build_chunks(pages: list[tuple[int, int | None, str]]) -> list[dict]:
    chunks = []
    for pdf_page, printed, text in pages:
        for piece in split_words(text.split(), CHUNK_WORDS, OVERLAP):
            if piece:
                chunks.append({"id": len(chunks), "page": pdf_page, "printed_page": printed,
                               "text": " ".join(piece)})
    return chunks


def main() -> None:
    pages, afrikaans = page_texts(PDF)
    empty = [n for n, _, t in pages if not t]
    chunks = build_chunks(pages)

    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    sizes = [len(c["text"].split()) for c in chunks]
    print(f"{len(pages)} English pages kept -> {len(chunks)} chunks "
          f"(words per chunk: min {min(sizes)}, median {sorted(sizes)[len(sizes) // 2]}, max {max(sizes)})")
    print(f"Skipped {len(afrikaans)} Afrikaans pages: {afrikaans}")
    print(f"Chunks still containing the Gazette header: {sum('GOVERNMENT GAZETTE' in c['text'] for c in chunks)}")
    print(f"Chunks that still look Afrikaans: {sum(looks_afrikaans(c['text']) for c in chunks)}")
    no_printed = [n for n, pr, _ in pages if pr is None]
    mapping = {n: pr for n, pr, _ in pages if pr is not None}
    printed_values = sorted(mapping.values())
    print(f"Printed Gazette pages found for {len(mapping)} of {len(pages)} pages "
          f"(range {printed_values[0]}-{printed_values[-1]})" if mapping else "No printed page numbers found")
    print("PDF page -> printed page, first five:", list(mapping.items())[:5])
    if no_printed:
        print(f"WARNING: no printed page number found for PDF pages {no_printed[:10]}")
    if empty:
        print(f"WARNING: {len(empty)} pages had no extractable text (scanned images?): {empty[:10]}")
    print("\nThree sample chunks:")
    for c in chunks[:: max(len(chunks) // 3, 1)][:3]:
        print(f"\n[chunk {c['id']}, page {c['page']}] {c['text'][:300]}...")


if __name__ == "__main__":
    main()