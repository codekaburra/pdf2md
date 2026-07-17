"""PDF → Markdown conversion built on pymupdf4llm."""

import re
from typing import List, Optional, Sequence

import pymupdf
import pymupdf4llm

from pdf2md.cleaner import clean_pages

# A page needs at least this many extracted characters to count as "has text".
_TEXT_PAGE_MIN_CHARS = 30

# If fewer than this fraction of pages have text, treat the PDF as scanned.
_TEXT_PAGE_RATIO = 0.2

# pymupdf4llm appends a horizontal-rule page separator at the end of each page.
_TRAILING_RULE_RE = re.compile(r"(?:\n|^)-{3,}\s*$")


class ScannedPDFError(Exception):
    """Raised when a PDF appears to have no usable text layer."""


def convert(
    pdf_path: str,
    *,
    pages: Optional[Sequence[int]] = None,
    filter_headers: bool = True,
) -> str:
    """Convert a PDF to markdown.

    ``pages`` is a sequence of 0-based page numbers, or None for all pages.
    Raises ScannedPDFError if the PDF looks like a scan without a text layer.
    """
    doc = pymupdf.open(pdf_path)
    try:
        if doc.needs_pass:
            raise ValueError("PDF is password-protected; decrypt it first")
        if pages is None:
            page_numbers = list(range(doc.page_count))
        else:
            page_numbers = list(pages)
            bad = [p for p in page_numbers if not 0 <= p < doc.page_count]
            if bad:
                raise ValueError(
                    f"page(s) out of range: {[p + 1 for p in bad]} "
                    f"(document has {doc.page_count} pages)"
                )
        _ensure_text_layer(doc, page_numbers)
        data = pymupdf4llm.to_markdown(doc, pages=page_numbers, page_chunks=True)
    finally:
        doc.close()

    page_md = [_strip_trailing_rule(item["text"]) for item in data]
    if filter_headers:
        page_md = clean_pages(page_md)
    body = "\n\n".join(page for page in page_md if page.strip()).strip()
    return body + "\n" if body else ""


def _ensure_text_layer(doc: "pymupdf.Document", page_numbers: List[int]) -> None:
    if not page_numbers:
        return
    text_pages = sum(
        1
        for p in page_numbers
        if len(doc[p].get_text().strip()) >= _TEXT_PAGE_MIN_CHARS
    )
    if text_pages / len(page_numbers) < _TEXT_PAGE_RATIO:
        raise ScannedPDFError(
            "This PDF appears to be scanned (no usable text layer). "
            "Run OCR first, e.g.: ocrmypdf input.pdf output.pdf "
            "— then convert the OCR'd file."
        )


def _strip_trailing_rule(page_text: str) -> str:
    return _TRAILING_RULE_RE.sub("", page_text.rstrip()).rstrip()
