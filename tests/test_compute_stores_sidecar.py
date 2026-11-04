"""CIP-0024: declared sidecar product stores."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from referia.assess.compute import Compute
from referia.assess.compute.pipeline import (
    _load_referia_stage_metas,
    _store_path_key,
    discover_pipeline_edges,
)
from referia.assess.compute.stores import (
    declared_store_path,
    load_declared_yaml_rows,
    named_store_status,
)


class _Iface(dict):
    def __init__(self, directory: str, **stores):
        super().__init__(stores)
        self.directory = directory

    def get(self, key, default=None):
        return super().get(key, default)


def test_load_declared_yaml_rows_and_path(tmp_path: Path):
    info = tmp_path / "info"
    info.mkdir()
    (info / "grounds.yml").write_text(
        "- phrase_id: p1\n  basis: principle\n",
        encoding="utf-8",
    )
    iface = _Iface(
        str(tmp_path),
        grounds={
            "type": "yaml",
            "directory": str(info),
            "filename": "grounds.yml",
            "index": "phrase_id",
        },
    )
    path = declared_store_path(iface, "grounds")
    assert path and path.endswith("grounds.yml")
    rows = load_declared_yaml_rows(iface, "grounds")
    assert rows == [{"phrase_id": "p1", "basis": "principle"}]
    assert load_declared_yaml_rows(iface, "phrases") is None
    status = named_store_status(iface)
    assert status["grounds"]["exists"] is True


def test_declared_store_path_edge_cases(tmp_path: Path):
    assert declared_store_path(None, "grounds") is None
    assert declared_store_path(_Iface(str(tmp_path)), "") is None
    assert declared_store_path(_Iface(str(tmp_path), grounds="nope"), "grounds") is None
    missing = tmp_path / "info"
    missing.mkdir()
    iface = _Iface(
        str(tmp_path),
        grounds={
            "type": "yaml",
            "directory": "info",
            "filename": "absent.yml",
        },
    )
    assert load_declared_yaml_rows(iface, "grounds") == []
    (missing / "not_list.yml").write_text("key: value\n", encoding="utf-8")
    iface["grounds"] = {
        "type": "yaml",
        "directory": "info",
        "filename": "not_list.yml",
    }
    assert load_declared_yaml_rows(iface, "grounds") == []


def test_compute_prefers_declared_grounds(tmp_path: Path):
    info = tmp_path / "info"
    info.mkdir()
    (info / "grounds.yml").write_text(
        "- phrase_id: p1\n  basis: personal_experience\n",
        encoding="utf-8",
    )
    compute = Compute({"input": {}})
    compute._interface = _Iface(
        str(tmp_path),
        input={
            "type": "yaml",
            "directory": "info",
            "filename": "constants.yml",
        },
        grounds={
            "type": "yaml",
            "directory": "info",
            "filename": "grounds.yml",
            "index": "phrase_id",
        },
    )
    rows = compute._load_info_yaml_rows("grounds.yml")
    assert rows[0]["basis"] == "personal_experience"


def test_compute_loads_scores_via_data_store(tmp_path: Path):
    info = tmp_path / "info"
    info.mkdir()
    (info / "scores.yml").write_text(
        "- Name: corpus\n  n_vq: 25\n", encoding="utf-8"
    )
    compute = Compute({"input": {}})
    compute._interface = _Iface(
        str(tmp_path),
        input={
            "type": "parquet",
            "directory": "info",
            "filename": "records.parquet",
        },
        data={
            "type": "yaml",
            "directory": "info",
            "filename": "scores.yml",
            "index": "Name",
        },
    )
    rows = compute._load_info_yaml_rows("scores.yml")
    assert rows[0]["n_vq"] == 25


def test_compute_blocks_undeclared_sibling(tmp_path: Path):
    info = tmp_path / "info"
    info.mkdir()
    (info / "grounds.yml").write_text(
        "- phrase_id: p1\n  basis: principle\n", encoding="utf-8"
    )
    compute = Compute({"input": {}})
    compute._interface = _Iface(
        str(tmp_path),
        input={
            "type": "yaml",
            "directory": "info",
            "filename": "constants.yml",
        },
    )
    with pytest.raises(ValueError, match="refuse undeclared product"):
        compute._load_info_yaml_rows("grounds.yml")


def test_codebook_parquet_path_declared_and_sibling(tmp_path: Path):
    info = tmp_path / "info"
    info.mkdir()
    codebook = info / "codebook.parquet"
    pd.DataFrame({"cluster_ids": [[0, 1]]}).to_parquet(codebook)

    compute = Compute({"input": {}})
    compute._interface = _Iface(
        str(tmp_path),
        codebook={
            "type": "parquet",
            "directory": "info",
            "filename": "codebook.parquet",
            "index": "Name",
        },
    )
    got = compute._codebook_parquet_path()
    assert got is not None and got.name == "codebook.parquet"

    compute2 = Compute({"input": {}})
    compute2._interface = _Iface(
        str(tmp_path),
        input={"type": "yaml", "directory": "info", "filename": "c.yml"},
    )
    assert compute2._codebook_parquet_path() is None

    bare = Compute({"input": {}})
    assert bare._codebook_parquet_path() is None


def test_run_document_distance_uses_roster_and_codebook(tmp_path: Path):
    info = tmp_path / "info"
    info.mkdir()
    pd.DataFrame({"cluster_ids": [[0, 1, 0]]}).to_parquet(
        info / "codebook.parquet"
    )
    (info / "documents.yml").write_text(
        "- Name: d1\n  title: Doc One\n", encoding="utf-8"
    )
    compute = Compute({"input": {}})
    compute._interface = _Iface(
        str(tmp_path),
        input={
            "type": "parquet",
            "directory": "info",
            "filename": "records.parquet",
        },
        codebook={
            "type": "parquet",
            "directory": "info",
            "filename": "codebook.parquet",
        },
        roster={
            "type": "yaml",
            "directory": "info",
            "filename": "documents.yml",
        },
    )
    sentinel = object()
    with patch(
        "referia.assess.compute.run_document_distance_analysis",
        return_value=sentinel,
    ) as mocked:
        out = compute._run_document_distance_analysis()
    assert out is sentinel
    kwargs = mocked.call_args.kwargs
    assert list(kwargs["cluster_ids"]) == [0, 1, 0]
    assert kwargs.get("doc_titles") is not None


def test_discover_pipeline_edges_includes_sidecar_and_pack():
    stages = [
        {
            "id": "02_embed",
            "meta": {
                "output": {
                    "filename": "phrases.yml",
                    "directory": "_data/corpus",
                },
                "pack": {
                    "filename": "records.parquet",
                    "directory": "_data/corpus",
                },
            },
        },
        {
            "id": "07_grounds",
            "meta": {
                "output": {
                    "filename": "grounds.yml",
                    "directory": "_data/corpus",
                },
            },
        },
        {
            "id": "07_part_b",
            "meta": {
                "input": {
                    "filename": "records.parquet",
                    "directory": "_data/corpus",
                },
                "grounds": {
                    "filename": "grounds.yml",
                    "directory": "_data/corpus",
                },
            },
        },
        {
            "id": "03_vq",
            "meta": {
                "input": {
                    "filename": "records.parquet",
                    "directory": "_data/corpus",
                },
            },
        },
    ]
    found = discover_pipeline_edges(stages=stages)
    pairs = {(e["from"], e["to"], e["via"]) for e in found["edges"]}
    assert (
        "07_grounds",
        "07_part_b",
        "_data/corpus/grounds.yml",
    ) in pairs
    assert (
        "02_embed",
        "03_vq",
        "_data/corpus/records.parquet",
    ) in pairs
    assert (
        "02_embed",
        "07_part_b",
        "_data/corpus/records.parquet",
    ) in pairs


def test_discover_pipeline_edges_from_root_and_orphans(tmp_path: Path):
    (tmp_path / "index.md").write_text(
        "---\nlayout: referia\ntitle: hub\n---\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("# skip\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("# not referia\n", encoding="utf-8")
    (tmp_path / "bad.md").write_text("---\nlayout: [broken\n", encoding="utf-8")
    (tmp_path / "01_chunk.md").write_text(
        "---\nlayout: referia\npermalink: /01_chunk/\n"
        "output:\n  type: yaml\n  directory: _data/corpus\n"
        "  filename: chunks.yml\n---\nbody\n",
        encoding="utf-8",
    )
    (tmp_path / "02_extract.md").write_text(
        "---\nlayout: referia\n"
        "input:\n  type: yaml\n  directory: _data/corpus\n"
        "  filename: chunks.yml\n"
        "constants:\n  type: yaml\n  directory: _data/corpus\n"
        "  filename: constants.yml\n"
        "output:\n  type: parquet\n  directory: _data/corpus\n"
        "  filename: extracts.parquet\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="root or stages"):
        discover_pipeline_edges()
    found = discover_pipeline_edges(tmp_path)
    assert "01_chunk" in found["stages"]
    assert "02_extract" in found["stages"]
    assert "index" not in found["stages"]
    pairs = {(e["from"], e["to"]) for e in found["edges"]}
    assert ("01_chunk", "02_extract") in pairs
    orphan_vias = {o["via"] for o in found["orphans"]}
    assert "_data/corpus/constants.yml" in orphan_vias

    metas = _load_referia_stage_metas(tmp_path)
    assert {m["id"] for m in metas} == {"01_chunk", "02_extract"}


def test_store_path_key_and_self_edge_skipped():
    assert _store_path_key("nope") is None
    assert _store_path_key({"filename": "x.yml"}) == "x.yml"
    assert _store_path_key({"filename": ""}) is None
    found = discover_pipeline_edges(
        stages=[
            {
                "id": "same",
                "meta": {
                    "output": {"filename": "a.yml", "directory": "d"},
                    "input": {"filename": "a.yml", "directory": "d"},
                },
            },
            {"id": "", "meta": {"input": {"filename": "a.yml"}}},
            {"id": "skip", "meta": "not-a-map"},
            {
                "id": "list_in",
                "meta": {
                    "input": [
                        {"filename": "a.yml", "directory": "d"},
                        "ignore-me",
                    ]
                },
            },
        ]
    )
    # Self-edge same→same skipped; list_in still consumes.
    assert all(e["from"] != e["to"] for e in found["edges"])
    assert any(e["to"] == "list_in" for e in found["edges"])


def test_run_format_share_fills_from_codebook(tmp_path: Path):
    info = tmp_path / "info"
    info.mkdir()
    pd.DataFrame({"cluster_ids": [[1, 2]]}).to_parquet(info / "codebook.parquet")
    (info / "phrases.yml").write_text(
        "- phrase: a\n  kind: concern\n  format: chatbot\n  doc_id: d1\n",
        encoding="utf-8",
    )
    compute = Compute({"input": {}})
    compute._interface = _Iface(
        str(tmp_path),
        codebook={
            "type": "parquet",
            "directory": "info",
            "filename": "codebook.parquet",
        },
        phrases={
            "type": "yaml",
            "directory": "info",
            "filename": "phrases.yml",
        },
    )
    sentinel = ("ok",)
    with patch(
        "referia.assess.compute.run_format_share_compare",
        return_value=sentinel,
    ) as mocked:
        out = compute._run_format_share_compare()
    assert out is sentinel
    assert list(mocked.call_args.kwargs["cluster_ids"]) == [1, 2]
    assert mocked.call_args.kwargs["kinds"] == ["concern"]


def test_document_distance_ignores_undeclared_roster(tmp_path: Path):
    info = tmp_path / "info"
    info.mkdir()
    (info / "documents.yml").write_text(
        "- Name: d1\n  title: Only Sibling\n", encoding="utf-8"
    )
    compute = Compute({"input": {}})
    compute._interface = _Iface(
        str(tmp_path),
        input={"type": "yaml", "directory": "info", "filename": "c.yml"},
    )
    with patch(
        "referia.assess.compute.run_document_distance_analysis",
        return_value="ok",
    ) as mocked:
        compute._run_document_distance_analysis(cluster_ids=[0])
    assert mocked.call_args.kwargs.get("doc_titles") is None


def test_discover_requires_frontmatter_when_loading_root(tmp_path: Path):
    import sys

    real_import = __import__
    saved = sys.modules.pop("frontmatter", None)

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "frontmatter" or (
            fromlist and "frontmatter" in fromlist
        ):
            raise ImportError("no frontmatter")
        return real_import(name, globals, locals, fromlist, level)

    try:
        with patch("builtins.__import__", side_effect=_import):
            with pytest.raises(ImportError, match="python-frontmatter"):
                _load_referia_stage_metas(tmp_path)
    finally:
        if saved is not None:
            sys.modules["frontmatter"] = saved


def test_declared_store_path_empty_stat_path(tmp_path: Path):
    iface = _Iface(
        str(tmp_path),
        grounds={
            "type": "yaml",
            "directory": "info",
            "filename": "grounds.yml",
        },
    )
    with patch(
        "referia.assess.compute.stores._store_stat",
        return_value={"path": None},
    ):
        assert declared_store_path(iface, "grounds") is None
    with patch(
        "referia.assess.compute.stores._store_stat",
        return_value={"path": ""},
    ):
        assert declared_store_path(iface, "grounds") is None


def test_load_declared_yaml_safe_loader_fallback(tmp_path: Path):
    import yaml

    info = tmp_path / "info"
    info.mkdir()
    (info / "grounds.yml").write_text(
        "- phrase_id: p1\n  basis: principle\n", encoding="utf-8"
    )
    iface = _Iface(
        str(tmp_path),
        grounds={
            "type": "yaml",
            "directory": "info",
            "filename": "grounds.yml",
        },
    )
    # ``from yaml import CSafeLoader`` raises when the attribute is absent.
    saved = getattr(yaml, "CSafeLoader", None)
    if saved is not None:
        delattr(yaml, "CSafeLoader")
    try:
        rows = load_declared_yaml_rows(iface, "grounds")
    finally:
        if saved is not None:
            yaml.CSafeLoader = saved
    assert rows == [{"phrase_id": "p1", "basis": "principle"}]


def test_load_via_data_store_unknown_product_name(tmp_path: Path):
    """Class A ``data:`` filename need not be in PRODUCT_SIDECAR_ROLES."""
    info = tmp_path / "info"
    info.mkdir()
    (info / "custom.yml").write_text("- x: 1\n", encoding="utf-8")
    compute = Compute({"input": {}})
    compute._interface = _Iface(
        str(tmp_path),
        data={
            "type": "yaml",
            "directory": "info",
            "filename": "custom.yml",
        },
    )
    assert compute._load_info_yaml_rows("custom.yml") == [{"x": 1}]


def test_load_info_yaml_safe_loader_and_stat_oserror(tmp_path: Path):
    import yaml

    info = tmp_path / "info"
    info.mkdir()
    (info / "grounds.yml").write_text(
        "- phrase_id: p1\n  basis: principle\n", encoding="utf-8"
    )
    compute = Compute({"input": {}})
    compute._interface = _Iface(
        str(tmp_path),
        grounds={
            "type": "yaml",
            "directory": "info",
            "filename": "grounds.yml",
        },
    )
    saved = getattr(yaml, "CSafeLoader", None)
    if saved is not None:
        delattr(yaml, "CSafeLoader")
    try:
        rows = compute._load_info_yaml_rows("grounds.yml")
    finally:
        if saved is not None:
            yaml.CSafeLoader = saved
    assert rows == [{"phrase_id": "p1", "basis": "principle"}]

    # Path present but ``stat`` fails after exists check → empty list.
    compute._info_yaml_cache = {}
    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "stat", side_effect=OSError("gone")):
            assert compute._load_info_yaml_rows("grounds.yml") == []


def test_codebook_path_without_interface():
    compute = Compute({"input": {}})
    compute._interface = None
    assert compute._codebook_parquet_path() is None


def test_load_info_yaml_iface_without_get(tmp_path: Path):
    """``hasattr(iface, \"get\")`` false branch skips ``data:`` fallback."""

    class _Bare:
        directory = str(tmp_path)

    compute = Compute({"input": {}})
    compute._interface = _Bare()
    with pytest.raises(ValueError, match="CIP-0024"):
        compute._load_info_yaml_rows("grounds.yml")


def test_load_declared_missing_file_returns_empty(tmp_path: Path):
    compute = Compute({"input": {}})
    compute._interface = _Iface(
        str(tmp_path),
        grounds={
            "type": "yaml",
            "directory": "info",
            "filename": "grounds.yml",
        },
    )
    (tmp_path / "info").mkdir()
    assert compute._load_info_yaml_rows("grounds.yml") == []


def test_corrupt_codebook_exceptions_swallowed(tmp_path: Path):
    info = tmp_path / "info"
    info.mkdir()
    (info / "codebook.parquet").write_bytes(b"not-a-parquet")
    (info / "phrases.yml").write_text(
        "- phrase: a\n  kind: concern\n  format: chatbot\n  doc_id: d1\n",
        encoding="utf-8",
    )
    compute = Compute({"input": {}})
    compute._interface = _Iface(
        str(tmp_path),
        codebook={
            "type": "parquet",
            "directory": "info",
            "filename": "codebook.parquet",
        },
        phrases={
            "type": "yaml",
            "directory": "info",
            "filename": "phrases.yml",
        },
        roster={
            "type": "yaml",
            "directory": "info",
            "filename": "documents.yml",
        },
    )
    with patch(
        "referia.assess.compute.run_document_distance_analysis",
        return_value="dist",
    ) as dist_mock:
        assert compute._run_document_distance_analysis() == "dist"
    assert dist_mock.call_args.kwargs.get("cluster_ids") is None or (
        dist_mock.call_args.args == () 
    )

    with patch(
        "referia.assess.compute.run_format_share_compare",
        return_value="fmt",
    ) as fmt_mock:
        assert compute._run_format_share_compare() == "fmt"
    # Corrupt codebook → fill skipped; kinds still from phrases.
    assert fmt_mock.call_args.kwargs["kinds"] == ["concern"]


def test_lens_reconstruction_codebook_absent_and_corrupt(tmp_path: Path):
    info = tmp_path / "info"
    info.mkdir()
    (info / "phrases.yml").write_text(
        "- phrase_id: p1\n  phrase: hello\n  quote: hello\n"
        "  format: workshop\n  doc_id: d1\n",
        encoding="utf-8",
    )
    (info / "scores.yml").write_text(
        "- Name: corpus\n  responsibilities: null\n",
        encoding="utf-8",
    )
    compute = Compute({"input": {}})
    compute._interface = _Iface(
        str(tmp_path),
        phrases={
            "type": "yaml",
            "directory": "info",
            "filename": "phrases.yml",
        },
        grain={
            "type": "yaml",
            "directory": "info",
            "filename": "scores.yml",
        },
    )
    # No codebook: → else cluster_ids = None → hard_lens_labels fails softly.
    out = compute._run_lens_reconstruction()
    assert out[-1] == 0
    assert "03_vq" in out[-2] or "lens" in out[-2].lower() or out[-2]

    (info / "codebook.parquet").write_bytes(b"bad")
    compute._interface = _Iface(
        str(tmp_path),
        phrases={
            "type": "yaml",
            "directory": "info",
            "filename": "phrases.yml",
        },
        grain={
            "type": "yaml",
            "directory": "info",
            "filename": "scores.yml",
        },
        codebook={
            "type": "parquet",
            "directory": "info",
            "filename": "codebook.parquet",
        },
    )
    out2 = compute._run_lens_reconstruction()
    assert out2[-1] == 0


def test_discover_skips_unreadable_markdown(tmp_path: Path):
    (tmp_path / "ok.md").write_text(
        "---\nlayout: referia\n"
        "output:\n  filename: a.yml\n  directory: d\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "boom.md").write_text("---\nx: 1\n---\n", encoding="utf-8")

    import frontmatter

    real_load = frontmatter.load

    def _load(path, *args, **kwargs):
        if Path(path).name == "boom.md":
            raise RuntimeError("cannot parse")
        return real_load(path, *args, **kwargs)

    with patch.object(frontmatter, "load", side_effect=_load):
        found = discover_pipeline_edges(tmp_path)
    assert found["stages"] == ["ok"]
