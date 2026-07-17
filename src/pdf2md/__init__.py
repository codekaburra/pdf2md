"""pdf2md — PDF → Markdown converter for LLM consumption."""

__version__ = "0.1.0"

from pdf2md.converter import ScannedPDFError, convert
from pdf2md.chunker import chunk_markdown

__all__ = ["convert", "chunk_markdown", "ScannedPDFError", "__version__"]
