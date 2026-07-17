"""Strip repeating page headers/footers and standalone page-number lines.

Pure text functions — no PDF dependency, so everything here is unit-testable
with plain strings.
"""

import math
import re
from collections import Counter
from typing import List, Set, Tuple

# How many non-empty lines at the top/bottom of a page count as the
# header/footer region (both for candidate collection and for stripping).
_REGION_LINES = 3

# Repeat-based detection only kicks in with at least this many pages.
_MIN_PAGES_FOR_REPEAT = 4

# A normalized line must appear on at least this fraction of pages
# (and on at least 3 pages) to be treated as a repeating header/footer.
_REPEAT_RATIO = 0.4

# Lines that only repeat once digits are masked (e.g. "12 | ACME Report")
# must be short to qualify — long lines differing only in numbers are far
# more likely to be content (list items, data rows) than running headers.
_MAX_MASKED_LEN = 80

# Placeholder for digit runs during normalization. Must not collide with
# characters that appear naturally in markdown lines (e.g. "#").
_DIGIT_MASK = "�"

# Standalone page-number lines: "12", "- 12 -", "Page 12", "Page 12 of 30",
# "12 / 30", "第 12 頁", optionally wrapped in dashes/underscores/asterisks.
_PAGE_NUMBER_RE = re.compile(
    r"""^[\s\-–—~*_]*
        (?:page|p\.|第)?\s*
        \d+
        (?:\s*(?:/|of|之)\s*\d+)?
        \s*(?:頁|页)?
        [\s\-–—~*_]*$""",
    re.IGNORECASE | re.VERBOSE,
)


def _normalize(line: str) -> str:
    """Collapse whitespace and mask digit runs so 'Page 3' == 'Page 27'."""
    return re.sub(r"\d+", _DIGIT_MASK, " ".join(line.split())).lower()


def _region_indices(lines: List[str]) -> Tuple[List[int], List[int]]:
    """Indices of the first/last few non-empty lines of a page."""
    non_empty = [i for i, ln in enumerate(lines) if ln.strip()]
    return non_empty[:_REGION_LINES], non_empty[-_REGION_LINES:]


def _repeating(region_sets: List[Set[str]], threshold: int) -> Set[str]:
    counts: Counter = Counter()
    for keys in region_sets:
        for key in keys:
            if key:
                counts[key] += 1
    return {key for key, count in counts.items() if count >= threshold}


def _matches(line: str, keys: Set[str]) -> bool:
    if _PAGE_NUMBER_RE.match(line):
        return True
    key = _normalize(line)
    if key not in keys:
        return False
    return _DIGIT_MASK not in key or len(key) <= _MAX_MASKED_LEN


def _strip_edges(lines: List[str], header_keys: Set[str], footer_keys: Set[str]) -> List[str]:
    """Peel matching lines off the top and bottom edges only.

    Stripping stops at the first non-matching line, so a repeated-looking
    line in the middle of the page body is never touched.
    """
    result = list(lines)
    for _ in range(_REGION_LINES):
        first = next((i for i, ln in enumerate(result) if ln.strip()), None)
        if first is None or not _matches(result[first], header_keys):
            break
        del result[: first + 1]
    for _ in range(_REGION_LINES):
        last = next(
            (i for i in range(len(result) - 1, -1, -1) if result[i].strip()), None
        )
        if last is None or not _matches(result[last], footer_keys):
            break
        del result[last:]
    return result


def clean_pages(pages: List[str]) -> List[str]:
    """Remove repeating headers/footers and page-number lines from each page.

    Repeat-based removal needs >= 4 pages; page-number lines at the very
    top/bottom edges are stripped regardless of page count.
    """
    pages_lines = [page.splitlines() for page in pages]

    header_keys: Set[str] = set()
    footer_keys: Set[str] = set()
    if len(pages) >= _MIN_PAGES_FOR_REPEAT:
        top_sets = []
        bottom_sets = []
        for lines in pages_lines:
            top_idx, bottom_idx = _region_indices(lines)
            top_sets.append({_normalize(lines[i]) for i in top_idx})
            bottom_sets.append({_normalize(lines[i]) for i in bottom_idx})
        threshold = max(3, math.ceil(len(pages) * _REPEAT_RATIO))
        header_keys = _repeating(top_sets, threshold)
        footer_keys = _repeating(bottom_sets, threshold)

    return [
        "\n".join(_strip_edges(lines, header_keys, footer_keys)).strip()
        for lines in pages_lines
    ]
