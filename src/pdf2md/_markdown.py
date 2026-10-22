"""Fence recognition shared by Markdown text processing."""

import re

_OPENING_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_CLOSING_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")


def opening_fence(line: str) -> str:
    """Return the opening marker, or an empty string for a non-fence line."""
    match = _OPENING_FENCE_RE.match(line)
    if match is None:
        return ""
    marker, info = match.groups()
    if marker[0] == "`" and "`" in info:
        return ""
    return marker


def closes_fence(line: str, marker: str) -> bool:
    """A closing fence must match the marker and be at least as long."""
    match = _CLOSING_FENCE_RE.match(line)
    if match is None:
        return False
    closing = match.group(1)
    return closing[0] == marker[0] and len(closing) >= len(marker)
