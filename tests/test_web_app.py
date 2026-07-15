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

    def test_root_slash_returns_listing_in_root_mode(self, tmp_path):
        """In root mode, GET / returns the directory listing (not 503)."""
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/")
        assert resp.status_code == 200
        assert "Reviews under" in resp.text


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
                resp = client.get("/group/")
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
                resp = client.get("/a/")
        assert "/a/b/" in resp.text

    def test_root_listing_shows_title_from_yml(self, tmp_path):
        """Title from _referia.yml is shown in the listing."""
        sub = tmp_path / "reviews" / "thesis"
        sub.mkdir(parents=True)
        (sub / "_referia.yml").write_text("title: PhD Thesis Reviews\ndescription: Examining 2024 cohort")
        app = create_app(root=str(tmp_path))
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.get("/reviews/")
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
                resp = client.get("/")
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
                resp = client.get("/group/")
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
                resp = client.get("/theses/")
        assert resp.status_code == 200
        assert "href=\"/\"" in resp.text  # parent link to root

    def test_root_listing_has_no_parent_link(self, tmp_path):
        """Root listing page has no '..' link."""
        sub = tmp_path / "reviews" / "phd"
        sub.mkdir(parents=True)
        (sub / "_referia.yml").write_text("title: PhD")
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/")
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
                resp = client.get("/group/")
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

    def test_current_only_filter_hides_non_current(self, tmp_path):
        """?current=1 hides entries where current is false/absent."""
        for name, yml in [("active", "title: A\ncurrent: true"), ("done", "title: B")]:
            d = tmp_path / name
            d.mkdir()
            (d / "_referia.yml").write_text(yml)
        app = create_app(root=str(tmp_path))
        with patch("referia.assess.web_review.WebReviewer", return_value=_mock_reviewer()):
            with TestClient(app) as client:
                resp = client.get("/?current=1")
        assert "title: A" not in resp.text  # raw yml not shown
        assert ">A<" in resp.text or "active" in resp.text.lower()
        # The non-current entry should not be visible
        assert ">B<" not in resp.text

    def test_after_filter_excludes_old_entries(self, tmp_path):
        """?after=2025-01-01 hides configs with dates before that."""
        for name, date in [("old", "2023-06-01"), ("new", "2025-06-01")]:
            d = tmp_path / name
            d.mkdir()
            (d / "_referia.yml").write_text(f"title: {name.title()}\ndate: '{date}'")
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/?after=2025-01-01")
        assert "Old" not in resp.text
        assert "New" in resp.text

    def test_listing_filter_form_is_present(self, tmp_path):
        """Listing page includes a filter form with date and current controls."""
        sub = tmp_path / "proj"
        sub.mkdir()
        (sub / "_referia.yml").write_text("title: Project")
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/")
        assert 'type="date"' in resp.text
        assert 'name="current"' in resp.text

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
