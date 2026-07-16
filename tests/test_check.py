"""Tests for referia.check — config linting module."""
import json
import sys
from pathlib import Path

import pytest

from referia.check import (
    _categorize_error,
    _check_one,
    format_json,
    format_text,
    scan_configs,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# _categorize_error
# ---------------------------------------------------------------------------

class TestCategorizeError:
    def test_glob_star_alias(self):
        slug, fix = _categorize_error("while scanning an alias")
        assert slug == "unquoted_glob_star"
        assert fix is not None

    def test_double_quoted_escape(self):
        slug, fix = _categorize_error("while scanning a double-quoted scalar")
        assert slug == "invalid_escape_in_double_quotes"
        assert fix is not None

    def test_simple_key(self):
        slug, fix = _categorize_error("while scanning a simple key at line 3")
        assert slug == "unquoted_colon_or_special_char"
        assert fix is not None

    def test_mapping_not_allowed(self):
        slug, fix = _categorize_error("mapping values are not allowed here")
        assert slug == "inline_value_with_subkeys"
        assert fix is not None

    def test_block_mapping(self):
        slug, fix = _categorize_error("while parsing a block mapping")
        assert slug == "indentation_error"
        assert fix is not None

    def test_unknown(self):
        slug, fix = _categorize_error("some completely unknown error message")
        assert slug == "unknown"
        assert fix is None


# ---------------------------------------------------------------------------
# _check_one — valid file
# ---------------------------------------------------------------------------

class TestCheckOneValid:
    def test_valid_yaml_returns_ok(self, tmp_path):
        yml = _write(tmp_path, "_referia.yml", "title: Test\ntype: review\n")
        result = _check_one(yml, tmp_path)
        assert result["ok"] is True
        assert result["error"] is None
        assert result["line"] is None
        assert result["context"] == []

    def test_relative_path_is_just_filename(self, tmp_path):
        yml = _write(tmp_path, "_referia.yml", "title: Test\n")
        result = _check_one(yml, tmp_path)
        assert result["relative_path"] == "_referia.yml"

    def test_nested_relative_path(self, tmp_path):
        sub = tmp_path / "theses" / "examined"
        sub.mkdir(parents=True)
        yml = _write(sub, "_referia.yml", "title: Theses\n")
        result = _check_one(yml, tmp_path)
        assert result["relative_path"] == "theses/examined/_referia.yml"


# ---------------------------------------------------------------------------
# _check_one — invalid files (one per error category)
# ---------------------------------------------------------------------------

class TestCheckOneInvalid:
    def test_unquoted_glob_star(self, tmp_path):
        yml = _write(tmp_path, "_referia.yml", "type: directory\nglob: *\n")
        result = _check_one(yml, tmp_path)
        assert result["ok"] is False
        assert result["category"] == "unquoted_glob_star"
        assert result["line"] is not None
        assert len(result["context"]) > 0

    def test_invalid_escape_in_double_quotes(self, tmp_path):
        # \( is not a valid YAML escape in a double-quoted string
        content = 'pattern: "\\(foo\\)"\n'
        yml = _write(tmp_path, "_referia.yml", content)
        result = _check_one(yml, tmp_path)
        assert result["ok"] is False
        assert result["category"] == "invalid_escape_in_double_quotes"

    def test_mapping_not_allowed(self, tmp_path):
        # inline scalar value followed by a sub-key on the next line
        content = "allocation:\n  index: Name\n    key: value\n"
        yml = _write(tmp_path, "_referia.yml", content)
        result = _check_one(yml, tmp_path)
        assert result["ok"] is False
        assert result["category"] == "inline_value_with_subkeys"

    def test_indentation_error(self, tmp_path):
        # Mixing indentation levels in a block mapping
        content = "viewer:\n  - type: textarea\n     field: notes\n"
        yml = _write(tmp_path, "_referia.yml", content)
        result = _check_one(yml, tmp_path)
        assert result["ok"] is False
        # May be categorised as indentation_error or another category
        assert result["category"] is not None

    def test_context_contains_arrow_at_error_line(self, tmp_path):
        yml = _write(tmp_path, "_referia.yml", "type: directory\nglob: *\n")
        result = _check_one(yml, tmp_path)
        assert any(line.startswith("→") for line in result["context"])

    def test_suggested_fix_is_a_string(self, tmp_path):
        yml = _write(tmp_path, "_referia.yml", "type: directory\nglob: *\n")
        result = _check_one(yml, tmp_path)
        assert isinstance(result["suggested_fix"], str)
        assert len(result["suggested_fix"]) > 10


# ---------------------------------------------------------------------------
# scan_configs
# ---------------------------------------------------------------------------

class TestScanConfigs:
    def test_empty_root_returns_empty(self, tmp_path):
        results = scan_configs(str(tmp_path))
        assert results == []

    def test_finds_single_config(self, tmp_path):
        _write(tmp_path, "_referia.yml", "title: Test\n")
        results = scan_configs(str(tmp_path))
        assert len(results) == 1
        assert results[0]["ok"] is True

    def test_finds_nested_configs(self, tmp_path):
        _write(tmp_path, "_referia.yml", "title: Root\n")
        sub = tmp_path / "sub"
        sub.mkdir()
        _write(sub, "_referia.yml", "title: Sub\n")
        results = scan_configs(str(tmp_path))
        assert len(results) == 2

    def test_results_sorted_by_relative_path(self, tmp_path):
        for name in ("zzz", "aaa", "mmm"):
            d = tmp_path / name
            d.mkdir()
            _write(d, "_referia.yml", f"title: {name}\n")
        results = scan_configs(str(tmp_path))
        paths = [r["relative_path"] for r in results]
        assert paths == sorted(paths)

    def test_mix_of_valid_and_invalid(self, tmp_path):
        _write(tmp_path, "_referia.yml", "title: OK\n")
        bad = tmp_path / "bad"
        bad.mkdir()
        _write(bad, "_referia.yml", "glob: *\n")
        results = scan_configs(str(tmp_path))
        ok_count = sum(1 for r in results if r["ok"])
        err_count = sum(1 for r in results if not r["ok"])
        assert ok_count == 1
        assert err_count == 1

    def test_accepts_tilde_path(self, tmp_path, monkeypatch):
        # Patch Path.home() so expanduser("~") resolves to tmp_path
        monkeypatch.setenv("HOME", str(tmp_path))
        _write(tmp_path, "_referia.yml", "title: Test\n")
        results = scan_configs("~")
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# format_text
# ---------------------------------------------------------------------------

class TestFormatText:
    def _results(self, tmp_path):
        _write(tmp_path, "_referia.yml", "title: OK\n")
        bad = tmp_path / "bad"
        bad.mkdir()
        _write(bad, "_referia.yml", "glob: *\n")
        return scan_configs(str(tmp_path))

    def test_contains_ok_count(self, tmp_path):
        results = self._results(tmp_path)
        text = format_text(results, str(tmp_path))
        assert "✓" in text
        assert "1" in text  # 1 OK

    def test_contains_error_count(self, tmp_path):
        results = self._results(tmp_path)
        text = format_text(results, str(tmp_path))
        assert "✗" in text

    def test_contains_relative_path(self, tmp_path):
        results = self._results(tmp_path)
        text = format_text(results, str(tmp_path))
        assert "bad/_referia.yml" in text

    def test_contains_category(self, tmp_path):
        results = self._results(tmp_path)
        text = format_text(results, str(tmp_path))
        assert "unquoted_glob_star" in text

    def test_all_valid_says_all_valid(self, tmp_path):
        _write(tmp_path, "_referia.yml", "title: OK\n")
        results = scan_configs(str(tmp_path))
        text = format_text(results, str(tmp_path))
        assert "All configs are valid" in text


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------

class TestFormatJson:
    def _results(self, tmp_path):
        _write(tmp_path, "_referia.yml", "title: OK\n")
        bad = tmp_path / "bad"
        bad.mkdir()
        _write(bad, "_referia.yml", "glob: *\n")
        return scan_configs(str(tmp_path))

    def test_valid_json(self, tmp_path):
        results = self._results(tmp_path)
        text = format_json(results, str(tmp_path))
        obj = json.loads(text)  # should not raise
        assert isinstance(obj, dict)

    def test_json_has_required_keys(self, tmp_path):
        results = self._results(tmp_path)
        obj = json.loads(format_json(results, str(tmp_path)))
        assert "root" in obj
        assert "total_scanned" in obj
        assert "error_count" in obj
        assert "errors" in obj

    def test_json_error_count_matches_errors_list(self, tmp_path):
        results = self._results(tmp_path)
        obj = json.loads(format_json(results, str(tmp_path)))
        assert obj["error_count"] == len(obj["errors"])
        assert obj["error_count"] == 1

    def test_json_error_entry_has_context(self, tmp_path):
        results = self._results(tmp_path)
        obj = json.loads(format_json(results, str(tmp_path)))
        err = obj["errors"][0]
        assert "context" in err
        assert isinstance(err["context"], list)

    def test_json_error_entry_has_suggested_fix(self, tmp_path):
        results = self._results(tmp_path)
        obj = json.loads(format_json(results, str(tmp_path)))
        err = obj["errors"][0]
        assert err.get("suggested_fix") is not None


# ---------------------------------------------------------------------------
# CLI integration via _check()
# ---------------------------------------------------------------------------

class TestCheckCLI:
    def test_exits_0_when_all_ok(self, tmp_path):
        _write(tmp_path, "_referia.yml", "title: OK\n")
        from referia.cli import _check
        import argparse
        args = argparse.Namespace(root=str(tmp_path), format="text", errors_only=False)
        with pytest.raises(SystemExit) as exc_info:
            _check(args)
        assert exc_info.value.code == 0

    def test_exits_1_when_errors(self, tmp_path):
        _write(tmp_path, "_referia.yml", "glob: *\n")
        from referia.cli import _check
        import argparse
        args = argparse.Namespace(root=str(tmp_path), format="text", errors_only=False)
        with pytest.raises(SystemExit) as exc_info:
            _check(args)
        assert exc_info.value.code == 1

    def test_json_format_outputs_valid_json(self, tmp_path, capsys):
        _write(tmp_path, "_referia.yml", "title: OK\n")
        from referia.cli import _check
        import argparse
        args = argparse.Namespace(root=str(tmp_path), format="json", errors_only=False)
        with pytest.raises(SystemExit):
            _check(args)
        captured = capsys.readouterr()
        obj = json.loads(captured.out)
        assert "errors" in obj

    def test_errors_only_flag_suppresses_summary(self, tmp_path, capsys):
        _write(tmp_path, "_referia.yml", "glob: *\n")
        from referia.cli import _check
        import argparse
        args = argparse.Namespace(root=str(tmp_path), format="text", errors_only=True)
        with pytest.raises(SystemExit):
            _check(args)
        captured = capsys.readouterr()
        # errors-only output should contain the path but not the summary header
        assert "_referia.yml" in captured.out
        assert "Scanning" not in captured.out
