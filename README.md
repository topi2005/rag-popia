# POPIA Question-Answering Assistant (RAG demo)

A small retrieval-augmented question-answering system over the **Protection of Personal Information Act, 2013 (Act No. 4 of 2013)**. It is designed to answer only from the text of the Act, cite the page it used, and refuse when the Act does not contain the answer.

The point of the project is not a clever chatbot but a measured one: retrieval and answers are evaluated against questions written from the Act itself, including questions the Act cannot answer.

## Status

| Step | What | Status |
|------|------|--------|
| 1 | Ingest the Act and split it into chunks | Done |
| 2 | Retrieval: TF-IDF baseline vs sentence embeddings, evaluated on a hand-written question set | Planned |
| 3 | Generation with page citations and a refusal rule | Planned |
| 4 | Evaluation, error analysis and write-up | Planned |

Results sections below are filled in only as each step is actually run.

## Why this document

- It is **public law**, so no confidential or personal data is involved.
- It is directly relevant to **data governance, privacy and assurance work**.
- It is long and structured enough that retrieval quality actually matters.

## Design principles

1. **Answer only from retrieved text.** The generator receives the retrieved passages and nothing else.
2. **Cite the source.** Every answer names the page(s) it relied on, so a reader can check it.
3. **Refuse when unsupported.** If the retrieved passages do not contain the answer, the system says so instead of guessing.
4. **Measure, don't assume.** Retrieval, citations and refusals are each evaluated on their own.

## Corpus and ingestion

Source: the Act as published in the Government Gazette (26 November 2013), saved locally as `data/raw/popia.pdf` (not committed; see Setup).

`ingest.py` extracts the text page by page, cleans it, and splits it into overlapping chunks of 180 words (40-word overlap), each stored with its PDF page number in `data/chunks.jsonl`.

First run: 76 PDF pages produced 271 chunks (49 to 180 words, median 180).

Problems found by inspecting the output, and how they were handled:

| Problem | Handling |
|---------|----------|
| The Gazette's running header ("No. 37067 GOVERNMENT GAZETTE, 26 November 2013 Act No. 4 of 2013 ...") appears on every page and would pollute retrieval | Removed with a targeted pattern; the script reports any chunks that still contain it |
| Ligatures such as "ﬁ" in the extracted text | Normalised to plain letters (Unicode NFKC) |
| Page 1 is the publisher's notice, not part of the Act | Skipped |

Known limitations of the chunking:

- Chunks are built **per page**, so a passage that crosses a page break is split in two.
- The `page` field is the **PDF page index** (1 to 76), not the printed Gazette page number. Gold labels in the evaluation set use the same PDF page index.

## Evaluation plan

The evaluation set lives in `eval/questions.csv` and is written by the author from the Act:

| Column | Meaning |
|--------|---------|
| `question` | A question a reader might ask |
| `pages` | PDF page number(s) where the answer is found (semicolon-separated); empty for out-of-scope questions |
| `in_scope` | `yes` if the Act answers it, `no` if it does not |

Target: about 30 in-scope questions and 6 to 8 out-of-scope questions.

Metrics:

- **Retrieval:** hit rate at k (does a gold page appear in the top k chunks) and mean reciprocal rank, for TF-IDF and for sentence embeddings.
- **Refusals:** share of out-of-scope questions the system correctly declines, and share of in-scope questions it wrongly declines.
- **Faithfulness:** manual check of whether each answer is supported by the cited page.

## Hypotheses

_To be written by the author before running retrieval, and not edited afterwards._

## Results

_Not yet run._

## Project structure

```
.
├── data/
│   ├── raw/               # popia.pdf (gitignored)
│   └── chunks.jsonl       # produced by ingest.py (gitignored)
├── eval/
│   └── questions.csv      # hand-written evaluation questions
├── results/               # retrieval and answer metrics
├── ingest.py              # PDF -> cleaned, overlapping chunks
├── requirements.txt
└── README.md
```

## Setup and usage

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
source .venv/Scripts/activate      # Windows, Git Bash
pip install -r requirements.txt
mkdir -p data/raw
```

Download the Act as a PDF from the official government publications site, save it as `data/raw/popia.pdf`, then run:

```bash
python ingest.py
```

## Limitations so far

- Per-page chunking splits passages that cross page breaks.
- Citations are PDF page numbers, not section numbers.
- The evaluation set will be small and written by one person.
- This is a demonstration on one public document, not a legal advice tool.

## Notes on AI assistance

This project was built with help from an AI assistant (Claude) for planning and code. All results reported here come from running the code in this repository, and the evaluation questions are written by the author.
