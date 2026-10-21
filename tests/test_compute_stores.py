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


def test_size_human_larger_units():
    assert "MiB" in size_human(2 * 1024 * 1024)
    assert "GiB" in size_human(3 * 1024 ** 3)
    assert "TiB" in size_human(2 * 1024 ** 4)
    assert size_human(None) == "0 B"


def test_skips_non_stores_and_empty_interface():
    assert named_store_status(None) == {}
    assert named_store_status({"title": "Review", "compute": []}) == {}


def test_store_stat_fallback_when_lynguine_raises(tmp_path, monkeypatch):
    import lynguine.access.io as io

    monkeypatch.setattr(
        io,
        "store_stat",
        lambda details: (_ for _ in ()).throw(RuntimeError("boom")),
        raising=False,
    )
    missing = named_store_status(
        {
            "cache": {
                "type": "yaml",
                "filename": "gone.yml.gz",
                "directory": str(tmp_path),
            }
        }
    )
    assert missing["cache"]["exists"] is False
    assert missing["cache"]["codec"] == "gzip"

    path = tmp_path / "out.yml.gz"
    path.write_bytes(b"abc")
    present = named_store_status(
        {
            "output": {
                "type": "yaml",
                "filename": "out.yml.gz",
                "directory": str(tmp_path),
                "index": "unit_id",
            }
        }
    )
    assert present["output"]["exists"] is True
    assert present["output"]["size_bytes"] == 3
    assert present["output"]["index"] == "unit_id"


def test_store_stat_import_error_fallback(tmp_path, monkeypatch):
    import lynguine.access.io as io

    monkeypatch.delattr(io, "store_stat", raising=False)
    status = named_store_status(
        {
            "input": {
                "type": "yaml",
                "filename": "missing.yml",
                "directory": str(tmp_path),
            }
        }
    )
    assert status["input"]["exists"] is False


def test_frame_catalogue_without_len(tmp_path):
    class _Frame:
        columns = ["a", "b"]
        index = type("Idx", (), {"name": "unit_id"})()

        def __len__(self):
            raise TypeError("no len")

    status = named_store_status(
        {
            "input": {
                "type": "yaml",
                "filename": "x.yml",
                "directory": str(tmp_path),
            }
        },
        data=_Frame(),
    )
    assert status["input"]["columns"] == ["a", "b"]
    assert status["input"]["index"] == "unit_id"
    assert "n_rows" not in status["input"]


def test_llm_diskcache_missing(tmp_path):
    status = named_store_status({}, llm_cache_dir=str(tmp_path / "absent"))
    assert status["llm_diskcache"]["exists"] is False


def test_store_stat_success_used_when_present(tmp_path, monkeypatch):
    import lynguine.access.io as io

    monkeypatch.setattr(
        io,
        "store_stat",
        lambda details: {
            "path": "/from-lynguine",
            "exists": True,
            "size_bytes": 11,
            "codec": "gzip",
        },
        raising=False,
    )
    status = named_store_status(
        {
            "cache": {
                "type": "yaml",
                "filename": "x.yml.gz",
                "directory": str(tmp_path),
            }
        }
    )
    assert status["cache"]["path"] == "/from-lynguine"
    assert status["cache"]["size_bytes"] == 11
    assert status["cache"]["size_human"] == "11 B"


def test_named_store_status_skips_llm_lookup(tmp_path, monkeypatch):
    compute = Compute(
        {
            "input": {
                "type": "yaml",
                "filename": "x.yml",
                "directory": str(tmp_path),
            }
        }
    )
    monkeypatch.setattr("referia.assess.compute.LLM_AVAILABLE", False)
    status = compute._named_store_status()
    assert "llm_diskcache" not in status

    monkeypatch.setattr("referia.assess.compute.LLM_AVAILABLE", True)
    monkeypatch.setattr("referia.assess.compute.get_llm_manager", None)
    status = compute._named_store_status()
    assert "llm_diskcache" not in status

    class _Mgr:
        cache = None

    monkeypatch.setattr("referia.assess.compute.get_llm_manager", lambda: _Mgr())
    status = compute._named_store_status()
    assert "llm_diskcache" not in status


def test_compute_wrapper_reads_manager(tmp_path, monkeypatch):
    from unittest.mock import MagicMock

    compute = Compute(
        {
            "input": {
                "type": "yaml",
                "filename": "x.yml",
                "directory": str(tmp_path),
            }
        }
    )
    mgr = MagicMock()
    mgr.cache.directory = str(tmp_path / "llm")
    monkeypatch.setattr("referia.assess.compute.LLM_AVAILABLE", True)
    monkeypatch.setattr("referia.assess.compute.get_llm_manager", lambda: mgr)
    status = compute._named_store_status()
    assert "llm_diskcache" in status

    monkeypatch.setattr(
        "referia.assess.compute.get_llm_manager",
        lambda: (_ for _ in ()).throw(RuntimeError("no mgr")),
    )
    status = compute._named_store_status()
    assert "llm_diskcache" not in status
