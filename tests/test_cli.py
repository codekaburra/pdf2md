import json

import pytest

from pdf2md import cli


def test_parse_pages_single_ranges_and_deduplicates():
    assert cli.parse_pages("1, 3, 5-7, 3") == [0, 2, 4, 5, 6]


@pytest.mark.parametrize("spec", ["", "0", "3-2", "-1", "abc"])
def test_parse_pages_rejects_invalid_specs(spec):
    with pytest.raises(ValueError):
        cli.parse_pages(spec)


def test_main_writes_default_output_and_uses_all_pages(tmp_path, monkeypatch, capsys):
    input_pdf = tmp_path / "report.pdf"
    input_pdf.write_bytes(b"%PDF placeholder")
    calls = []

    def fake_convert(pdf_path, *, pages=None, filter_headers=True):
        calls.append(
            {
                "pdf_path": pdf_path,
                "pages": pages,
                "filter_headers": filter_headers,
            }
        )
        return "# Report\n\nBody text.\n"

    monkeypatch.setattr(cli, "convert", fake_convert)

    result = cli.main([str(input_pdf)])

    assert result == 0
    assert calls == [
        {
            "pdf_path": str(input_pdf),
            "pages": None,
            "filter_headers": True,
        }
    ]
    assert input_pdf.with_suffix(".md").read_text(encoding="utf-8") == (
        "# Report\n\nBody text.\n"
    )
    assert "wrote" in capsys.readouterr().out


def test_main_passes_page_subset_and_keep_headers(tmp_path, monkeypatch):
    input_pdf = tmp_path / "manual.pdf"
    input_pdf.write_bytes(b"%PDF placeholder")
    output_md = tmp_path / "out.md"
    calls = []

    def fake_convert(pdf_path, *, pages=None, filter_headers=True):
        calls.append((pdf_path, pages, filter_headers))
        return "Selected pages\n"

    monkeypatch.setattr(cli, "convert", fake_convert)

    result = cli.main(
        [
            str(input_pdf),
            "-o",
            str(output_md),
            "--pages",
            "1,3-4",
            "--keep-headers",
        ]
    )

    assert result == 0
    assert calls == [(str(input_pdf), [0, 2, 3], False)]
    assert output_md.read_text(encoding="utf-8") == "Selected pages\n"


def test_main_writes_chunks_json_with_requested_size(tmp_path, monkeypatch):
    input_pdf = tmp_path / "source.pdf"
    input_pdf.write_bytes(b"%PDF placeholder")
    output_md = tmp_path / "nested" / "converted.md"
    chunk_calls = []

    monkeypatch.setattr(cli, "convert", lambda *args, **kwargs: "# One\n\nAlpha\n")

    def fake_chunk_markdown(markdown, *, source="", max_chars=0):
        chunk_calls.append(
            {
                "markdown": markdown,
                "source": source,
                "max_chars": max_chars,
            }
        )
        return [
            {
                "path": "One",
                "heading": "One",
                "level": 1,
                "content": "Alpha",
                "chars": 5,
            }
        ]

    monkeypatch.setattr(cli, "chunk_markdown", fake_chunk_markdown)

    result = cli.main(
        [str(input_pdf), "-o", str(output_md), "--chunks", "--max-chars", "2000"]
    )

    assert result == 0
    assert output_md.read_text(encoding="utf-8") == "# One\n\nAlpha\n"
    chunks_path = output_md.with_suffix(".chunks.json")
    assert json.loads(chunks_path.read_text(encoding="utf-8")) == [
        {
            "path": "One",
            "heading": "One",
            "level": 1,
            "content": "Alpha",
            "chars": 5,
        }
    ]
    assert chunk_calls == [
        {
            "markdown": "# One\n\nAlpha\n",
            "source": "source",
            "max_chars": 2000,
        }
    ]


def test_main_reports_page_parse_errors_before_conversion(tmp_path, monkeypatch, capsys):
    input_pdf = tmp_path / "report.pdf"
    input_pdf.write_bytes(b"%PDF placeholder")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("convert should not be called for invalid page specs")

    monkeypatch.setattr(cli, "convert", fail_if_called)

    result = cli.main([str(input_pdf), "--pages", "2-1"])

    assert result == 1
    assert "invalid page range" in capsys.readouterr().err
