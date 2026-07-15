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
