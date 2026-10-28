"""Tests for referia.web.app.create_app() factory — both modes.

Single-config mode (original):
    create_app(user_file=..., directory=...)

Root-server mode (new):
    create_app(root=...)
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from referia.web.app import create_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _yaml_exception_text(text: str) -> str:
    """Return PyYAML's exception string for *text*, which must fail to parse."""
    import yaml

    try:
        yaml.safe_load(text)
    except Exception as exc:
        return str(exc)
    raise AssertionError(f"expected YAML parse failure for {text!r}")


def _mock_reviewer():
    r = MagicMock()
    r.index_list.return_value = ["alice", "bob"]
    r.get_index.return_value = "alice"
    r.get_viewer_specs.return_value = []
    r.get_review_specs.return_value = []
    r.get_widget_specs.return_value = []
    r.render_viewer_html.return_value = ""
    r.get_value.return_value = ""
    r.get_row_data.return_value = {}
    return r


# ---------------------------------------------------------------------------
# Single-config mode
# ---------------------------------------------------------------------------

class TestSingleConfigMode:
    def test_app_state_set_correctly(self):
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            app = create_app(user_file="_referia.yml", directory="/tmp")
        assert app.state.user_file == "_referia.yml"
        assert app.state.directory == str(Path("/tmp").resolve())
        assert app.state.root is None

    def test_reviewer_cache_initialised(self):
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            app = create_app(user_file="_referia.yml", directory="/tmp")
        assert hasattr(app.state, "reviewer_cache")
        assert app.state.reviewer_cache == {}

    def test_reviewer_loaded_on_startup(self):
        mock_rev = _mock_reviewer()
        with patch("referia.assess.web_review.WebReviewer", return_value=mock_rev):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app):
                assert app.state.reviewer is mock_rev

    def test_health_endpoint_single_config(self):
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "single-config"
        assert body["status"] == "ok"
        assert body["reviewer"] == "loaded"

    def test_health_degraded_when_startup_fails(self):
        with patch(
            "referia.assess.web_review.WebReviewer",
            side_effect=RuntimeError("bad config"),
        ):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                resp = client.get("/health")
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["reviewer"] == "failed"

    def test_field_bulk_sets_all_working_indices(self):
        mock_rev = _mock_reviewer()
        mock_rev.working_indices.return_value = ["a", "b", "c"]
        mock_rev.get_display_layout.return_value = "inline_list"
        mock_rev.get_filter_specs.return_value = []
        mock_rev.get_sort_specs.return_value = []
        mock_rev.get_filter_state.return_value = {}
        complete_spec = {"type": "Checkbox", "field": "complete"}
        mock_rev.get_review_specs.return_value = [complete_spec]
        mock_rev.get_widget_specs.return_value = [complete_spec]
        mock_rev.list_pdf_entries.return_value = []
        mock_rev.list_url_entries.return_value = []
        mock_rev.list_document_entries.return_value = []
        mock_rev.affected_widgets.return_value = []
        with patch("referia.assess.web_review.WebReviewer", return_value=mock_rev):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                resp = client.post(
                    "/field-bulk/complete",
                    data={"complete": "true"},
                )
        assert resp.status_code == 200
        assert mock_rev.set_value.call_count == 3
        assert all(
            call.args == ("complete", True)
            for call in mock_rev.set_value.call_args_list
        )

    def test_field_bulk_parameter_writes_once(self):
        mock_rev = _mock_reviewer()
        data = MagicMock()
        data.isparameter.return_value = True
        data.ismutable.return_value = True
        mock_rev._data = data
        mock_rev.working_indices.return_value = ["a", "b"]
        mock_rev.get_display_layout.return_value = "inline_list"
        mock_rev.get_filter_specs.return_value = []
        mock_rev.get_sort_specs.return_value = []
        mock_rev.get_filter_state.return_value = {}
        spec = {"type": "Text", "field": "phrase_kinds"}
        mock_rev.get_review_specs.return_value = [spec]
        mock_rev.get_widget_specs.return_value = [spec]
        mock_rev.list_pdf_entries.return_value = []
        mock_rev.list_url_entries.return_value = []
        mock_rev.list_document_entries.return_value = []
        mock_rev.affected_widgets.return_value = []
        with patch("referia.assess.web_review.WebReviewer", return_value=mock_rev):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                resp = client.post(
                    "/field-bulk/phrase_kinds",
                    data={"phrase_kinds": "concern, benefit"},
                )
        assert resp.status_code == 200
        mock_rev.set_value.assert_called_once_with("phrase_kinds", "concern, benefit")

    def test_populate_all_runs_for_working_indices(self):
        mock_rev = _mock_reviewer()
        mock_rev.working_indices.return_value = ["a", "b"]
        mock_rev.get_display_layout.return_value = "inline_list"
        mock_rev.get_filter_specs.return_value = []
        mock_rev.get_sort_specs.return_value = []
        mock_rev.get_filter_state.return_value = {}
        mock_rev.get_display_detail_field.return_value = None
        btn = {
            "type": "PopulateButton",
            "field": "_segment",
            "args": {
                "description": "Segment document",
                "target": "units",
                "compute": {"field": "units", "function": "document_segment"},
            },
        }
        mock_rev.get_review_specs.return_value = [btn]
        mock_rev.get_widget_specs.return_value = [btn]
        mock_rev.list_pdf_entries.return_value = []
        mock_rev.list_url_entries.return_value = []
        mock_rev.list_document_entries.return_value = []
        mock_rev.affected_widgets.return_value = []
        mock_rev.run_populate.return_value = None
        with patch("referia.assess.web_review.WebReviewer", return_value=mock_rev):
            app = create_app(user_file="_referia.yml", directory="/tmp")
            with TestClient(app) as client:
                resp = client.post("/populate-all/_segment")
        assert resp.status_code == 200
        assert mock_rev.run_populate.call_count == 2


# ---------------------------------------------------------------------------
# Root-server mode
# ---------------------------------------------------------------------------

class TestRootServerMode:
    def test_app_state_root_set(self, tmp_path):
        app = create_app(root=str(tmp_path))
        assert app.state.root == str(tmp_path.resolve())

    def test_app_state_reviewer_is_none(self, tmp_path):
        app = create_app(root=str(tmp_path))
        assert app.state.reviewer is None

    def test_reviewer_cache_initialised(self, tmp_path):
        app = create_app(root=str(tmp_path))
        assert app.state.reviewer_cache == {}

    def test_user_file_is_none_in_root_mode(self, tmp_path):
        app = create_app(root=str(tmp_path))
        assert app.state.user_file is None

    def test_directory_set_to_root(self, tmp_path):
        app = create_app(root=str(tmp_path))
        assert app.state.directory == str(tmp_path.resolve())

    def test_root_is_resolved_to_absolute(self):
        """Relative root path is resolved to an absolute path."""
        app = create_app(root=".")
        assert os.path.isabs(app.state.root)

    def test_health_endpoint_root_mode(self, tmp_path):
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "root-server"
        assert body["status"] == "ok"
        assert body["root"] == str(tmp_path.resolve())
        assert body["configs_cached"] == 0

    def test_root_mode_does_not_call_web_reviewer_at_startup(self, tmp_path):
        """WebReviewer must NOT be constructed during startup in root mode."""
        with patch("referia.assess.web_review.WebReviewer") as MockRev:
            app = create_app(root=str(tmp_path))
            with TestClient(app):
                MockRev.assert_not_called()

    def test_root_slash_returns_listing_when_no_root_yml(self, tmp_path):
        """In root mode without {root}/_referia.yml, GET / lists configs (CIP-000C)."""
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/")
        assert resp.status_code == 200
        assert "Reviews under" in resp.text

    def test_root_slash_loads_referia_yml_when_present(self, tmp_path):
        """CIP-0010: GET / loads {root}/_referia.yml instead of the listing."""
        (tmp_path / "_referia.yml").write_text("title: Root Overview\n")
        mock_rev = _mock_reviewer()
        with patch("referia.assess.web_review.WebReviewer", return_value=mock_rev):
            app = create_app(root=str(tmp_path))
            with TestClient(app) as client:
                resp = client.get("/")
        assert resp.status_code == 200
        assert "Reviews under" not in resp.text
        assert "<!DOCTYPE html>" in resp.text
        mock_rev.index_list.assert_called()

    def test_root_slash_record_serves_root_yml(self, tmp_path):
        """Unprefixed /record uses {root}/_referia.yml when present."""
        (tmp_path / "_referia.yml").write_text("title: Root Overview\n")
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            app = create_app(root=str(tmp_path))
            with TestClient(app) as client:
                resp = client.get("/record")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# inline_list grouping
# ---------------------------------------------------------------------------

class TestInlineListGroup:
    def test_relative_source_directory_uses_top_level(self, tmp_path):
        from referia.web.routes import _inline_list_group

        reviewer = MagicMock()
        reviewer._directory = str(tmp_path)
        group = _inline_list_group(
            reviewer,
            {
                "sourceDirectory": (
                    "templates/2026-10-09_recurring/"
                    "mphil-admissions/interview-setup"
                )
            },
        )
        assert group == "templates"

    def test_absolute_source_directory_uses_top_level(self, tmp_path):
        from referia.web.routes import _inline_list_group

        leaf = (
            tmp_path
            / "applications"
            / "2025-01-27_phd"
            / "interview-setup"
        )
        leaf.mkdir(parents=True)
        reviewer = MagicMock()
        reviewer._directory = str(tmp_path)
        assert _inline_list_group(
            reviewer, {"sourceDirectory": str(leaf)}
        ) == "applications"

    def test_shallow_path_has_no_group(self, tmp_path):
        from referia.web.routes import _inline_list_group

        reviewer = MagicMock()
        reviewer._directory = str(tmp_path)
        assert _inline_list_group(reviewer, {"sourceDirectory": "."}) == ""
        assert _inline_list_group(
            reviewer, {"sourceDirectory": "solo.yml"}
        ) == ""

    def test_group_by_version(self, tmp_path):
        from referia.web.routes import _inline_list_group, _inline_list_group_by

        reviewer = MagicMock()
        reviewer._directory = str(tmp_path)
        assert (
            _inline_list_group(
                reviewer,
                {"referia_config_version": 2, "sourceDirectory": "a/b"},
                group_by="version",
            )
            == "v2"
        )
        assert (
            _inline_list_group(
                reviewer,
                {"referia_config_version": "v1"},
                group_by="version",
            )
            == "v1"
        )
        assert (
            _inline_list_group(reviewer, {}, group_by="version") == "unknown"
        )
        assert _inline_list_group_by({"_group": "version"}) == "version"
        assert _inline_list_group_by({}) == "directory"
        assert _inline_list_group_by({"_group": "nope"}) == "directory"
        assert _inline_list_group_by({"_group": "month"}) == "month"
        assert _inline_list_group_by({"_group": "none"}) == "none"

    def test_group_by_month_from_when(self, tmp_path):
        from referia.web.routes import _inline_list_group, _month_group_from_when

        reviewer = MagicMock()
        reviewer._directory = str(tmp_path)
        assert (
            _inline_list_group(
                reviewer, {"when": "20261028"}, group_by="month"
            )
            == "2026-10"
        )
        assert (
            _inline_list_group(
                reviewer, {"when": "2026-11-01"}, group_by="month"
            )
            == "2026-11"
        )
        assert (
            _inline_list_group(reviewer, {"when": ""}, group_by="month") == ""
        )
        assert _month_group_from_when("not-a-date") == ""
        assert _month_group_from_when(None) == ""

    def test_group_by_none_is_flat(self, tmp_path):
        from referia.web.routes import _inline_list_group

        reviewer = MagicMock()
        reviewer._directory = str(tmp_path)
        assert (
            _inline_list_group(
                reviewer,
                {"sourceDirectory": "applications/foo", "when": "20261028"},
                group_by="none",
            )
            == ""
        )

    def test_inline_list_href_keeps_index_query(self):
        from referia.web.routes import _inline_list_href

        reviewer = MagicMock()
        href = _inline_list_href(
            reviewer,
            {"config_url": "/_marking/worksheet1/?index=alice"},
            prefix="/_marking/worksheet1-summary",
        )
        assert href == "/_marking/worksheet1/?index=alice"


# ---------------------------------------------------------------------------
# Root-server path resolution helpers
# ---------------------------------------------------------------------------

class TestResolveConfigPath:
    def test_directory_path_maps_to_default_yml(self, tmp_path):
        from referia.web.routes import _resolve_config_path
        cfg = tmp_path / "reviews" / "intro"
        cfg.mkdir(parents=True)
        (cfg / "_referia.yml").write_text("title: test")
        file_path, user_file = _resolve_config_path(str(tmp_path), "reviews/intro")
        assert file_path == cfg / "_referia.yml"
        assert user_file == "_referia.yml"

    def test_trailing_slash_stripped(self, tmp_path):
        from referia.web.routes import _resolve_config_path
        cfg = tmp_path / "intro"
        cfg.mkdir()
        (cfg / "_referia.yml").write_text("title: test")
        file_path, user_file = _resolve_config_path(str(tmp_path), "intro/")
        assert file_path == cfg / "_referia.yml"
        assert user_file == "_referia.yml"

    def test_explicit_yml_filename(self, tmp_path):
        from referia.web.routes import _resolve_config_path
        cfg = tmp_path / "intro"
        cfg.mkdir()
        (cfg / "_draft.yml").write_text("title: draft")
        file_path, user_file = _resolve_config_path(str(tmp_path), "intro/_draft.yml")
        assert file_path == cfg / "_draft.yml"
        assert user_file == "_draft.yml"

    def test_missing_config_raises_404(self, tmp_path):
        from referia.web.routes import _resolve_config_path
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _resolve_config_path(str(tmp_path), "nonexistent/path")
        assert exc_info.value.status_code == 404

    def test_path_traversal_raises_400(self, tmp_path):
        from referia.web.routes import _resolve_config_path
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _resolve_config_path(str(tmp_path), "../../etc/passwd")
        assert exc_info.value.status_code == 400

    def test_empty_path_uses_root_default_yml(self, tmp_path):
        from referia.web.routes import _resolve_config_path
        (tmp_path / "_referia.yml").write_text("title: root")
        file_path, user_file = _resolve_config_path(str(tmp_path), "")
        assert file_path == tmp_path / "_referia.yml"
        assert user_file == "_referia.yml"


class TestGetCachedReviewer:
    def test_loads_reviewer_on_cache_miss(self, tmp_path):
        from referia.web.routes import _get_cached_reviewer
        cfg = tmp_path / "_referia.yml"
        cfg.write_text("title: test")
        mock_state = MagicMock()
        mock_state.reviewer_cache = {}
        mock_rev = _mock_reviewer()
        with patch("referia.assess.web_review.WebReviewer", return_value=mock_rev):
            result = _get_cached_reviewer(mock_state, cfg, "_referia.yml")
        assert result is mock_rev
        assert str(cfg) in mock_state.reviewer_cache

    def test_returns_cached_reviewer_on_hit(self, tmp_path):
        from referia.web.routes import _get_cached_reviewer
        cfg = tmp_path / "_referia.yml"
        cfg.write_text("title: test")
        mock_state = MagicMock()
        mock_rev = _mock_reviewer()
        mtime = cfg.stat().st_mtime
        mock_state.reviewer_cache = {str(cfg): (mtime, mock_rev)}
        with patch("referia.assess.web_review.WebReviewer") as MockRev:
            result = _get_cached_reviewer(mock_state, cfg, "_referia.yml")
            MockRev.assert_not_called()
        assert result is mock_rev

    def test_reloads_when_mtime_changes(self, tmp_path):
        from referia.web.routes import _get_cached_reviewer
        import time
        cfg = tmp_path / "_referia.yml"
        cfg.write_text("title: v1")
        mock_state = MagicMock()
        old_rev = _mock_reviewer()
        # Store a stale mtime (0.0)
        mock_state.reviewer_cache = {str(cfg): (0.0, old_rev)}
        new_rev = _mock_reviewer()
        with patch("referia.assess.web_review.WebReviewer", return_value=new_rev):
            result = _get_cached_reviewer(mock_state, cfg, "_referia.yml")
        assert result is new_rev


# ---------------------------------------------------------------------------
# Root-server router integration
# ---------------------------------------------------------------------------

def _make_root_app_with_config(tmp_path, config_path: str, mock_reviewer=None):
    """Create a root-mode app with a real (empty) _referia.yml at config_path."""
    config_dir = tmp_path / config_path
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "_referia.yml").write_text("title: test")
    if mock_reviewer is None:
        mock_reviewer = _mock_reviewer()
    with patch("referia.assess.web_review.WebReviewer", return_value=mock_reviewer):
        app = create_app(root=str(tmp_path))
    return app, mock_reviewer


class TestRootRouterRoutes:
    def test_root_index_redirects_to_trailing_slash(self, tmp_path):
        """GET /reviews/intro should redirect to /reviews/intro/ for correct relative URL resolution."""
        app, _ = _make_root_app_with_config(tmp_path, "reviews/intro")
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app, follow_redirects=False) as client:
                resp = client.get("/reviews/intro")
        assert resp.status_code == 301
        assert resp.headers["location"].endswith("/reviews/intro/")

    def test_root_index_redirect_preserves_index_query(self, tmp_path):
        app, _ = _make_root_app_with_config(tmp_path, "reviews/intro")
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app, follow_redirects=False) as client:
                resp = client.get("/reviews/intro?index=bob")
        assert resp.status_code == 301
        location = resp.headers["location"]
        assert location.endswith("/reviews/intro/?index=bob") or (
            "/reviews/intro/" in location and "index=bob" in location
        )

    def test_root_index_honours_query_index(self, tmp_path):
        reviewer = _mock_reviewer()
        app, _ = _make_root_app_with_config(tmp_path, "reviews/intro", reviewer)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            with TestClient(app) as client:
                reviewer.set_index.reset_mock()
                resp = client.get("/reviews/intro/?index=bob")
        assert resp.status_code == 200
        reviewer.set_index.assert_called_with("bob")

    def test_root_index_trailing_slash_returns_full_page(self, tmp_path):
        app, _ = _make_root_app_with_config(tmp_path, "reviews/intro")
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.get("/reviews/intro/")
        assert resp.status_code == 200
        assert "<!DOCTYPE html>" in resp.text

    def test_root_index_contains_config_path_prefix_in_js(self, tmp_path):
        app, _ = _make_root_app_with_config(tmp_path, "reviews/intro")
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.get("/reviews/intro/")
        assert "/reviews/intro" in resp.text

    def test_root_record_fragment_200(self, tmp_path):
        app, _ = _make_root_app_with_config(tmp_path, "reviews/intro")
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.get("/reviews/intro/record")
        assert resp.status_code == 200

    def test_root_save_returns_ok(self, tmp_path):
        app, _ = _make_root_app_with_config(tmp_path, "reviews/intro")
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.post("/reviews/intro/save")
        assert resp.status_code == 200
        assert "Saved" in resp.text

    def test_root_generate_honours_form_index(self, tmp_path):
        reviewer = _mock_reviewer()
        reviewer.generate_document.return_value = {
            "type": "email",
            "href": "/document/out.eml",
            "status": "created",
        }
        app, _ = _make_root_app_with_config(tmp_path, "reviews/intro", reviewer)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            with TestClient(app) as client:
                reviewer.set_index.reset_mock()
                resp = client.post(
                    "/reviews/intro/generate-document/0",
                    data={"index": "bob"},
                )
        assert resp.status_code == 200
        reviewer.set_index.assert_called_with("bob")
        reviewer.generate_document.assert_called_once_with(0, summary=False)
        assert "Download" in resp.text

    def test_root_generate_reports_invalid_form_index(self, tmp_path):
        reviewer = _mock_reviewer()
        reviewer.generate_document.return_value = {
            "type": "email",
            "href": "/document/out.eml",
            "status": "created",
        }
        app, _ = _make_root_app_with_config(tmp_path, "reviews/intro", reviewer)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            with TestClient(app) as client:
                reviewer.set_index.side_effect = KeyError("ghost")
                reviewer.generate_document.reset_mock()
                resp = client.post(
                    "/reviews/intro/generate-document/0",
                    data={"index": "ghost"},
                )
        assert resp.status_code == 200
        assert "Generate document failed" in resp.text
        assert "See server log" in resp.text
        reviewer.generate_document.assert_not_called()

    def _listing_populate_reviewer(self):
        reviewer = _mock_reviewer()
        btn = {
            "type": "PopulateButton",
            "field": "_segment",
            "args": {
                "description": "Segment document",
                "target": "units",
                "compute": {"field": "units", "function": "document_segment"},
            },
        }
        reviewer.get_widget_specs.return_value = [btn]
        reviewer.get_review_specs.return_value = [btn]
        reviewer.get_display_layout.return_value = "inline_list"
        reviewer.working_indices.return_value = ["a", "b"]
        reviewer.get_filter_specs.return_value = []
        reviewer.get_sort_specs.return_value = []
        reviewer.get_filter_state.return_value = {}
        reviewer.get_display_detail_field.return_value = None
        reviewer.get_row_data.return_value = {"Name": "a"}
        reviewer.list_pdf_entries.return_value = []
        reviewer.list_url_entries.return_value = []
        reviewer.list_document_entries.return_value = []
        reviewer.affected_widgets.return_value = []
        reviewer.run_populate.return_value = None
        return reviewer

    def test_root_populate_all_runs_for_working_indices(self, tmp_path):
        reviewer = self._listing_populate_reviewer()
        app, _ = _make_root_app_with_config(tmp_path, "reviews/intro", reviewer)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            with TestClient(app) as client:
                resp = client.post("/reviews/intro/populate-all/_segment")
        assert resp.status_code == 200
        assert reviewer.run_populate.call_count == 2
        assert "Segment document all filtered" in resp.text

    def test_root_populate_all_unknown_field_warns(self, tmp_path):
        reviewer = self._listing_populate_reviewer()
        app, _ = _make_root_app_with_config(tmp_path, "reviews/intro", reviewer)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            with TestClient(app) as client:
                resp = client.post("/reviews/intro/populate-all/missing")
        assert resp.status_code == 200
        assert "No PopulateButton" in resp.text
        reviewer.run_populate.assert_not_called()

    def test_root_populate_honours_form_index(self, tmp_path):
        reviewer = self._listing_populate_reviewer()
        app, _ = _make_root_app_with_config(tmp_path, "reviews/intro", reviewer)
        with patch("referia.assess.web_review.WebReviewer", return_value=reviewer):
            with TestClient(app) as client:
                reviewer.set_index.reset_mock()
                resp = client.post(
                    "/reviews/intro/populate/_segment",
                    data={"index": "bob"},
                )
        assert resp.status_code == 200
        reviewer.set_index.assert_any_call("bob")
        reviewer.run_populate.assert_called_once()

    def test_root_missing_config_404(self, tmp_path):
        app = create_app(root=str(tmp_path))
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/no/such/config")
        assert resp.status_code == 404

    def test_root_intermediate_dir_shows_listing(self, tmp_path):
        """A directory with no _referia.yml but sub-configs shows a listing page."""
        sub = tmp_path / "group" / "project"
        sub.mkdir(parents=True)
        (sub / "_referia.yml").write_text("title: My Project")
        app = create_app(root=str(tmp_path))
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.get("/group/?current=0")
        assert resp.status_code == 200
        assert "project" in resp.text

    def test_root_listing_links_are_clickable_urls(self, tmp_path):
        """Listing entries link to the correct root-relative URL."""
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True)
        (sub / "_referia.yml").write_text("title: test")
        app = create_app(root=str(tmp_path))
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.get("/a/?current=0")
        assert "/a/b/" in resp.text

    def test_root_listing_shows_title_from_yml(self, tmp_path):
        """Title from _referia.yml is shown in the listing."""
        sub = tmp_path / "reviews" / "thesis"
        sub.mkdir(parents=True)
        (sub / "_referia.yml").write_text("title: PhD Thesis Reviews\ndescription: Examining 2024 cohort")
        app = create_app(root=str(tmp_path))
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.get("/reviews/?current=0")
        assert "PhD Thesis Reviews" in resp.text
        assert "Examining 2024 cohort" in resp.text

    def test_root_listing_groups_by_subdirectory(self, tmp_path):
        """Configs sharing an immediate parent are grouped under a section heading."""
        for name in ("intro", "pdfpages"):
            d = tmp_path / "theses" / name
            d.mkdir(parents=True)
            (d / "_referia.yml").write_text(f"title: {name}")
        app = create_app(root=str(tmp_path))
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.get("/?current=0")
        # Group heading links to the intermediate directory
        assert "/theses/" in resp.text
        assert "intro" in resp.text
        assert "pdfpages" in resp.text

    def test_root_listing_intermediate_dir_heading_is_clickable(self, tmp_path):
        """The group heading href navigates to the subdirectory listing."""
        sub = tmp_path / "group" / "deep" / "project"
        sub.mkdir(parents=True)
        (sub / "_referia.yml").write_text("title: Deep Project")
        app = create_app(root=str(tmp_path))
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.get("/group/?current=0")
        # The group heading should link to /group/deep/
        assert 'href="/group/deep/"' in resp.text

    # ── new listing-page feature tests ──────────────────────────────────────

    def test_listing_has_parent_link_for_non_root(self, tmp_path):
        """Listing pages below root contain a '..' link to the parent directory."""
        sub = tmp_path / "theses" / "intro"
        sub.mkdir(parents=True)
        (sub / "_referia.yml").write_text("title: Intro")
        app = create_app(root=str(tmp_path))
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.get("/theses/?current=0")
        assert resp.status_code == 200
        assert "href=\"/\"" in resp.text  # parent link to root

    def test_root_listing_has_no_parent_link(self, tmp_path):
        """Root listing page has no '..' link."""
        sub = tmp_path / "reviews" / "phd"
        sub.mkdir(parents=True)
        (sub / "_referia.yml").write_text("title: PhD")
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/?current=0")
        assert resp.status_code == 200
        assert "&uarr;" not in resp.text  # no up-arrow

    def test_listing_shows_date_from_yml(self, tmp_path):
        """Date field from _referia.yml is shown in the listing."""
        sub = tmp_path / "group" / "project"
        sub.mkdir(parents=True)
        (sub / "_referia.yml").write_text("title: Test\ndate: '2024-03-15'")
        app = create_app(root=str(tmp_path))
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.get("/group/?current=0")
        assert "2024-03-15" in resp.text

    def test_listing_shows_current_badge(self, tmp_path):
        """current: true in _referia.yml shows a 'current' badge."""
        sub = tmp_path / "group" / "active"
        sub.mkdir(parents=True)
        (sub / "_referia.yml").write_text("title: Active\ncurrent: true")
        app = create_app(root=str(tmp_path))
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.get("/group/")
        assert "current" in resp.text

    def test_current_only_defaults_on(self, tmp_path):
        """Root listing defaults to Current only (hides non-current entries)."""
        for name, yml in [("active", "title: A\ncurrent: true"), ("done", "title: B")]:
            d = tmp_path / name
            d.mkdir()
            (d / "_referia.yml").write_text(yml)
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/")
        assert ">A<" in resp.text or "active" in resp.text.lower()
        assert ">B<" not in resp.text
        assert 'name="current" value="1" checked' in resp.text

    def test_current_0_shows_all_entries(self, tmp_path):
        """?current=0 turns Current only off and shows non-current entries."""
        for name, yml in [("active", "title: A\ncurrent: true"), ("done", "title: B")]:
            d = tmp_path / name
            d.mkdir()
            (d / "_referia.yml").write_text(yml)
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/?current=0")
        assert ">A<" in resp.text or "active" in resp.text.lower()
        assert ">B<" in resp.text or "done" in resp.text.lower()
        assert 'name="current" value="1"' in resp.text
        assert 'name="current" value="1" checked' not in resp.text

    def test_clear_leaves_current_on(self, tmp_path):
        """Clear link resets to bare ? so Current only stays on by default."""
        sub = tmp_path / "proj"
        sub.mkdir()
        (sub / "_referia.yml").write_text("title: Project\ncurrent: true")
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/?after=2025-01-01&current=0")
        assert 'href="?"' in resp.text
        assert 'class="clear"' in resp.text

    def test_after_filter_excludes_old_entries(self, tmp_path):
        """?after=2025-01-01 hides configs with dates before that."""
        for name, date in [("old", "2023-06-01"), ("new", "2025-06-01")]:
            d = tmp_path / name
            d.mkdir()
            (d / "_referia.yml").write_text(f"title: {name.title()}\ndate: '{date}'")
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/?after=2025-01-01&current=0")
        assert "Old" not in resp.text
        assert "New" in resp.text

    def test_listing_filter_form_is_present(self, tmp_path):
        """Listing page includes a filter form with date and current controls."""
        sub = tmp_path / "proj"
        sub.mkdir()
        (sub / "_referia.yml").write_text("title: Project\ncurrent: true")
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/")
        assert 'type="date"' in resp.text
        assert 'name="current"' in resp.text
        assert 'name="current" value="1" checked' in resp.text

    # ── Inheritance display ──────────────────────────────────────────────────

    def test_same_group_child_indented_under_parent(self, tmp_path):
        """Child config inherits from a sibling in the same top-level cluster.

        Structure (all in cluster ``people/``):
          people/_referia.yml       ← parent
          people/letters/_referia.yml  ← child (inherits: directory: ../)
        """
        parent_dir = tmp_path / "people"
        child_dir = tmp_path / "people" / "letters"
        parent_dir.mkdir(parents=True)
        child_dir.mkdir(parents=True)
        (parent_dir / "_referia.yml").write_text("title: People")
        (child_dir / "_referia.yml").write_text(
            "title: People Letters\ninherit:\n  directory: ../\n"
        )
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/?current=0")
        text = resp.text
        # Child should be indented (margin-left style applied)
        assert "margin-left" in text
        # The parent-child marker should appear
        assert "&#x21b3;" in text

    def test_same_group_parent_appears_before_child(self, tmp_path):
        """Topological sort puts parent before child when listing a cluster."""
        parent_dir = tmp_path / "people"
        child_dir = tmp_path / "people" / "letters"
        parent_dir.mkdir(parents=True)
        child_dir.mkdir(parents=True)
        (parent_dir / "_referia.yml").write_text("title: People Base")
        (child_dir / "_referia.yml").write_text(
            "title: People Letters\ninherit:\n  directory: ../\n"
        )
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/?current=0")
        pos_parent = resp.text.index("People Base")
        pos_child = resp.text.index("People Letters")
        assert pos_parent < pos_child, "Parent should render before child"

    def test_cross_group_child_shows_inherits_annotation(self, tmp_path):
        """Child in one top-level group that inherits from a different group shows annotation.

        Structure:
          shared/_referia.yml         ← parent (group: shared)
          emails/_referia.yml         ← child  (group: emails, inherits: ../shared)
        """
        (tmp_path / "shared").mkdir()
        (tmp_path / "shared" / "_referia.yml").write_text("title: Shared Config")
        (tmp_path / "emails").mkdir()
        (tmp_path / "emails" / "_referia.yml").write_text(
            "title: Email Reviews\ninherit:\n  directory: ../shared\n"
        )
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/?current=0")
        # The child entry in 'emails' group should have an "inherits" annotation.
        assert "inherits&nbsp;" in resp.text

    def test_no_inheritance_renders_cleanly(self, tmp_path):
        """Listing with no inheritance relationships renders without indent markers."""
        for name in ("alpha", "beta", "gamma"):
            d = tmp_path / name
            d.mkdir()
            (d / "_referia.yml").write_text(f"title: {name.title()}")
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/?current=0")
        # The ↳ indent marker should not appear in the list items.
        assert "&#x21b3;" not in resp.text
        # "inherits&nbsp;" is the visible annotation text — not in CSS class names.
        assert "inherits&nbsp;" not in resp.text

    # ── Error logging and /errors page ──────────────────────────────────────

    def test_parse_error_shows_warning_icon_on_listing(self, tmp_path):
        """A _referia.yml with invalid YAML shows ⚠️ on the listing."""
        bad = tmp_path / "broken"
        bad.mkdir()
        (bad / "_referia.yml").write_text("title: [unclosed bracket")
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/?current=0")
        # The warning icon entity appears for the broken config.
        assert "&#x26A0;" in resp.text

    def test_parse_error_shows_error_banner_on_listing(self, tmp_path):
        """Error banner with link to /errors appears when any config fails to parse."""
        bad = tmp_path / "broken"
        bad.mkdir()
        (bad / "_referia.yml").write_text("title: [unclosed bracket")
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/?current=0")
        assert "error-banner" in resp.text
        assert "/errors" in resp.text

    def test_errors_page_shows_parse_failures(self, tmp_path):
        """GET /errors lists configs that failed YAML parsing."""
        bad = tmp_path / "bad"
        bad.mkdir()
        (bad / "_referia.yml").write_text(": invalid: yaml: :")
        good = tmp_path / "good"
        good.mkdir()
        (good / "_referia.yml").write_text("title: Good Config")
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/errors")
        assert resp.status_code == 200
        assert "YAML parse failures" in resp.text
        # The broken file path should appear
        assert str(bad / "_referia.yml") in resp.text

    def test_errors_page_shows_none_when_all_ok(self, tmp_path):
        """GET /errors shows 'None' in the parse-failures section when all configs parse OK."""
        ok = tmp_path / "ok"
        ok.mkdir()
        (ok / "_referia.yml").write_text("title: Fine")
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/errors")
        assert resp.status_code == 200
        assert "YAML parse failures (0)" in resp.text

    def test_errors_and_listing_omit_parse_exception_text(self, tmp_path):
        """CIP-000E: parse exception strings stay in the log, not HTML."""
        yaml_text = "title: [unclosed bracket"
        marker = _yaml_exception_text(yaml_text)
        bad = tmp_path / "broken"
        bad.mkdir()
        (bad / "_referia.yml").write_text(yaml_text)
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            listing = client.get("/?current=0")
            errors = client.get("/errors")
        assert listing.status_code == 200
        assert errors.status_code == 200
        assert marker not in listing.text
        assert marker not in errors.text
        assert "See server log" in listing.text
        assert "See server log" in errors.text
        assert str(bad / "_referia.yml") in errors.text

    def test_errors_page_omits_load_exception_text(self, tmp_path):
        """CIP-000E: WebReviewer load failures do not put str(exc) in /errors."""
        marker = "UNIQUE_LOAD_FAILURE_xyzzy"
        good = tmp_path / "good"
        good.mkdir()
        (good / "_referia.yml").write_text("title: Good Config\n")
        with patch(
            "referia.assess.web_review.WebReviewer",
            side_effect=RuntimeError(marker),
        ):
            app = create_app(root=str(tmp_path))
            with TestClient(app) as client:
                load_resp = client.get("/good/")
                errors = client.get("/errors")
            registry = list(app.state.load_errors)
        assert load_resp.status_code == 503
        assert "Could not load config" in load_resp.text
        assert "allowed serve roots" not in load_resp.text
        assert marker not in load_resp.text
        assert errors.status_code == 200
        assert marker not in errors.text
        assert marker not in str(registry)
        assert "See server log" in errors.text
        assert str(good / "_referia.yml") in errors.text

    def test_path_escape_load_uses_fixed_hint(self, tmp_path):
        """PathEscape gets a fixed jail hint; str(exc) paths stay out of HTML."""
        from lynguine.access.paths import PathEscapeError

        marker = "/UNIQUE_ESCAPED_PATH_xyzzy/secret"
        good = tmp_path / "jailed"
        good.mkdir()
        (good / "_referia.yml").write_text("title: Needs External Data\n")
        with patch(
            "referia.assess.web_review.WebReviewer",
            side_effect=PathEscapeError(marker, [str(tmp_path)]),
        ):
            app = create_app(root=str(tmp_path))
            with TestClient(app) as client:
                load_resp = client.get("/jailed/")
                errors = client.get("/errors")
            registry = list(app.state.load_errors)
        assert load_resp.status_code == 503
        assert "allowed serve roots" in load_resp.text
        assert marker not in load_resp.text
        assert marker not in errors.text
        assert marker not in str(registry)
        assert "PathEscapeError" in errors.text
        assert "allowed serve roots" in errors.text
        assert str(good / "_referia.yml") in errors.text

    def test_root_log_file_created(self, tmp_path):
        """A referia-server.log file is created at the root when running in root mode."""
        app = create_app(root=str(tmp_path))
        with TestClient(app):
            pass
        assert (tmp_path / "referia-server.log").exists()

    def test_missing_root_raises_filenotfound(self, tmp_path):
        """A non-existent --root fails before FileHandler can traceback."""
        missing = tmp_path / "no-such-serve-root"
        with pytest.raises(FileNotFoundError, match="does not exist"):
            create_app(root=str(missing))
        assert not missing.exists()

    def test_root_that_is_a_file_raises(self, tmp_path):
        not_a_dir = tmp_path / "a-file"
        not_a_dir.write_text("not a directory\n")
        with pytest.raises(NotADirectoryError, match="not a directory"):
            create_app(root=str(not_a_dir))

    def test_health_not_swallowed_by_root_catchall(self, tmp_path):
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["mode"] == "root-server"

    def test_root_slash_returns_listing_not_503(self, tmp_path):
        """GET / in root mode renders the listing page, not a 503 error."""
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/")
        assert resp.status_code == 200
        assert "Reviews under" in resp.text


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

class TestCLIArgumentParsing:
    def test_default_single_config(self):
        from referia.cli import _build_parser
        args = _build_parser().parse_args(["serve"])
        assert args.config == "_referia.yml"
        assert args.directory is None
        assert args.root is None

    def test_root_option_parsed(self):
        from referia.cli import _build_parser
        args = _build_parser().parse_args(["serve", "--root", "/some/path"])
        assert args.root == "/some/path"

    def test_directory_option_parsed(self):
        from referia.cli import _build_parser
        args = _build_parser().parse_args(["serve", "--directory", "/some/path"])
        assert args.directory == "/some/path"

    def test_root_and_directory_mutual_exclusion(self):
        """_serve() should raise SystemExit(1) when both --root and --directory are given."""
        from referia.cli import _serve
        import argparse
        args = argparse.Namespace(
            root="/tmp", directory="/tmp", config="_referia.yml",
            host="127.0.0.1", port=8000,
        )
        with pytest.raises(SystemExit) as exc_info:
            _serve(args)
        assert exc_info.value.code == 1

    def test_missing_root_exits_with_clear_error(self, tmp_path, capsys):
        """_serve() exits 1 with the resolved path when --root does not exist."""
        from referia.cli import _serve
        import argparse
        missing = tmp_path / "personal"
        args = argparse.Namespace(
            root=str(missing), directory=None, config="_referia.yml",
            host="127.0.0.1", port=8000,
        )
        with pytest.raises(SystemExit) as exc_info:
            _serve(args)
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "does not exist" in err
        assert str(missing) in err
