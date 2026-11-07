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

First run (before cleaning): 76 PDF pages produced 271 chunks. After cleaning and skipping the publisher’s notice: 74 English pages produced 252 chunks (41 to 180 words, median 180), only page 10 skipped as Afrikaans, and no leftover headers or Afrikaans-looking chunks.

Problems found by inspecting the output, and how they were handled:

| Problem | Handling |
|---------|----------|
| The Gazette's running header ("No. 37067 GOVERNMENT GAZETTE, 26 November 2013 Act No. 4 of 2013 ...") appears on every page and would pollute retrieval | Removed with a targeted pattern; the script reports any chunks that still contain it |
| Ligatures such as "ﬁ" in the extracted text | Normalised to plain letters (Unicode NFKC) |
| Page 1 is the publisher's notice, not part of the Act | Skipped |
| The PDF also contains Afrikaans pages (running header "Wet No. 4 van 2013"), which English questions cannot match | Detected by their header and excluded; the script reports how many pages were skipped and checks that no Afrikaans-looking chunks remain |
| Page numbers had two possible meanings (PDF index vs printed number) | chunks store both; evaluation uses printed numbers |

Known limitations of the chunking:

- Chunks are built per page, so a passage that crosses a page break is split in two.
- Each chunk stores both the PDF page index (page) and the printed Gazette page number (printed_page). Gold labels in the evaluation set and citations use the printed Gazette numbers.

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

**H1**: Embedding-based retrieval will achieve a Hit@3 score at least 5 percentage points higher than TF-IDF, while the difference in Hit@5 will be smaller (approximately 0–5 percentage points).
Reason: Embeddings should capture semantic similarity between questions and legal passages even when they use different wording. However, TF-IDF may still retrieve relevant passages within a larger candidate set through shared legal terminology.
Judged by: Hit@3 and Hit@5, reported as percentage-point differences between methods.

**H2**: TF-IDF will perform better on questions using terminology close to the Act's wording, while embeddings will perform better on everyday paraphrased questions. The difference between methods will be larger for paraphrased questions than for Act-wording questions.
Reason: TF-IDF relies heavily on lexical overlap, which should benefit questions containing terms such as "responsible party", "personal information" and "lawful processing". Embeddings should be more capable of matching everyday language to the underlying legal concepts.
Judged by: Hit@3 and MRR, calculated separately for Act-wording and paraphrased questions.

**H3**: Neither retrieval method will consistently retrieve both gold pages for multi-page questions. Embeddings will retrieve both pages for at least 50% of these questions at k=5, compared with at least 35% for TF-IDF.
Reason: Multi-page questions require retrieving passages that cover different parts of a legal requirement. Semantic similarity may help identify conceptually related passages, but separate page-level chunks can make it difficult to retrieve all required pages together.
Judged by: Multi-page coverage@5: the percentage of multi-page questions for which all gold pages appear among the top five retrieved chunks.

**H4**: Questions whose answers depend on information split across consecutive PDF pages will have lower Hit@3 scores than questions whose answers are contained within a single page, for both retrieval methods.
Reason: The page-based chunking strategy separates text at page boundaries. A question requiring context from the end of one page and the beginning of another may not match either chunk strongly enough on its own.
Judged by: Hit@3 for boundary-dependent questions versus single-page questions, reported separately for TF-IDF and embeddings.

**H5**: Out-of-scope questions will have lower top-1 similarity scores on average than in-scope questions for both retrieval methods, but the two score distributions will overlap.
Reason: Some out-of-scope questions may share general legal or privacy terminology with POPIA, even though the Act does not answer them. This could produce relatively high similarity scores despite the question being outside the document's scope.
Judged by: Mean and median top-1 scores for in-scope and out-of-scope questions, and the degree of overlap between their score distributions.

**H6**: Retrieval failures will be more common for multi-section questions and questions requiring legal definitions or cross-references than for straightforward questions about a single provision.
Reason: Questions involving several provisions require the retriever to identify multiple relevant passages. Questions involving definitions and cross-references may also use wording that differs substantially from the relevant passage.
Judged by: Hit@3 and MRR grouped by question type, supported by manual examination of failed retrievals.

## Measurement definitions (fixed before running retrieval)

- **Hit@k:** at least one gold page appears among the printed pages of the top-k chunks (chunk-level, k = 1, 3, 5).
- **MRR:** mean of 1/rank, where rank is the position of the first chunk on a gold page, over in-scope questions.
- **Coverage@5:** for multi-page questions, all gold pages appear among the top 5 chunks.
- **Boundary-dependent question (H4):** a question whose gold pages include two consecutive PDF pages.
- **Question type (H6):** labelled by the author before retrieval: `single`, `multi-section` or `definition-xref`.
- **Score comparison (H5):** top-1 similarity compared within each method; overlap measured by AUC for separating in-scope from out-of-scope questions, and by the share of out-of-scope questions scoring above the in-scope median.
- **Sample size:** 30 in-scope questions (each worth 3.3 points), 7 multi-page, 7 out-of-scope. Differences of one or two questions are treated as noise; paired bootstrap intervals are reported for H1.
- **Grading:** a hypothesis is *confirmed* if every numeric or directional claim holds, *partly confirmed* if some do, and *refuted* otherwise. "Consistently" in H3 means 100% coverage.

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
