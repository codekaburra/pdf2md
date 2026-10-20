import json

import pytest

from pdf2md.chunker import chunk_markdown

SAMPLE = """intro paragraph before any heading.

# User Guide

## 1. Installation

Installation steps go here.

## 2. Settings

Settings content goes here.

### 2.1 Advanced

Advanced content goes here.

## 3. Troubleshooting

Troubleshooting content goes here.
"""


def test_breadcrumb_paths():
    chunks = chunk_markdown(SAMPLE, source="manual")
    paths = [c["path"] for c in chunks]
    assert "manual" in paths  # preamble
    assert "User Guide > 1. Installation" in paths
    assert "User Guide > 2. Settings > 2.1 Advanced" in paths
    assert "User Guide > 3. Troubleshooting" in paths


def test_preamble_without_source():
    chunks = chunk_markdown("just some text, no headings")
    assert len(chunks) == 1
    assert chunks[0]["heading"] == "(preamble)"
    assert chunks[0]["level"] == 0


@pytest.mark.parametrize(
    "heading, title",
    [
        ("# C#", "C#"),
        ("## F#", "F#"),
        ("# C# ###", "C#"),
        ("# Step 1 #", "Step 1"),
        ("# Issue #123#", "Issue #123#"),
        ("# Topic ###suffix", "Topic ###suffix"),
        ("# Topic\t###\t", "Topic"),
        ("   ### C#", "C#"),
    ],
)
def test_heading_hashes_preserve_title_and_breadcrumb(heading, title):
    chunks = chunk_markdown(f"{heading}\n\nBody\n\n#### Child\n\nDetails")

    assert chunks[0]["heading"] == title
    assert chunks[0]["path"] == title
    assert chunks[1]["path"] == f"{title} > Child"


def test_empty_heading_sections_skipped():
    md = "# Top\n\n## Empty parent\n\n### Child\n\ncontent here\n"
    chunks = chunk_markdown(md)
    headings = [c["heading"] for c in chunks]
    assert "Empty parent" not in headings
    assert "Child" in headings


def test_hash_inside_code_fence_not_a_heading():
    md = "# Real\n\n```bash\n# not a heading\necho hi\n```\n\ntext after\n"
    chunks = chunk_markdown(md)
    assert len(chunks) == 1
    assert chunks[0]["heading"] == "Real"
    assert "# not a heading" in chunks[0]["content"]


@pytest.mark.parametrize(
    "opening, inner, closing",
    [
        ("````markdown", "```", "````"),
        ("```", "~~~", "```"),
        ("~~~", "```", "~~~~"),
        ("```", "``` trailing text", "```"),
        ("```", "    ```", "   ````  "),
    ],
)
def test_only_matching_fence_closes_code_block(opening, inner, closing):
    block = f"{opening}\n{inner}\n# not a heading\n{closing}"
    chunks = chunk_markdown(f"# Real\n\n{block}\n\n## Next\n\nBody")

    assert [chunk["heading"] for chunk in chunks] == ["Real", "Next"]
    assert chunks[0]["content"] == block.strip()


def test_backtick_in_info_string_is_not_an_opening_fence():
    md = "```invalid`info\n# Real\n\nBody"
    assert [chunk["heading"] for chunk in chunk_markdown(md)] == ["(preamble)", "Real"]


def test_chunk_fields_and_chars():
    chunks = chunk_markdown(SAMPLE, source="manual")
    for c in chunks:
        assert set(c) == {"path", "heading", "level", "content", "chars"}
        assert c["chars"] == len(c["content"])
        assert c["content"].strip()
    json.dumps(chunks, ensure_ascii=False)  # serializable


def test_max_chars_splits_at_paragraph_boundaries():
    paras = [f"paragraph {i} " + "x" * 80 for i in range(4)]
    md = "# Big\n\n" + "\n\n".join(paras) + "\n"
    chunks = chunk_markdown(md, max_chars=200)
    assert len(chunks) > 1
    for i, c in enumerate(chunks, 1):
        assert c["path"].endswith(f"({i}/{len(chunks)})")
        # no paragraph was split mid-way
        for para in c["content"].split("\n\n"):
            assert para in paras


def test_max_chars_never_splits_single_paragraph():
    md = "# Big\n\n" + "y" * 500 + "\n"
    chunks = chunk_markdown(md, max_chars=100)
    assert len(chunks) == 1
    assert chunks[0]["chars"] == 500
