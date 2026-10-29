"""CIP-001C example catalog: schedule columns, exclude, sibling views."""

from __future__ import annotations

from pathlib import Path

import yaml

EXAMPLE = (
    Path(__file__).resolve().parents[1] / "examples" / "overview_inline_list"
)


def _load(rel: str) -> dict:
    return yaml.safe_load((EXAMPLE / rel).read_text())


def test_example_root_declares_schedule_store_and_exclude():
    root = _load("_referia.yml")
    source = root["input"]["source"][0]
    assert "today/**" in source["exclude"]
    assert "year/**" in source["exclude"]
    assert source.get("include_start_directory") is False
    assert root["output"]["columns"] == ["complete", "due", "event", "notes"]
    compute_fields = [c["field"] for c in root["input"]["compute"]]
    assert "today" in compute_fields
    assert "when" not in compute_fields
    assert "on_today" not in compute_fields
    review_fields = [r.get("field") for r in root["review"] if isinstance(r, dict)]
    assert "event" in review_fields
    assert "due" in review_fields
    assert "notes" in review_fields
    defaults = root["display"]["filter_defaults"]
    assert "when" in defaults
    assert "date" not in defaults


def test_example_views_reuse_parent_and_own_chrome():
    today = _load("today/_referia.yml")
    year = _load("year/_referia.yml")
    for view in (today, year):
        inherit = view["inherit"]
        assert inherit["directory"] == "../"
        assert inherit["writable"] is True
        assert "review" in inherit["reuse"]
        assert "compute" in inherit["reuse"]
        assert "viewer" in inherit["ignore"]
        assert view["display"]["layout"] == "inline_list"
    assert today["display"]["filter_defaults"]["_group"] == "none"
    assert today["display"]["filter_defaults"]["on_today"] is True
    assert year["display"]["filter_defaults"]["_group"] == "month"
    assert year["display"]["filter_defaults"]["when"]["after"] == "2026-10-01"


def test_example_scores_seed_event_and_due():
    rows = yaml.safe_load((EXAMPLE / "info" / "overview-scores.yml").read_text())
    by_src = {row["sourceDirectory"]: row for row in rows}
    assert by_src["spring"]["event"] == "20260301"
    assert by_src["autumn"]["due"] == "20261115"
    autumn = _load("autumn/_referia.yml")
    assert str(autumn["due"]) == "2026-11-15"
    assert "due" not in _load("spring/_referia.yml")


def test_inherited_today_keeps_store_field_column_names(tmp_path):
    """Inherit must not rewrite store_fields.directory into a path (CIP-0018)."""
    from referia.assess.data import CustomDataFrame
    from referia.config.interface import Interface

    parent = tmp_path / "root"
    child = parent / "today"
    work = parent / "work"
    parent.mkdir()
    child.mkdir()
    work.mkdir()
    (work / "_referia.yml").write_text(
        "referia_config_version: 2\n"
        "title: Work\n"
        "date: 2026-10-01\n"
        "allocation:\n  type: fake\n  index: name\n  nrows: 1\n  cols: [name]\n"
    )
    (parent / "_referia.yml").write_text(
        "referia_config_version: 2\n"
        "writable: true\n"
        "input:\n"
        "  type: yaml_directory\n"
        "  index: sourceFile\n"
        "  source:\n"
        "    - directory: .\n"
        "      glob: '**/_referia.yml'\n"
        "      recursive: true\n"
        "      include_start_directory: false\n"
        "      exclude: [today/**]\n"
        "  fields: [title, date]\n"
        "  store_fields:\n"
        "    directory: sourceDirectory\n"
        "    filename: sourceFile\n"
        "    root: sourceRoot\n"
        "output:\n"
        "  type: yaml\n"
        "  index: sourceFile\n"
        "  filename: catalog-scores.yml\n"
        "  directory: ./info\n"
        "  columns: [complete, due, event, notes]\n"
    )
    (child / "_referia.yml").write_text(
        "referia_config_version: 2\n"
        "writable: true\n"
        "inherit:\n"
        "  directory: ../\n"
        "  filename: _referia.yml\n"
        "  writable: true\n"
        "  reuse: [input, output]\n"
        "  ignore: [viewer]\n"
    )
    iface = Interface.from_file(
        "_referia.yml",
        str(child),
        allowed_roots=[str(tmp_path.resolve())],
    )
    cdf = CustomDataFrame.from_flow(iface)
    frame = cdf._d["input"]
    assert "sourceDirectory" in list(frame.columns)
    assert all(
        not str(col).endswith("/sourceDirectory") for col in frame.columns
    )
    assert "_referia.yml" in list(frame.index)
