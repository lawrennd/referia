"""Tests for referia.web.path_safety (CIP-000E)."""

from __future__ import annotations

import pytest

from referia.web.path_safety import PathOutsideRootError, safe_path_under_root
from referia.web.routes import _list_sub_configs, _resolve_config_path


class TestSafePathUnderRoot:
    def test_empty_path_returns_root(self, tmp_path):
        assert safe_path_under_root(tmp_path, "") == tmp_path.resolve()
        assert safe_path_under_root(tmp_path, "/") == tmp_path.resolve()

    def test_nested_relative_path(self, tmp_path):
        nested = tmp_path / "reviews" / "intro"
        nested.mkdir(parents=True)
        assert safe_path_under_root(tmp_path, "reviews/intro") == nested.resolve()

    def test_dotdot_segment_rejected(self, tmp_path):
        with pytest.raises(PathOutsideRootError):
            safe_path_under_root(tmp_path, "../../etc/passwd")

    def test_parent_in_middle_rejected(self, tmp_path):
        (tmp_path / "reviews").mkdir()
        with pytest.raises(PathOutsideRootError):
            safe_path_under_root(tmp_path, "reviews/../..")

    def test_leading_slash_is_relative_to_root(self, tmp_path):
        """URL paths are stripped of slashes, so they cannot name OS absolute paths."""
        nested = tmp_path / "etc" / "passwd"
        nested.mkdir(parents=True)
        assert safe_path_under_root(tmp_path, "/etc/passwd") == nested.resolve()


class TestListSubConfigsPathSafety:
    def test_traversal_returns_empty_list(self, tmp_path):
        assert _list_sub_configs(str(tmp_path), "../../etc") == []

    def test_valid_subdir_finds_yml(self, tmp_path):
        nested = tmp_path / "group" / "project"
        nested.mkdir(parents=True)
        (nested / "_referia.yml").write_text("title: Project")
        configs = _list_sub_configs(str(tmp_path), "group")
        assert any(c["title"] == "Project" for c in configs)


class TestResolveConfigPathGenericErrors:
    def test_missing_config_detail_has_no_user_path(self, tmp_path):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _resolve_config_path(str(tmp_path), "secret-name/path")
        assert exc_info.value.status_code == 404
        assert "secret-name" not in str(exc_info.value.detail)
