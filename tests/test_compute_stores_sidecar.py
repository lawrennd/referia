"""CIP-0024: declared sidecar product stores."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from referia.assess.compute import Compute
from referia.assess.compute.pipeline import discover_pipeline_edges
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


def test_compute_prefers_declared_grounds(tmp_path: Path):
    info = tmp_path / "info"
    info.mkdir()
    (info / "grounds.yml").write_text(
        "- phrase_id: p1\n  basis: personal_experience\n",
        encoding="utf-8",
    )
    # Sibling undeclared file would be wrong if used.
    (info / "wrong.yml").write_text(
        "- phrase_id: x\n  basis: unclear\n", encoding="utf-8"
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


def test_compute_warns_on_undeclared_sibling(tmp_path: Path, caplog):
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
    import logging

    with caplog.at_level(logging.WARNING):
        rows = compute._load_info_yaml_rows("grounds.yml")
    assert rows[0]["basis"] == "principle"
    assert any("CIP-0024" in r.message for r in caplog.records)


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
