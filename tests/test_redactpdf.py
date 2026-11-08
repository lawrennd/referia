"""redactpdf interface key (CIP-0025 Phase A)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from test_web_reviewer import _build_reviewer


def _redact_setup(tmp_path, *, extra_view=None, col_vals=None, index_vals=None):
    config_dir = tmp_path / "review"
    source_dir = tmp_path / "files"
    store_dir = tmp_path / "pdfs"
    for d in (config_dir, source_dir, store_dir):
        d.mkdir()
    src = source_dir / "paper.pdf"
    src.write_bytes(b"%PDF-source%\n")
    view = {
        "sourcedirectory": "../files",
        "storedirectory": "../pdfs",
        "field": "LocalDocumentLink",
        "terms_field": "RedactTerms",
        "name": "redacted",
    }
    if extra_view:
        view.update(extra_view)
    reviewer, _, _ = _build_reviewer(
        index_vals=index_vals or ["Deep GPs"],
        col_vals=col_vals
        or {
            "LocalDocumentLink": "paper.pdf",
            "RedactTerms": "Alice Example",
        },
        extra={"redactpdf": [view]},
    )
    reviewer._directory = str(config_dir)
    return reviewer, src, store_dir


def test_redactpdf_resolve_missing_until_prepared(tmp_path, monkeypatch):
    reviewer, _, _ = _redact_setup(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert reviewer.get_record_document("redactpdf", 0) is None
    entries = reviewer.list_pdf_entries()
    assert entries[0]["kind"] == "redactpdf"
    assert entries[0]["exists"] is False


def test_ensure_redact_pdf_writes_store_not_source(tmp_path, monkeypatch):
    reviewer, src, _ = _redact_setup(
        tmp_path, extra_view={"max_pages": 2, "pages": [0]}
    )
    monkeypatch.chdir(tmp_path)
    before = src.read_bytes()

    def _fake_redact(source, dest, terms, **kwargs):
        Path(dest).write_bytes(b"%PDF-redacted%\n")
        assert Path(source).read_bytes() == before
        assert kwargs.get("max_pages") == 2
        assert kwargs.get("pages") == [0]
        assert terms[0]["value"] == "Alice Example"
        return {"matches": 1, "warnings": [], "dest": str(dest)}

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


def test_redact_terms_from_configured_list_and_dicts(tmp_path, monkeypatch):
    reviewer, _, _ = _redact_setup(
        tmp_path,
        col_vals={"LocalDocumentLink": "paper.pdf", "RedactTerms": ""},
        extra_view={
            "terms_field": "RedactTerms",
            "terms": [
                "Carol Config",
                {"value": "Dan Dict", "kind": "name", "match": "whole_word"},
                {"value": ""},
            ],
        },
    )
    monkeypatch.chdir(tmp_path)
    view = reviewer._interface_section("redactpdf")[0]
    terms = reviewer._redact_terms_from_view(view)
    values = [t["value"] for t in terms]
    assert "Carol Config" in values
    assert "Dan Dict" in values


def test_redact_terms_from_terms_string(tmp_path, monkeypatch):
    reviewer, _, _ = _redact_setup(
        tmp_path,
        col_vals={"LocalDocumentLink": "paper.pdf"},
        extra_view={"terms": "Eve | Frank"},
    )
    view = reviewer._interface_section("redactpdf")[0]
    view.pop("terms_field", None)
    monkeypatch.chdir(tmp_path)
    terms = reviewer._redact_terms_from_view(view)
    assert [t["value"] for t in terms] == ["Eve", "Frank"]


def test_redactpdf_requires_directories(tmp_path, monkeypatch):
    reviewer, _, _ = _redact_setup(tmp_path)
    view = reviewer._interface_section("redactpdf")[0]
    view.pop("sourcedirectory", None)
    view.pop("storedirectory", None)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="sourcedirectory and storedirectory"):
        reviewer._redactpdf_dest(view)


def test_redactpdf_default_stub_without_name(tmp_path, monkeypatch):
    reviewer, src, store_dir = _redact_setup(tmp_path)
    view = reviewer._interface_section("redactpdf")[0]
    view.pop("name", None)
    monkeypatch.chdir(tmp_path)
    dest, orig = reviewer._redactpdf_dest(view)
    assert orig == src
    assert dest.parent == store_dir
    assert "redacted_paper.pdf" in dest.name


def test_ensure_redact_pdf_errors(tmp_path, monkeypatch):
    reviewer, src, _ = _redact_setup(tmp_path)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(IndexError):
        reviewer.ensure_redact_pdf(9)

    src.unlink()
    with pytest.raises(FileNotFoundError, match="Source PDF"):
        with patch(
            "lynguine.access.documents.redact_pdf",
            side_effect=lambda *a, **k: None,
            create=True,
        ):
            reviewer.ensure_redact_pdf(0)


def test_ensure_redact_pdf_no_file_value(tmp_path, monkeypatch):
    reviewer, _, _ = _redact_setup(
        tmp_path, col_vals={"LocalDocumentLink": "", "RedactTerms": "A"}
    )
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError, match="No file value"):
        reviewer.ensure_redact_pdf(0)


def test_ensure_redact_pdf_dest_missing_after_call(tmp_path, monkeypatch):
    reviewer, _, _ = _redact_setup(tmp_path)
    monkeypatch.chdir(tmp_path)

    def _fake_redact(source, dest, terms, **kwargs):
        # Intentionally do not write dest.
        return {"matches": 0, "warnings": ["none"], "dest": str(dest)}

    with patch(
        "lynguine.access.documents.redact_pdf",
        side_effect=_fake_redact,
        create=True,
    ):
        with pytest.raises(FileNotFoundError, match="Could not create"):
            reviewer.ensure_redact_pdf(0)


def test_ensure_redact_pdf_import_error(tmp_path, monkeypatch):
    import sys
    import types

    reviewer, _, _ = _redact_setup(tmp_path)
    monkeypatch.chdir(tmp_path)

    fake_mod = types.ModuleType("lynguine.access.documents")
    with patch.dict(sys.modules, {"lynguine.access.documents": fake_mod}):
        with pytest.raises(ImportError, match="redact_pdf is required"):
            reviewer.ensure_redact_pdf(0)


def test_redact_pdf_button_in_document_panel():
    from referia.web.render import render_document_panel

    html = render_document_panel(
        [{"kind": "redactpdf", "n": 0, "label": "redacted", "exists": False}],
        [],
    )
    assert 'hx-post="/redact-pdf/0"' in html
    assert "Prepare redacted view" in html


def test_run_redact_pdf_success_warnings_and_prefix():
    from referia.web.routes import _run_redact_pdf

    class _Rev:
        def ensure_redact_pdf(self, n):
            assert n == 0
            return Path("/tmp/out.pdf"), {
                "matches": 0,
                "warnings": ["no matches for Alice"],
            }

    resp = _run_redact_pdf(_Rev(), 0, path_prefix="/reviews/intro")
    body = resp.body.decode()
    assert "Redacted PDF ready (0 matches)" in body
    assert "no matches for Alice" in body
    assert 'href="/reviews/intro/record-document/redactpdf/0"' in body
    assert 'data-auto-download="/reviews/intro/record-document/redactpdf/0"' in body


def test_run_redact_pdf_index_and_generic_errors():
    from referia.web.routes import _run_redact_pdf

    reviewer = MagicMock()
    reviewer.ensure_redact_pdf.side_effect = IndexError("missing")
    body = _run_redact_pdf(reviewer, 3).body.decode()
    assert "No redactpdf at index 3" in body

    reviewer.ensure_redact_pdf.side_effect = RuntimeError("secret /tmp/x")
    body = _run_redact_pdf(reviewer, 0).body.decode()
    assert "Prepare redacted PDF failed" in body
    assert "secret" not in body


def test_run_redact_pdf_uses_document_download_href():
    from referia.web.routes import _run_redact_pdf

    reviewer = MagicMock()
    reviewer.ensure_redact_pdf.return_value = (
        Path("/tmp/out.pdf"),
        {"matches": 2, "warnings": []},
    )
    reviewer.document_download_href.return_value = "/document/prepared.pdf"
    body = _run_redact_pdf(reviewer, 0).body.decode()
    assert 'href="/document/prepared.pdf"' in body
    assert "2 matches" in body


def test_post_redact_pdf_route():
    from referia.web.app import create_app

    reviewer = MagicMock()
    reviewer.index_list.return_value = ["alice"]
    reviewer.get_index.return_value = "alice"
    reviewer.get_viewer_specs.return_value = []
    reviewer.get_review_specs.return_value = []
    reviewer.get_widget_specs.return_value = []
    reviewer.render_viewer_html.return_value = ""
    reviewer.list_pdf_entries.return_value = []
    reviewer.list_url_entries.return_value = []
    reviewer.list_document_entries.return_value = []
    reviewer.ensure_redact_pdf.return_value = (
        Path("/tmp/out.pdf"),
        {"matches": 1, "warnings": []},
    )
    reviewer.document_download_href.return_value = "/document/redacted.pdf"
    reviewer._directory = "/tmp"

    with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
        app = create_app(user_file="_referia.yml", directory="/tmp")
        with TestClient(app) as client:
            response = client.post("/redact-pdf/0")
    assert response.status_code == 200
    reviewer.ensure_redact_pdf.assert_called_once_with(0)
    assert "Download" in response.text
    assert 'href="/document/redacted.pdf"' in response.text


def test_record_document_serves_redactpdf(tmp_path):
    from referia.web.app import create_app

    pdf = tmp_path / "redacted.pdf"
    pdf.write_bytes(b"%PDF-1.1\n%%EOF\n")
    reviewer = MagicMock()
    reviewer.index_list.return_value = ["alice"]
    reviewer.get_index.return_value = "alice"
    reviewer.get_viewer_specs.return_value = []
    reviewer.get_review_specs.return_value = []
    reviewer.get_widget_specs.return_value = []
    reviewer.render_viewer_html.return_value = ""
    reviewer.list_pdf_entries.return_value = []
    reviewer.list_url_entries.return_value = []
    reviewer.list_document_entries.return_value = []
    reviewer.get_record_document.return_value = pdf
    reviewer.allowed_roots_for_document.return_value = [tmp_path]
    reviewer._directory = str(tmp_path)

    with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
        app = create_app(user_file="_referia.yml", directory=str(tmp_path))
        with TestClient(app) as client:
            response = client.get(
                "/record-document/redactpdf/0", params={"index": "alice"}
            )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    reviewer.get_record_document.assert_called()
    assert reviewer.get_record_document.call_args[0][:2] == ("redactpdf", 0)


def test_root_redact_pdf_route(tmp_path):
    from referia.web.app import create_app

    config_dir = tmp_path / "reviews" / "intro"
    config_dir.mkdir(parents=True)
    (config_dir / "_referia.yml").write_text("title: test\n")

    # No document_download_href → fallback href gets path_prefix.
    rev = SimpleNamespace(
        ensure_redact_pdf=MagicMock(
            return_value=(
                Path("/tmp/out.pdf"),
                {"matches": 3, "warnings": []},
            )
        ),
        index_list=MagicMock(return_value=["alice"]),
        get_index=MagicMock(return_value="alice"),
        get_viewer_specs=MagicMock(return_value=[]),
        get_review_specs=MagicMock(return_value=[]),
        get_widget_specs=MagicMock(return_value=[]),
        render_viewer_html=MagicMock(return_value=""),
        list_pdf_entries=MagicMock(return_value=[]),
        list_url_entries=MagicMock(return_value=[]),
        list_document_entries=MagicMock(return_value=[]),
        get_row_data=MagicMock(return_value={}),
        get_value=MagicMock(return_value=""),
        affected_widgets=MagicMock(return_value=set()),
        _directory=str(config_dir),
        set_index=MagicMock(),
    )

    with patch("referia.assess.web_review.WebReviewer", return_value=rev):
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            response = client.post("/reviews/intro/redact-pdf/0")
    assert response.status_code == 200
    assert "3 matches" in response.text
    assert "/reviews/intro/record-document/redactpdf/0" in response.text
    rev.ensure_redact_pdf.assert_called_once_with(0)
