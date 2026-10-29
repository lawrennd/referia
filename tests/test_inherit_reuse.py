"""CIP-001C inherit.reuse — catalog views share compute/review; candidates do not."""

from __future__ import annotations

from pathlib import Path

from referia.config.inherit_view import PARENT_ASSESSOR_LINK_KEY
from referia.config.interface import Interface


def _catalog_cfg(*, extra: str = "") -> str:
    return (
        "referia_config_version: 2\n"
        "title: Catalog\n"
        "strict_columns: false\n"
        "writable: true\n"
        "allocation:\n"
        "  type: fake\n"
        "  index: name\n"
        "  nrows: 1\n"
        "  cols:\n"
        "    - name\n"
        "review:\n"
        "  - type: Checkbox\n"
        "    field: complete\n"
        "compute:\n"
        "  - field: today\n"
        "    function: today\n"
        "filters:\n"
        "  - field: complete\n"
        "    type: boolean\n"
        f"{extra}"
    )


def _load(path: Path) -> Interface:
    return Interface.from_file(
        "_referia.yml",
        str(path),
        allowed_roots=[str(path.parent.resolve())],
    )


def test_default_inherit_still_ignores_parent_review(tmp_path):
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    parent.mkdir()
    child.mkdir()
    (parent / "_referia.yml").write_text(_catalog_cfg())
    (child / "_referia.yml").write_text(
        "referia_config_version: 2\n"
        "title: Candidate\n"
        "strict_columns: false\n"
        "allocation:\n"
        "  type: fake\n"
        "  index: name\n"
        "  nrows: 1\n"
        "  cols:\n"
        "    - name\n"
        "inherit:\n"
        "  directory: ../parent\n"
        "review:\n"
        "  - type: Textarea\n"
        "    field: childComment\n"
    )
    iface = _load(child)
    assert "review" in iface._data["inherit"]["ignore"]
    assert "compute" in iface._data["inherit"]["ignore"]
    assert iface["review"][0]["field"] == "childComment"
    assert not any(
        isinstance(e, dict) and e.get("field") == "complete" for e in iface["review"]
    )
    viewer = iface["viewer"]
    entries = viewer if isinstance(viewer, list) else [viewer]
    assert any(
        isinstance(e, dict) and e.get(PARENT_ASSESSOR_LINK_KEY) for e in entries
    )


def test_reuse_inherits_parent_review_and_compute(tmp_path):
    parent = tmp_path / "catalog"
    child = tmp_path / "today"
    parent.mkdir()
    child.mkdir()
    (parent / "_referia.yml").write_text(_catalog_cfg())
    (child / "_referia.yml").write_text(
        "referia_config_version: 2\n"
        "title: Today\n"
        "strict_columns: false\n"
        "writable: true\n"
        "allocation:\n"
        "  type: fake\n"
        "  index: name\n"
        "  nrows: 1\n"
        "  cols:\n"
        "    - name\n"
        "inherit:\n"
        "  directory: ../catalog\n"
        "  filename: _referia.yml\n"
        "  writable: true\n"
        "  reuse: [input, output, compute, review, filters, sort]\n"
        "  ignore: [viewer]\n"
        "viewer:\n"
        "  - liquid: Today chrome\n"
    )
    iface = _load(child)
    ignore = iface._data["inherit"]["ignore"]
    assert "review" not in ignore
    assert "compute" not in ignore
    assert "viewer" in ignore
    assert iface["review"][0]["field"] == "complete"
    assert iface["compute"][0]["field"] == "today"
    assert iface["filters"][0]["field"] == "complete"
    viewer = iface["viewer"]
    entries = viewer if isinstance(viewer, list) else [viewer]
    assert not any(
        isinstance(e, dict) and e.get(PARENT_ASSESSOR_LINK_KEY) for e in entries
    )
    assert any("Today chrome" in str(e) for e in entries)


def test_reuse_string_is_accepted(tmp_path):
    parent = tmp_path / "catalog"
    child = tmp_path / "year"
    parent.mkdir()
    child.mkdir()
    (parent / "_referia.yml").write_text(_catalog_cfg())
    (child / "_referia.yml").write_text(
        "referia_config_version: 2\n"
        "title: Year\n"
        "strict_columns: false\n"
        "allocation:\n"
        "  type: fake\n"
        "  index: name\n"
        "  nrows: 1\n"
        "  cols:\n"
        "    - name\n"
        "inherit:\n"
        "  directory: ../catalog\n"
        "  reuse: review\n"
        "  ignore: [viewer]\n"
    )
    iface = _load(child)
    assert "review" not in iface._data["inherit"]["ignore"]
    assert iface["review"][0]["field"] == "complete"


def test_scalar_viewer_prepends_parent_link(tmp_path):
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    parent.mkdir()
    child.mkdir()
    (parent / "_referia.yml").write_text(_catalog_cfg())
    (child / "_referia.yml").write_text(
        "referia_config_version: 2\n"
        "title: Candidate\n"
        "strict_columns: false\n"
        "allocation:\n"
        "  type: fake\n"
        "  index: name\n"
        "  nrows: 1\n"
        "  cols:\n"
        "    - name\n"
        "inherit:\n"
        "  directory: ../parent\n"
        "viewer: Child chrome\n"
    )
    iface = _load(child)
    viewer = iface["viewer"]
    assert isinstance(viewer, list)
    assert viewer[1] == "Child chrome"
    assert isinstance(viewer[0], dict) and viewer[0].get(PARENT_ASSESSOR_LINK_KEY)


def test_empty_append_still_adds_viewer(tmp_path):
    parent = tmp_path / "parent"
    child = tmp_path / "child"
    parent.mkdir()
    child.mkdir()
    (parent / "_referia.yml").write_text(_catalog_cfg())
    (child / "_referia.yml").write_text(
        "referia_config_version: 2\n"
        "title: Candidate\n"
        "strict_columns: false\n"
        "allocation:\n"
        "  type: fake\n"
        "  index: name\n"
        "  nrows: 1\n"
        "  cols:\n"
        "    - name\n"
        "inherit:\n"
        "  directory: ../parent\n"
        "  append: []\n"
    )
    iface = _load(child)
    assert "viewer" in iface._data["inherit"]["append"]
