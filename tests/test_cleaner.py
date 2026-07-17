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
