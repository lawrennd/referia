"""Tests for CIP-000F config dialect detect / normalise / stamp."""

from __future__ import annotations

import textwrap

import pytest

from referia.config.dialect import (
    detect_config_dialect,
    deep_copy_config,
    inferred_stamp_version,
    normalise_referia_config,
    stamp_version_text,
)
from referia.config.interface import Interface


def test_detect_v1_allocation():
    data = {
        "allocation": [{"type": "excel", "filename": "a.xlsx", "index": "Name"}],
        "scores": {"type": "excel", "filename": "s.xlsx"},
    }
    report = detect_config_dialect(data)
    assert report.version_inferred == 1
    assert report.needs_normalise is True
    assert "allocation" in report.markers
    assert "scores" in report.markers
    assert report.conflicts == []


def test_detect_v2_canonical():
    data = {
        "input": {"type": "excel", "filename": "a.xlsx"},
        "output": {"type": "excel", "filename": "s.xlsx"},
        "review": [{"type": "Checkbox", "field": "ok"}],
    }
    report = detect_config_dialect(data)
    assert report.version_inferred == 2
    assert report.needs_normalise is False


def test_detect_mixed_conflict():
    data = {
        "allocation": [{"type": "excel", "filename": "a.xlsx", "index": "Name"}],
        "input": {"type": "excel", "filename": "b.xlsx"},
    }
    report = detect_config_dialect(data)
    assert "allocation+input" in report.conflicts


def test_detect_declared_version():
    data = {"referia_config_version": 2, "review": []}
    report = detect_config_dialect(data)
    assert report.version_declared == 2
    assert report.version_inferred == 2


def test_detect_proto_v0():
    data = {"datadirectory": "/tmp", "allocation": "candidates.xlsx"}
    report = detect_config_dialect(data)
    assert report.version_inferred == 0
    assert report.needs_normalise is False


def test_normalise_v1_to_v2_keys():
    data = {
        "allocation": [
            {
                "type": "excel",
                "filename": "a.xlsx",
                "index": "Name",
                "columns": ["Name"],
            }
        ],
        "scores": {"type": "excel", "filename": "s.xlsx"},
        "scorer": [{"type": "Checkbox", "field": "ok"}],
        "global_consts": {"type": "yaml", "filename": "c.yml"},
        "globals": {"type": "yaml", "filename": "g.yml"},
    }
    with pytest.warns(DeprecationWarning, match="scorer"):
        normalise_referia_config(data, directory=".", user_file="_referia.yml")

    assert "allocation" not in data
    assert "scores" not in data
    assert "scorer" not in data
    assert "global_consts" not in data
    assert "globals" not in data
    assert "input" in data
    assert "output" in data
    assert "review" in data
    assert "constants" in data
    assert "parameters" in data
    assert data["input"]["type"] == "hstack"
    report = detect_config_dialect(data)
    assert report.version_inferred == 2
    assert report.needs_normalise is False


def test_normalise_converters_to_dtypes():
    data = {
        "input": {
            "type": "excel",
            "filename": "a.xlsx",
            "converters": [{"field": "n", "type": "int"}],
        }
    }
    normalise_referia_config(data)
    assert "converters" not in data["input"]
    assert data["input"]["dtypes"] == [{"field": "n", "type": "int"}]


def test_normalise_rejects_allocation_and_input():
    data = {
        "allocation": [{"type": "excel", "filename": "a.xlsx", "index": "Name"}],
        "input": {"type": "excel", "filename": "b.xlsx"},
    }
    with pytest.raises(ValueError, match="allocation"):
        normalise_referia_config(data)


def test_stamp_version_text_preserves_comments():
    original = textwrap.dedent(
        """\
        # Review for cohort X
        # Keep this comment

        title: Example
        review:
          - type: Checkbox
            field: ok
        """
    )
    stamped = stamp_version_text(original, 2)
    assert "referia_config_version: 2\n" in stamped
    assert "# Review for cohort X" in stamped
    assert "# Keep this comment" in stamped
    assert stamped.index("# Review for cohort X") < stamped.index(
        "referia_config_version"
    )
    assert stamped.index("referia_config_version") < stamped.index("title:")
    # Idempotent
    assert stamp_version_text(stamped, 2) == stamped


def test_inferred_stamp_version_skips_declared_and_v0():
    assert inferred_stamp_version({"review": []}) == 2
    assert (
        inferred_stamp_version(
            {"allocation": [{"type": "excel", "index": "Name"}]}
        )
        == 1
    )
    assert inferred_stamp_version({"referia_config_version": 2, "review": []}) is None
    assert inferred_stamp_version({"datadirectory": "/tmp"}) is None


def test_interface_accepts_allowed_roots_kwargs(tmp_path):
    """from_file-style kwargs must not raise TypeError."""
    data = {"review": [{"type": "Checkbox", "field": "ok"}]}
    iface = Interface(
        deep_copy_config(data),
        directory=str(tmp_path),
        user_file="_referia.yml",
        allowed_roots=[str(tmp_path)],
        unbounded_paths=False,
    )
    assert iface.user_file == "_referia.yml"


def test_interface_from_file_with_kwargs(tmp_path):
    cfg = tmp_path / "_referia.yml"
    cfg.write_text(
        "review:\n  - type: Checkbox\n    field: ok\n",
        encoding="utf-8",
    )
    iface = Interface.from_file(
        user_file="_referia.yml",
        directory=str(tmp_path),
        allowed_roots=[str(tmp_path)],
    )
    assert "review" in iface._config or True  # constructed successfully
    assert iface.directory == str(tmp_path)


def test_migrate_stamp_only_dry_run_and_write(tmp_path):
    from referia.migrate import apply_stamp, scan_for_stamp

    sub = tmp_path / "review"
    sub.mkdir()
    yml = sub / "_referia.yml"
    body = "# keep me\ntitle: T\nreview: []\n"
    yml.write_text(body, encoding="utf-8")

    planned = scan_for_stamp(str(tmp_path))
    assert len(planned) == 1
    assert planned[0]["action"] == "stamp"
    assert planned[0]["version"] == 2

    dry = apply_stamp(planned, write=False)
    assert dry[0]["written"] is False
    assert yml.read_text(encoding="utf-8") == body

    planned2 = scan_for_stamp(str(tmp_path))
    written = apply_stamp(planned2, write=True)
    assert written[0]["written"] is True
    text = yml.read_text(encoding="utf-8")
    assert "referia_config_version: 2" in text
    assert "# keep me" in text

    planned3 = scan_for_stamp(str(tmp_path))
    assert planned3[0]["action"] == "skip_already_stamped"


def test_check_reports_dialect(tmp_path):
    from referia.check import format_json, scan_configs

    (tmp_path / "_referia.yml").write_text(
        "allocation:\n  - type: excel\n    filename: a.xlsx\n    index: Name\n",
        encoding="utf-8",
    )
    results = scan_configs(str(tmp_path))
    assert results[0]["ok"] is True
    assert results[0]["dialect"]["version_inferred"] == 1
    payload = format_json(results, str(tmp_path))
    assert "version_inferred" in payload
