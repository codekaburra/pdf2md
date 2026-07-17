# pdf2md

A PDF → Markdown converter built for feeding documents to LLMs (Ollama, Claude, etc.) without wasting tokens.

## Why

Feeding a raw PDF to an AI model is expensive in tokens. Converting to clean Markdown first gives you:

- Much lower token usage (no layout noise, repeating headers/footers, or page numbers)
- Better model comprehension — LLMs are trained on huge amounts of Markdown
- Complex tables preserved as inline HTML `<table>` by pymupdf4llm, so structure isn't lost

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
# Basic conversion: produces report.md
pdf2md report.pdf

# Custom output path
pdf2md report.pdf -o docs/report.md

# Convert a subset of pages (1-based)
pdf2md report.pdf --pages 1-10
pdf2md report.pdf --pages 1,3,5-7

# Keep headers/footers (by default, repeating headers, footers, and
# page numbers are filtered out automatically)
pdf2md report.pdf --keep-headers
```

## Batch conversion

`pdf2md` only takes one input file at a time. To convert every PDF in a
folder, loop over them with the shell:

```bash
cd /path/to/your/pdf/folder
for f in *.pdf; do
  pdf2md "$f" --chunks
done
```

How it works:

- `for f in *.pdf; do ... done` — bash loop syntax. `*.pdf` expands to every
  `.pdf` filename in the current directory; each iteration sets `f` to one of
  them.
- `pdf2md "$f" --chunks` — the actual conversion call, using `$f` (the
  current filename) as input. Always quote `"$f"` — an unquoted variable
  breaks on filenames containing spaces.
- Each output `.md` (and `.chunks.json`) is written next to its source PDF,
  named after it.

If you didn't activate the virtualenv (see [Install](#install)), call the
binary by its full path instead: `/path/to/pdf2md/.venv/bin/pdf2md`.

## `--chunks`: split by heading

If the end goal is LLM Q&A (stuffing context directly or building a RAG index),
add `--chunks` to also emit `report.chunks.json`, which splits the document
along Markdown headings into breadcrumb-tagged pieces:

```bash
pdf2md report.pdf --chunks
# or cap each chunk's size (oversized chunks split at paragraph boundaries)
pdf2md report.pdf --chunks --max-chars 2000
```

Output format:

```json
[
  {
    "path": "User Guide > 2. Settings > 2.1 Advanced",
    "heading": "2.1 Advanced",
    "level": 3,
    "content": "Advanced content...",
    "chars": 600
  }
]
```

At query time you only feed the relevant chunks into the prompt instead of the
whole document, saving a large share of tokens. For RAG, embed each chunk directly.

## CJK documents

CJK fonts are fixed-width, so pymupdf4llm's monospace-means-code rule wraps
every Chinese/Japanese/Korean run in backticks. `pdf2md` undoes this
automatically: prose comes out as prose, while spans holding ASCII
identifiers (`CSV`, `print("...")`) stay marked as code. No flag needed.

## Known limitations

- **Scanned PDFs**: no text layer, no conversion — see below.
- **Wrapped table cells lose a space**: when a cell's text wraps, pymupdf4llm
  joins the lines without one, so `Sheung Shui` can come out as `SheungShui`.
  Affects table-heavy documents; the text is present, just run together.
- **Heading detection is font-size based**: documents whose body text is set
  at heading size (common in short CJK spec sheets) may promote paragraphs to
  headings, which in turn coarsens `--chunks` output.

## Limitation: scanned (image-only) PDFs

This tool does **not** perform OCR. A scanned PDF with no text layer will error
out (exit code 2). Add a text layer first with
[ocrmypdf](https://ocrmypdf.readthedocs.io/), then convert:

```bash
ocrmypdf scanned.pdf ocred.pdf
pdf2md ocred.pdf
```

## Development

```bash
pip install -e ".[dev]"
pytest
```
