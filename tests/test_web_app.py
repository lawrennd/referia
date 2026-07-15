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

    def test_single_config_routes_return_503_in_root_mode(self, tmp_path):
        """In root mode, the existing single-config routes return 503 (no reviewer)."""
        app = create_app(root=str(tmp_path))
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/")
        assert resp.status_code == 503


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

    def test_health_not_swallowed_by_root_catchall(self, tmp_path):
        app = create_app(root=str(tmp_path))
        with TestClient(app) as client:
            resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["mode"] == "root-server"

    def test_single_config_slash_still_returns_503_in_root_mode(self, tmp_path):
        """GET / (no config path) hits the single-config route, which returns 503."""
        app = create_app(root=str(tmp_path))
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/")
        assert resp.status_code == 503


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
