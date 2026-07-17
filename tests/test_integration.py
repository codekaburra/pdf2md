import json
import subprocess
import sys

import pymupdf
import pytest

from pdf2md.chunker import chunk_markdown
from pdf2md.converter import ScannedPDFError, convert

N_PAGES = 5
SECTIONS = ["Introduction", "Methodology", "Results", "Discussion", "Conclusion"]


@pytest.fixture(scope="module")
def sample_pdf(tmp_path_factory):
    """A 5-page PDF with a repeating header, footer page numbers,
    per-page section headings, and body text."""
    path = tmp_path_factory.mktemp("pdfs") / "sample.pdf"
    doc = pymupdf.open()
    for i, section in enumerate(SECTIONS, 1):
        page = doc.new_page()  # A4
        page.insert_text((72, 40), "ACME Corp — Confidential", fontsize=9)
        page.insert_text((72, 120), section, fontsize=22)
        for j in range(3):
            page.insert_text(
                (72, 170 + j * 40),
                f"This paragraph explains the {section.lower()} of topic {j} "
                "in perfectly plain English prose.",
                fontsize=11,
            )
        page.insert_text((72, 810), f"Page {i} of {N_PAGES}", fontsize=9)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture(scope="module")
def scanned_pdf(tmp_path_factory):
    """Pages with no text layer at all."""
    path = tmp_path_factory.mktemp("pdfs") / "scanned.pdf"
    doc = pymupdf.open()
    for _ in range(3):
        page = doc.new_page()
        page.draw_rect(pymupdf.Rect(50, 50, 500, 700))
    doc.save(str(path))
    doc.close()
    return path


def test_convert_strips_header_and_footer(sample_pdf):
    md = convert(str(sample_pdf))
    assert "ACME" not in md
    assert "Page 1 of 5" not in md
    assert "Results" in md
    assert "plain English prose" in md


def test_keep_headers_flag(sample_pdf):
    md = convert(str(sample_pdf), filter_headers=False)
    assert "ACME" in md


def test_pages_subset(sample_pdf):
    md = convert(str(sample_pdf), pages=[0])
    assert "Introduction" in md
    assert "Results" not in md


def test_pages_out_of_range(sample_pdf):
    with pytest.raises(ValueError):
        convert(str(sample_pdf), pages=[99])


def test_scanned_pdf_raises(scanned_pdf):
    with pytest.raises(ScannedPDFError):
        convert(str(scanned_pdf))


def test_chunks_from_converted_markdown(sample_pdf):
    md = convert(str(sample_pdf))
    chunks = chunk_markdown(md, source="sample")
    assert chunks
    assert all(c["content"].strip() for c in chunks)
    # font-size-based heading detection should have produced real headings
    assert any(c["level"] > 0 for c in chunks)
    all_paths = " ".join(c["path"] for c in chunks)
    assert any(section in all_paths for section in SECTIONS)


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "pdf2md.cli", *args],
        capture_output=True,
        text=True,
    )


def test_cli_end_to_end(sample_pdf, tmp_path):
    out = tmp_path / "out.md"
    result = _run_cli(str(sample_pdf), "-o", str(out), "--chunks")
    assert result.returncode == 0, result.stderr
    assert out.is_file()
    chunks_file = tmp_path / "out.chunks.json"
    assert chunks_file.is_file()
    chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
    assert isinstance(chunks, list) and chunks


def test_cli_missing_file(tmp_path):
    result = _run_cli(str(tmp_path / "nope.pdf"))
    assert result.returncode == 1


def test_cli_scanned_exit_code(scanned_pdf):
    result = _run_cli(str(scanned_pdf))
    assert result.returncode == 2
    assert "ocrmypdf" in result.stderr


def test_cli_bad_page_range(sample_pdf, tmp_path):
    result = _run_cli(str(sample_pdf), "-o", str(tmp_path / "x.md"), "--pages", "99")
    assert result.returncode == 1


def test_cli_corrupt_pdf(tmp_path):
    bad = tmp_path / "corrupt.pdf"
    bad.write_bytes(b"this is not a pdf at all")
    result = _run_cli(str(bad))
    assert result.returncode == 1
    assert "Traceback" not in result.stderr


def test_cli_creates_output_directory(sample_pdf, tmp_path):
    out = tmp_path / "does" / "not" / "exist" / "out.md"
    result = _run_cli(str(sample_pdf), "-o", str(out))
    assert result.returncode == 0, result.stderr
    assert out.is_file()
