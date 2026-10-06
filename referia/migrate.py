"""Stamp and migrate referia ``_referia.yml`` dialects (CIP-000F).

Stamp-only mode inserts ``referia_config_version`` without rewriting keys.
Full rewrite mode applies ``normalise_referia_config`` on disk (may lose
comments / reorder keys). Dry-run is the default; pass ``write=True`` to
modify files.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import yaml

from referia.config.dialect import (
    deep_copy_config,
    detect_config_dialect,
    inferred_stamp_version,
    normalise_referia_config,
    stamp_version_text,
)


def scan_for_stamp(root: str) -> list[dict[str, Any]]:
    """Plan stamp-only actions for every ``_referia.yml`` under *root*."""
    root_path = Path(root).expanduser().resolve()
    results: list[dict[str, Any]] = []
    for yml in sorted(root_path.rglob("_referia.yml")):
        results.append(_plan_stamp(yml, root_path))
    return results


def _plan_stamp(yml_path: Path, root_path: Path) -> dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Full dialect rewrite (may lose comments / reorder keys)
# ---------------------------------------------------------------------------

_V1_KEYS = (
    "allocation",
    "additional",
    "scores",
    "scorer",
    "global_consts",
    "globals",
)


def scan_for_rewrite(root: str) -> list[dict[str, Any]]:
    """Plan full key-rewrite actions for every ``_referia.yml`` under *root*."""
    root_path = Path(root).expanduser().resolve()
    return [
        _plan_rewrite(yml, root_path)
        for yml in sorted(root_path.rglob("_referia.yml"))
    ]


def _keys_that_change(before: dict, after: dict) -> list[str]:
    changed: list[str] = []
    for key in _V1_KEYS:
        if key in before and key not in after:
            changed.append(f"-{key}")
    for key in ("input", "output", "review", "constants", "parameters"):
        if key not in before and key in after:
            changed.append(f"+{key}")
        elif key in before and key in after and before[key] != after[key]:
            changed.append(f"~{key}")
    if before.get("referia_config_version") != after.get("referia_config_version"):
        changed.append("~referia_config_version")
    return changed


def _plan_rewrite(yml_path: Path, root_path: Path) -> dict[str, Any]:
    rel = str(yml_path.relative_to(root_path))
    base: dict[str, Any] = {
        "path": str(yml_path),
        "relative_path": rel,
        "action": "error",
        "ok": False,
        "error": None,
        "dialect": None,
        "changes": [],
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
        if report.version_inferred == 0:
            base["action"] = "skip_v0"
            base["ok"] = True
            base["error"] = "proto v0; not rewritten"
            return base
        if report.conflicts:
            base["error"] = "dialect conflicts: " + ", ".join(report.conflicts)
            return base
        if not report.needs_normalise and report.version_declared == 2:
            base["action"] = "skip_already_v2"
            base["ok"] = True
            return base

        before = deep_copy_config(data)
        after = deep_copy_config(data)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            normalise_referia_config(after)
        after["referia_config_version"] = 2
        changes = _keys_that_change(before, after)
        if not changes and not report.needs_normalise:
            if report.version_declared == 2:
                base["action"] = "skip_already_v2"
                base["ok"] = True
                return base
            changes = ["~referia_config_version"]

        base["action"] = "rewrite"
        base["ok"] = True
        base["changes"] = changes
        base["_after"] = after
        return base
    except Exception as exc:  # noqa: BLE001
        base["error"] = str(exc)
        return base


def apply_rewrite(
    results: list[dict[str, Any]],
    *,
    write: bool = False,
    in_place: bool = False,
) -> list[dict[str, Any]]:
    """Apply rewrite plans.

    Default write target is sibling ``_referia.migrated.yml``. With
    ``in_place=True``, overwrites the original after writing a ``.bak``.
    """
    out: list[dict[str, Any]] = []
    for r in results:
        item = {k: v for k, v in r.items() if not k.startswith("_")}
        if r.get("action") != "rewrite":
            out.append(item)
            continue
        after = r.get("_after")
        if after is None:
            item["error"] = "missing normalised payload"
            item["action"] = "error"
            item["ok"] = False
            out.append(item)
            continue
        dumped = yaml.safe_dump(
            after,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
        src = Path(r["path"])
        if in_place:
            dest = src
            bak = src.with_suffix(src.suffix + ".bak")
        else:
            dest = src.with_name("_referia.migrated.yml")
            bak = None
        item["dest"] = str(dest)
        item["would_write"] = True
        if write:
            if in_place and bak is not None:
                bak.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                item["backup"] = str(bak)
            dest.write_text(dumped, encoding="utf-8")
            item["written"] = True
        else:
            item["written"] = False
        out.append(item)
    return out


def format_rewrite_text(
    results: list[dict[str, Any]], root: str, *, write: bool, in_place: bool
) -> str:
    root_abs = str(Path(root).expanduser().resolve())
    mode = "in-place" if in_place else "sibling _referia.migrated.yml"
    lines = [
        f"{'Writing' if write else 'Dry-run'} full dialect rewrite under {root_abs}",
        f"  Target: {mode}",
        "  Note: full rewrite may lose comments and reorder keys.",
        "",
    ]
    counts: dict[str, int] = {}
    for r in results:
        action = r.get("action", "error")
        counts[action] = counts.get(action, 0) + 1
        if action == "rewrite":
            flag = "wrote" if r.get("written") else "would rewrite"
            dest = r.get("dest", "")
            ch = ", ".join(r.get("changes") or []) or "(version only)"
            lines.append(f"  [{flag}] {r['relative_path']} -> {dest}")
            lines.append(f"           changes: {ch}")
        elif action == "error":
            lines.append(f"  [error] {r['relative_path']}: {r.get('error')}")
        elif action == "skip_v0":
            lines.append(f"  [skip v0] {r['relative_path']}")
        elif action == "skip_already_v2":
            lines.append(f"  [skip v2] {r['relative_path']}")
    lines.append("")
    lines.append("  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return "\n".join(lines)


def format_rewrite_json(
    results: list[dict[str, Any]], root: str, *, write: bool, in_place: bool
) -> str:
    payload = {
        "root": str(Path(root).expanduser().resolve()),
        "write": write,
        "in_place": in_place,
        "results": [
            {k: v for k, v in r.items() if not k.startswith("_")} for r in results
        ],
    }
    return json.dumps(payload, indent=2)
