"""Named-store status for the review pane (CIP-0017).

Wraps lynguine ``store_stat`` (file facts) and adds catalogue fields from a
loaded frame plus a labelled LLM diskcache line. Display only.
"""

from __future__ import annotations

import os
from typing import Any, Mapping

__all__ = ["size_human", "named_store_status"]

_STORE_HINTS = ("filename", "type", "directory")


def size_human(n: int | float | None) -> str:
    """Human-readable byte count (KiB / MiB / GiB)."""
    value = float(n or 0)
    if value < 1024:
        return f"{int(value)} B"
    for unit in ("KiB", "MiB", "GiB"):
        value /= 1024.0
        if value < 1024:
            return f"{value:.1f} {unit}"
    value /= 1024.0
    return f"{value:.1f} TiB"


def _store_stat(details: Mapping) -> dict[str, Any]:
    try:
        from lynguine.access.io import store_stat
    except ImportError:
        store_stat = None
    if store_stat is not None:
        try:
            return dict(store_stat(dict(details)))
        except Exception:
            pass
    filename = str(details.get("filename") or "")
    directory = str(details.get("directory") or ".")
    path = filename if os.path.isabs(filename) else os.path.join(directory, filename)
    abs_path = os.path.abspath(path)
    codec = details.get("compress")
    if not codec and filename.endswith(".gz"):
        codec = "gzip"
    if not os.path.exists(abs_path):
        return {
            "path": abs_path,
            "exists": False,
            "mtime": None,
            "size_bytes": 0,
            "codec": codec,
            "logical_type": details.get("type"),
            "role": details.get("role"),
        }
    st = os.stat(abs_path)
    import datetime as _dt

    mtime = _dt.datetime.fromtimestamp(
        st.st_mtime, tz=_dt.datetime.now().astimezone().tzinfo
    )
    return {
        "path": abs_path,
        "exists": True,
        "mtime": mtime.isoformat(),
        "size_bytes": st.st_size,
        "codec": codec,
        "logical_type": details.get("type"),
        "role": details.get("role"),
    }


def _is_store(value: Any) -> bool:
    return isinstance(value, Mapping) and any(k in value for k in _STORE_HINTS)


def _frame_catalogue(frame: Any) -> dict[str, Any]:
    if frame is None:
        return {}
    columns_attr = getattr(frame, "columns", None)
    columns = [str(c) for c in list(columns_attr)] if columns_attr is not None else []
    index = getattr(getattr(frame, "index", None), "name", None)
    try:
        n_rows = int(len(frame))
    except TypeError:
        n_rows = None
    out: dict[str, Any] = {}
    if n_rows is not None:
        out["n_rows"] = n_rows
    if columns:
        out["columns"] = columns
    if index:
        out["index"] = str(index)
    return out


def named_store_status(
    interface: Mapping | None,
    data: Any = None,
    llm_cache_dir: str | None = None,
    **_kwargs,
) -> dict[str, Any]:
    """Mapping of named Access stores → file facts + catalogue.

    Does not dump cell values (payloads, embeddings, unit text).
    """
    status: dict[str, Any] = {}
    if interface:
        for key, details in dict(interface).items():
            if not _is_store(details):
                continue
            entry = _store_stat(details)
            entry["size_human"] = size_human(entry.get("size_bytes"))
            declared = details.get("columns")
            if declared:
                entry.setdefault("columns", [str(c) for c in list(declared)])
            if details.get("index"):
                entry.setdefault("index", str(details["index"]))
            entry.setdefault("role", key)
            if key in {"input", "output", "cache"}:
                cat = _frame_catalogue(data)
                if "n_rows" in cat:
                    entry["n_rows"] = cat["n_rows"]
                if cat.get("columns") and "columns" not in entry:
                    entry["columns"] = cat["columns"]
                if cat.get("index") and "index" not in entry:
                    entry["index"] = cat["index"]
            status[str(key)] = entry
    if llm_cache_dir:
        exists = os.path.isdir(llm_cache_dir)
        status["llm_diskcache"] = {
            "label": "API cost cache; not analysis state",
            "path": os.path.abspath(llm_cache_dir),
            "exists": exists,
            "size_bytes": 0,
            "size_human": "—",
        }
    return status
