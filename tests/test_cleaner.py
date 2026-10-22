import pytest

from pdf2md.cleaner import clean_pages

_WORDS = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]


def _make_pages(n=5, header="ACME Corp — Annual Report", footer=True):
    pages = []
    for i in range(1, n + 1):
        word = _WORDS[i - 1]
        lines = [
            header,
            "",
            f"The {word} section discusses {word} widgets.",
            f"More prose about {word} follows here.",
            "",
        ]
        if footer:
            lines.append(f"Page {i} of {n}")
        pages.append("\n".join(lines))
    return pages


def test_repeating_header_removed():
    cleaned = clean_pages(_make_pages())
    for page in cleaned:
        assert "ACME" not in page
        assert "widgets" in page


@pytest.mark.parametrize("level", range(1, 7))
@pytest.mark.parametrize("edge", ["top", "bottom"])
def test_repeating_heading_and_adjacent_page_number_removed(level, edge):
    header = f"{'#' * level} ACME Report 2026"
    pages = []
    bodies = []
    for i, word in enumerate(_WORDS[:4], 1):
        body = f"Opening about {word}.\n\nDetails about {word}.\n\nClosing on {word}."
        bodies.append(body)
        margin = f"{header}\nPage {i}" if edge == "top" else f"Page {i}\n{header}"
        pages.append(f"{margin}\n\n{body}" if edge == "top" else f"{body}\n\n{margin}")

    assert clean_pages(pages) == bodies


def test_heading_repeat_detection_uses_exact_text():
    headings = ["# Results", "# RESULTS", "#  Results", " # Results"]
    pages = [
        f"{heading}\n\nUnique body about {word}."
        for heading, word in zip(headings, _WORDS)
    ]

    for heading, page in zip(headings, clean_pages(pages)):
        assert heading.strip() in page


def test_footer_page_numbers_removed():
    cleaned = clean_pages(_make_pages())
    for page in cleaned:
        assert "Page" not in page


def test_header_with_varying_number_removed():
    pages = []
    for i in range(1, 6):
        word = _WORDS[i - 1]
        pages.append(f"{i} | ACME Report\n\nParagraph about {word} things.")
    cleaned = clean_pages(pages)
    for page in cleaned:
        assert "ACME" not in page
        assert "Paragraph about" in page


def test_few_pages_keeps_repeated_lines():
    # Repeat-based removal needs >= 4 pages.
    cleaned = clean_pages(_make_pages(n=3, footer=False))
    for page in cleaned:
        assert "ACME" in page


def test_page_number_variants_stripped_even_on_single_page():
    for variant in ["12", "- 12 -", "Page 12", "Page 12 of 30", "12 / 30", "第 12 頁"]:
        page = f"Some real content.\n\n{variant}"
        cleaned = clean_pages([page])
        assert "Some real content." in cleaned[0]
        assert variant not in cleaned[0]


def test_content_starting_with_number_kept():
    page = "12 monkeys jumped on the bed.\n\nMore text."
    cleaned = clean_pages([page])
    assert "12 monkeys" in cleaned[0]


def test_numbered_markdown_heading_kept():
    page = "## 3. Results\n\nFindings below."
    cleaned = clean_pages([page])
    assert "## 3. Results" in cleaned[0]


@pytest.mark.parametrize("level", range(1, 7))
@pytest.mark.parametrize("edge", ["top", "bottom"])
def test_repeated_numbered_headings_kept_across_pages(level, edge):
    headings = [f"{'#' * level} {i}. Results" for i in range(1, 5)]
    bodies = [f"Unique body about {word}." for word in _WORDS[:4]]
    pages = [
        f"ACME Report\n\n{heading}\n\n{body}\n\nPage {i}"
        if edge == "top" else
        f"ACME Report\n\n{body}\n\n{heading}\n\nPage {i}"
        for i, (heading, body) in enumerate(zip(headings, bodies), 1)
    ]

    for heading, body, page in zip(headings, bodies, clean_pages(pages)):
        assert heading in page
        assert body in page
        assert "ACME" not in page
        assert "Page " not in page


def test_distinct_top_lines_kept():
    pages = [f"Opening about {word}.\n\nBody prose on {word}." for word in _WORDS]
    cleaned = clean_pages(pages)
    for word, page in zip(_WORDS, cleaned):
        assert f"Opening about {word}." in page


def test_repeated_line_in_middle_of_page_kept():
    # The same disclaimer sentence in the middle of every page must survive:
    # only the page edges are stripped.
    pages = []
    for i in range(1, 6):
        word = _WORDS[i - 1]
        pages.append(
            f"Opening about {word}.\n\nSee appendix for details.\n\nClosing on {word}."
        )
    cleaned = clean_pages(pages)
    for page in cleaned:
        assert "See appendix for details." in page
