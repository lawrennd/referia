"""redactpdf interface key (CIP-0025 Phase A)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from test_web_reviewer import _build_reviewer


def test_redactpdf_resolve_missing_until_prepared(tmp_path, monkeypatch):
    config_dir = tmp_path / "review"
    source_dir = tmp_path / "files"
    store_dir = tmp_path / "pdfs"
    for d in (config_dir, source_dir, store_dir):
        d.mkdir()
    src = source_dir / "paper.pdf"
    src.write_bytes(b"%PDF-1.1\n%%EOF\n")

    reviewer, _, _ = _build_reviewer(
        index_vals=["Deep GPs"],
        col_vals={
            "LocalDocumentLink": "paper.pdf",
            "RedactTerms": "Alice Example; Bob Example",
        },
        extra={
            "redactpdf": [
                {
                    "sourcedirectory": "../files",
                    "storedirectory": "../pdfs",
                    "field": "LocalDocumentLink",
                    "terms_field": "RedactTerms",
                    "name": "redacted",
                }
            ],
        },
    )
    reviewer._directory = str(config_dir)
    monkeypatch.chdir(tmp_path)

    assert reviewer.get_record_document("redactpdf", 0) is None
    entries = reviewer.list_pdf_entries()
    assert entries[0]["kind"] == "redactpdf"
    assert entries[0]["exists"] is False


def test_ensure_redact_pdf_writes_store_not_source(tmp_path, monkeypatch):
    config_dir = tmp_path / "review"
    source_dir = tmp_path / "files"
    store_dir = tmp_path / "pdfs"
    for d in (config_dir, source_dir, store_dir):
        d.mkdir()
    src = source_dir / "paper.pdf"
    src.write_bytes(b"%PDF-source%\n")
    before = src.read_bytes()

    reviewer, _, _ = _build_reviewer(
        index_vals=["Deep GPs"],
        col_vals={
            "LocalDocumentLink": "paper.pdf",
            "RedactTerms": "Alice Example",
        },
        extra={
            "redactpdf": [
                {
                    "sourcedirectory": "../files",
                    "storedirectory": "../pdfs",
                    "field": "LocalDocumentLink",
                    "terms_field": "RedactTerms",
                    "name": "redacted",
                    "max_pages": 2,
                }
            ],
        },
    )
    reviewer._directory = str(config_dir)
    monkeypatch.chdir(tmp_path)

    def _fake_redact(source, dest, terms, **kwargs):
        Path(dest).write_bytes(b"%PDF-redacted%\n")
        assert Path(source).read_bytes() == before
        assert kwargs.get("max_pages") == 2
        assert terms[0]["value"] == "Alice Example"
        return {"matches": 1, "warnings": [], "dest": str(dest)}

    # create=True: CI may still install lynguine without CIP-001A redact_pdf.
    with patch(
        "lynguine.access.documents.redact_pdf",
        side_effect=_fake_redact,
        create=True,
    ):
        dest, result = reviewer.ensure_redact_pdf(0)

    assert dest.is_file()
    assert dest.read_bytes() == b"%PDF-redacted%\n"
    assert src.read_bytes() == before
    assert result["matches"] == 1
    assert reviewer.get_record_document("redactpdf", 0) == dest


def test_redact_pdf_button_in_document_panel():
    from referia.web.render import render_document_panel

    html = render_document_panel(
        [{"kind": "redactpdf", "n": 0, "label": "redacted", "exists": False}],
        [],
    )
    assert 'hx-post="/redact-pdf/0"' in html
    assert "Prepare redacted view" in html
