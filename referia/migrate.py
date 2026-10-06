"""Stamp and migrate referia ``_referia.yml`` dialects (CIP-000F).

Stamp-only mode inserts ``referia_config_version`` without rewriting keys.
Dry-run is the default; pass ``write=True`` to modify files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from referia.config.dialect import (
    detect_config_dialect,
    inferred_stamp_version,
    stamp_version_text,
)


def scan_for_stamp(root: str) -> list[dict[str, Any]]:
    """Plan stamp-only actions for every ``_referia.yml`` under *root*."""
    root_path = Path(root).expanduser().resolve()
    results: list[dict[str, Any]] = []
    for yml in sorted(root_path.rglob("_referia.yml")):
        results.append(_plan_one(yml, root_path))
    return results


def _plan_one(yml_path: Path, root_path: Path) -> dict[str, Any]:
    rel = str(yml_path.relative_to(root_path))
    base: dict[str, Any] = {
        "path": str(yml_path),
        "relative_path": rel,
        "action": "error",
        "version": None,
        "ok": False,
        "error": None,
        "dialect": None,
    }
    try:
        text = yml_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            base["error"] = "YAML root is not a mapping"
            return base
        report = detect_config_dialect(data)
        base["dialect"] = report.as_dict()
        version = inferred_stamp_version(data)
        if report.version_inferred == 0:
            base["action"] = "skip_v0"
            base["ok"] = True
            base["error"] = "proto v0; not stamped"
            return base
        if report.version_declared is not None:
            base["action"] = "skip_already_stamped"
            base["version"] = report.version_declared
            base["ok"] = True
            return base
        if report.conflicts:
            base["action"] = "error"
            base["error"] = "dialect conflicts: " + ", ".join(report.conflicts)
            return base
        base["action"] = "stamp"
        base["version"] = version
        base["ok"] = True
        base["_text"] = text  # used only by apply; stripped in formatters
        return base
    except Exception as exc:  # noqa: BLE001 — surface any read/parse failure
        base["error"] = str(exc)
        return base


def apply_stamp(results: list[dict[str, Any]], *, write: bool = False) -> list[dict[str, Any]]:
    """Apply stamp plans. When *write* is False, only report would-be changes."""
    out: list[dict[str, Any]] = []
    for r in results:
        item = {k: v for k, v in r.items() if k != "_text"}
        if r.get("action") != "stamp":
            out.append(item)
            continue
        text = r.get("_text")
        if text is None:
            text = Path(r["path"]).read_text(encoding="utf-8")
        new_text = stamp_version_text(text, int(r["version"]))
        item["would_write"] = new_text != text
        if write and new_text != text:
            Path(r["path"]).write_text(new_text, encoding="utf-8")
            item["written"] = True
        else:
            item["written"] = False
        out.append(item)
    return out


def format_stamp_text(results: list[dict[str, Any]], root: str, *, write: bool) -> str:
    """Human-readable stamp report."""
    root_abs = str(Path(root).expanduser().resolve())
    lines = [
        f"{'Writing' if write else 'Dry-run'} stamp-only under {root_abs}",
        "",
    ]
    counts = {
        "stamp": 0,
        "skip_already_stamped": 0,
        "skip_v0": 0,
        "error": 0,
    }
    for r in results:
        action = r.get("action", "error")
        counts[action] = counts.get(action, 0) + 1
        if action == "stamp":
            flag = "wrote" if r.get("written") else "would stamp"
            lines.append(
                f"  [{flag}] {r['relative_path']} -> referia_config_version: {r['version']}"
            )
        elif action == "error":
            lines.append(f"  [error] {r['relative_path']}: {r.get('error')}")
        elif action == "skip_v0":
            lines.append(f"  [skip v0] {r['relative_path']}")
    lines.append("")
    lines.append(
        f"  stamp={counts.get('stamp', 0)}  "
        f"already={counts.get('skip_already_stamped', 0)}  "
        f"v0={counts.get('skip_v0', 0)}  "
        f"error={counts.get('error', 0)}"
    )
    return "\n".join(lines)


def format_stamp_json(results: list[dict[str, Any]], root: str, *, write: bool) -> str:
    payload = {
        "root": str(Path(root).expanduser().resolve()),
        "write": write,
        "results": [{k: v for k, v in r.items() if k != "_text"} for r in results],
    }
    return json.dumps(payload, indent=2)
