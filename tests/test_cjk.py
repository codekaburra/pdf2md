from pdf2md.cjk import unwrap_cjk_code

# Chinese sample data is functional here: these tests exist to prove CJK
# prose is not mistaken for code, so the fixtures have to be real CJK.
_PROSE = "香港島區"
_PROSE2 = "數據規格"


def test_inline_cjk_span_unwrapped():
    md = f"`{_PROSE}` / `{_PROSE2}`"
    assert unwrap_cjk_code(md) == f"{_PROSE} / {_PROSE2}"


def test_inline_span_in_heading_unwrapped():
    assert unwrap_cjk_code(f"# `{_PROSE}` ") == f"# {_PROSE} "


def test_ascii_code_span_preserved():
    md = "Download as `CSV` or `XLSX`."
    assert unwrap_cjk_code(md) == md


def test_mixed_cjk_and_ascii_span_preserved():
    # Real code that happens to contain CJK must stay marked as code.
    md = f'Call `print("{_PROSE}")` to log it.'
    assert unwrap_cjk_code(md) == md


def test_cjk_span_in_table_cell_unwrapped():
    md = f"|`{_PROSE}`|`{_PROSE2}`|"
    assert unwrap_cjk_code(md) == f"|{_PROSE}|{_PROSE2}|"


def test_cjk_fenced_block_unwrapped():
    md = f"```\n{_PROSE}\n{_PROSE2}\n```"
    assert unwrap_cjk_code(md) == f"{_PROSE}\n{_PROSE2}"


def test_ascii_fenced_block_preserved():
    md = '```\n{ "route": "1" }\n```'
    assert unwrap_cjk_code(md) == md


def test_fenced_block_with_any_ascii_preserved():
    # Conservative: one ASCII identifier is enough to keep the fence.
    md = f"```\n{_PROSE}\nrequests.get(url)\n```"
    assert unwrap_cjk_code(md) == md


def test_tilde_fence_honored():
    md = f"~~~\n{_PROSE}\n~~~"
    assert unwrap_cjk_code(md) == _PROSE


def test_inline_spans_inside_fence_untouched():
    md = f"```\n`{_PROSE}` = value\n```"
    assert unwrap_cjk_code(md) == md


def test_unterminated_fence_emitted_verbatim():
    md = f"```\n{_PROSE}"
    assert unwrap_cjk_code(md) == md


def test_plain_markdown_unchanged():
    md = "# Title\n\nSome English prose with `code` in it.\n"
    assert unwrap_cjk_code(md) == md.rstrip("\n")


def test_punctuation_only_span_left_alone():
    # No ideograph/kana/hangul: not enough evidence it is prose.
    md = "`---`"
    assert unwrap_cjk_code(md) == md
