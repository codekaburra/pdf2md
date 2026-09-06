"""Undo pymupdf4llm's code formatting around CJK prose.

CJK fonts are genuinely fixed-width, so their spans carry the monospaced
font flag. pymupdf4llm equates monospaced with code, which leaves every
Chinese/Japanese/Korean run wrapped in backticks: an LLM then reads prose
as identifiers, and the extra markup inflates exactly the token count this
tool exists to cut. pymupdf4llm's own ``ignore_code`` only suppresses
fenced blocks, not inline spans, so the unwrapping happens here instead.

Pure text functions — no PDF dependency.
"""

import re
from typing import List, Match

# Kana, CJK ideographs (incl. extension A and compatibility), and hangul.
# A span needs one of these to count as CJK; CJK punctuation alone is not
# enough to justify unwrapping.
_CJK_RE = re.compile("[぀-ヿ㐀-䶿一-鿿豈-﫿가-힯]")

_ASCII_LETTER_RE = re.compile(r"[A-Za-z]")
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_FENCE_RE = re.compile(r"^\s{0,3}(?:```|~~~)")


def _is_cjk_prose(text: str) -> bool:
    """True for CJK text carrying no ASCII identifiers.

    The ASCII-letter test is what keeps real code intact: a snippet like
    ``print("...")`` stays fenced, while a run of bare CJK prose does not.
    """
    return bool(_CJK_RE.search(text)) and not _ASCII_LETTER_RE.search(text)


def _unwrap_span(match: Match) -> str:
    content = match.group(1)
    return content if _is_cjk_prose(content) else match.group(0)


def unwrap_cjk_code(md: str) -> str:
    """Strip code markup that only exists because the font was monospaced."""
    out: List[str] = []
    fence = ""  # opening fence line; empty when outside a fenced block
    block: List[str] = []

    for line in md.splitlines():
        if fence:
            if _FENCE_RE.match(line):
                if _is_cjk_prose("\n".join(block)):
                    out.extend(block)  # drop both fence lines
                else:
                    out.append(fence)
                    out.extend(block)
                    out.append(line)
                fence, block = "", []
            else:
                block.append(line)
            continue
        if _FENCE_RE.match(line):
            fence = line
            continue
        out.append(_INLINE_CODE_RE.sub(_unwrap_span, line))

    if fence:  # unterminated fence: emit verbatim rather than guess
        out.append(fence)
        out.extend(block)
    return "\n".join(out)
