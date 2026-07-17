"""Split a markdown document into heading-based chunks for RAG / selective
context stuffing.

Pure text functions — no PDF dependency.
"""

import re
from typing import Dict, List

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^\s{0,3}(```|~~~)")


def chunk_markdown(md: str, *, source: str = "", max_chars: int = 0) -> List[Dict]:
    """Split markdown into chunks along ATX headings.

    Each chunk carries a breadcrumb ``path`` built from the heading
    hierarchy, e.g. ``"User Guide > 2. Settings > 2.1 Advanced"``. Content before
    the first heading becomes a chunk titled after ``source`` (or
    ``"(preamble)"``). Headings inside fenced code blocks are ignored.

    If ``max_chars > 0``, oversized chunks are split at paragraph
    boundaries and their paths suffixed with `` (1/2)``, `` (2/2)`` etc.
    A single paragraph longer than ``max_chars`` is never split.
    """
    chunks: List[Dict] = []
    stack: List[Dict] = []  # enclosing headings: {"level": int, "title": str}
    current_heading = source or "(preamble)"
    current_level = 0
    buf: List[str] = []
    in_fence = False

    def flush() -> None:
        content = "\n".join(buf).strip()
        buf.clear()
        if not content:
            return
        path = " > ".join(h["title"] for h in stack) if stack else current_heading
        chunks.append(
            {
                "path": path,
                "heading": current_heading,
                "level": current_level,
                "content": content,
                "chars": len(content),
            }
        )

    for line in md.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            buf.append(line)
            continue
        heading = None if in_fence else _HEADING_RE.match(line)
        if heading is None:
            buf.append(line)
            continue
        flush()
        level = len(heading.group(1))
        title = heading.group(2).strip()
        while stack and stack[-1]["level"] >= level:
            stack.pop()
        stack.append({"level": level, "title": title})
        current_heading = title
        current_level = level
    flush()

    if max_chars > 0:
        split = []
        for chunk in chunks:
            split.extend(_split_chunk(chunk, max_chars))
        chunks = split
    return chunks


def _split_chunk(chunk: Dict, max_chars: int) -> List[Dict]:
    if chunk["chars"] <= max_chars:
        return [chunk]

    paragraphs = chunk["content"].split("\n\n")
    parts: List[str] = []
    current: List[str] = []
    current_len = 0
    for para in paragraphs:
        added = len(para) + (2 if current else 0)
        if current and current_len + added > max_chars:
            parts.append("\n\n".join(current))
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += added
    if current:
        parts.append("\n\n".join(current))

    if len(parts) <= 1:
        return [chunk]
    result = []
    for i, part in enumerate(parts, 1):
        piece = dict(chunk)
        piece["path"] = f"{chunk['path']} ({i}/{len(parts)})"
        piece["content"] = part
        piece["chars"] = len(part)
        result.append(piece)
    return result
