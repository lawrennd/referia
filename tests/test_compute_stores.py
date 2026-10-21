"""CIP-0017 named-store status mapping."""

from pathlib import Path

import pandas as pd

from referia.assess.compute import Compute
from referia.assess.compute.stores import named_store_status, size_human


def test_size_human():
    assert size_human(0) == "0 B"
    assert size_human(512) == "512 B"
    assert "KiB" in size_human(2048)


def test_missing_cache_file(tmp_path):
    interface = {
        "cache": {
            "type": "yaml",
            "filename": "_extract_cache.yml.gz",
            "directory": str(tmp_path),
            "compress": "gzip",
            "columns": ["extraction_payload"],
            "index": "unit_id",
        }
    }
    status = named_store_status(interface)
    assert status["cache"]["exists"] is False
    assert status["cache"]["size_bytes"] == 0
    assert status["cache"]["columns"] == ["extraction_payload"]
    assert "extraction_payload" not in str(status).split("columns")[0]


def test_present_gzip_cache_lists_columns_not_payload(tmp_path):
    path = Path(tmp_path) / "_extract_cache.yml.gz"
    path.write_bytes(b"\x1f\x8b fake gzip")
    interface = {
        "cache": {
            "type": "yaml",
            "filename": "_extract_cache.yml.gz",
            "directory": str(tmp_path),
            "compress": "gzip",
            "columns": ["extraction_payload"],
        },
        "output": {
            "type": "yaml",
            "filename": "phrases.yml.gz",
            "directory": str(tmp_path),
        },
    }
    frame = pd.DataFrame({"extraction_payload": ["secret text should not leak"]})
    status = named_store_status(interface, data=frame)
    assert status["cache"]["exists"] is True
    assert status["cache"]["n_rows"] == 1
    assert "extraction_payload" in status["cache"]["columns"]
    assert "secret text should not leak" not in str(status)
    assert status["output"]["exists"] is False


def test_llm_diskcache_labelled(tmp_path):
    cache_dir = tmp_path / ".llm_cache"
    cache_dir.mkdir()
    status = named_store_status({}, llm_cache_dir=str(cache_dir))
    assert status["llm_diskcache"]["exists"] is True
    assert "not analysis state" in status["llm_diskcache"]["label"]


def test_named_store_status_registered():
    names = {e["name"] for e in Compute({"input": {}})._compute_functions_list()}
    assert "named_store_status" in names
