"""Command-line interface: pdf2md input.pdf [-o out.md] [--chunks] ..."""

import argparse
import json
import sys
from pathlib import Path
from typing import List

from pdf2md import __version__
from pdf2md.chunker import chunk_markdown
from pdf2md.converter import ScannedPDFError, convert


def parse_pages(spec: str) -> List[int]:
    """Parse a 1-based page spec like '1,3,5-7' into 0-based page numbers."""
    pages: List[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, _, end_s = part.partition("-")
            start, end = int(start_s), int(end_s)
            if start < 1 or end < start:
                raise ValueError(f"invalid page range: {part!r}")
            pages.extend(range(start - 1, end))
        else:
            page = int(part)
            if page < 1:
                raise ValueError(f"invalid page number: {part!r}")
            pages.append(page - 1)
    if not pages:
        raise ValueError(f"empty page spec: {spec!r}")
    return sorted(set(pages))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="pdf2md",
        description="Convert PDF to Markdown for LLM consumption (token-efficient).",
    )
    parser.add_argument("input", help="input PDF file")
    parser.add_argument("-o", "--output", help="output .md path (default: <input>.md)")
    parser.add_argument(
        "--chunks",
        action="store_true",
        help="also write heading-based chunks to <output>.chunks.json",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=0,
        metavar="N",
        help="split chunks larger than N chars at paragraph boundaries (0 = off)",
    )
    parser.add_argument(
        "--pages",
        metavar="RANGE",
        help="1-based pages to convert, e.g. '1-10' or '1,3,5-7' (default: all)",
    )
    parser.add_argument(
        "--keep-headers",
        action="store_true",
        help="do not filter repeating page headers/footers and page numbers",
    )
    parser.add_argument("--version", action="version", version=f"pdf2md {__version__}")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"pdf2md: file not found: {input_path}", file=sys.stderr)
        return 1
    output_path = Path(args.output) if args.output else input_path.with_suffix(".md")

    try:
        pages = parse_pages(args.pages) if args.pages else None
        markdown = convert(
            str(input_path),
            pages=pages,
            filter_headers=not args.keep_headers,
        )
    except ScannedPDFError as exc:
        print(f"pdf2md: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"pdf2md: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:  # pymupdf.FileDataError etc. on corrupt input
        print(f"pdf2md: cannot read {input_path}: {exc}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    summary = f"wrote {output_path}"

    if args.chunks:
        chunks = chunk_markdown(
            markdown, source=input_path.stem, max_chars=args.max_chars
        )
        chunks_path = output_path.with_suffix(".chunks.json")
        chunks_path.write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        summary += f" and {chunks_path} ({len(chunks)} chunks)"

    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
