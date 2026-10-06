"""Config-file linting for referia.

``scan_configs(root)`` walks a directory tree, attempts to ``yaml.safe_load``
every ``_referia.yml`` it finds, and returns a structured list of results.

Each result dict has the keys::

    path           – absolute path to the file
    relative_path  – path relative to the root
    ok             – True if YAML parsed without error
    error          – YAML error message (None if ok)
    line           – 1-indexed line number of the error (None if ok)
    column         – 1-indexed column number of the error (None if ok)
    category       – short error category string (None if ok)
    context        – list of annotated source lines around the error
    suggested_fix  – human-readable hint (None if ok or unknown)
    dialect        – DialectReport fields (None if parse failed)

Use ``format_text`` / ``format_json`` to render the result set for display or
LLM consumption.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from referia.config.dialect import (
    SUPPORTED_CONFIG_VERSION,
    detect_config_dialect,
    get_version_enforcement,
)


# ---------------------------------------------------------------------------
# Error categorisation
# ---------------------------------------------------------------------------

_CATEGORIES: list[tuple[str, str, str]] = [
    # (substring in error message, category slug, suggested fix template)
    (
        "while scanning an alias",
        "unquoted_glob_star",
        (
            "A bare '*' or '*...' is interpreted as a YAML alias.  "
            "Quote the value in double quotes.  "
            "Example:  glob: \"*\"  or  glob: \"*_foo.pdf\""
        ),
    ),
    (
        "while scanning a double-quoted scalar",
        "invalid_escape_in_double_quotes",
        (
            "A backslash sequence in a double-quoted string is invalid YAML "
            "(e.g. '\\(' is not a recognised escape).  "
            "Switch the string to single quotes or escape the backslash as '\\\\\\\\'."
        ),
    ),
    (
        "while scanning a simple key",
        "unquoted_colon_or_special_char",
        (
            "A value contains an unquoted ':' or other special character, or "
            "a simple key spans multiple lines.  "
            "Quote the value in single or double quotes."
        ),
    ),
    (
        "mapping values are not allowed here",
        "inline_value_with_subkeys",
        (
            "A key has both an inline scalar value and sub-keys (mapping "
            "values cannot follow the scalar).  "
            "Remove the inline value, or quote the value if ':' appears inside it.  "
            "Example: change  `index: Name: \\n  key: val`  to  `index: \"Name: \"`"
        ),
    ),
    (
        "while parsing a block mapping",
        "indentation_error",
        (
            "A block mapping has inconsistent indentation.  "
            "Ensure all sibling keys are indented by the same number of spaces."
        ),
    ),
]


def _categorize_error(error_msg: str) -> tuple[str, str | None]:
    """Return ``(category_slug, suggested_fix)`` for a YAML error message."""
    lower = error_msg.lower()
    for needle, slug, fix in _CATEGORIES:
        if needle in lower:
            return slug, fix
    return "unknown", None


# ---------------------------------------------------------------------------
# Single-file checker
# ---------------------------------------------------------------------------

def _check_one(
    yml_path: Path,
    root_path: Path,
    *,
    version_enforcement: str | None = None,
) -> dict[str, Any]:
    """Check a single ``_referia.yml``.  Always returns a result dict."""
    rel = str(yml_path.relative_to(root_path))
    base: dict[str, Any] = {
        "path": str(yml_path),
        "relative_path": rel,
        "ok": True,
        "error": None,
        "line": None,
        "column": None,
        "category": None,
        "context": [],
        "suggested_fix": None,
        "dialect": None,
        "warnings": [],
    }
    mode = version_enforcement or get_version_enforcement()
    try:
        import yaml  # type: ignore[import]
        with open(yml_path, encoding="utf-8") as fh:
            content = fh.read()
        data = yaml.safe_load(content)
        if data is None:
            data = {}
        if isinstance(data, dict):
            report = detect_config_dialect(data)
            base["dialect"] = report.as_dict()
            if report.conflicts:
                base["ok"] = False
                base["error"] = (
                    "dialect conflict: " + ", ".join(report.conflicts)
                )
                base["category"] = "dialect_conflict"
                base["suggested_fix"] = (
                    "Remove mixed v1/v2 keys that name the same slot "
                    "(e.g. allocation with input, scores with output)."
                )
            declared = report.version_declared
            if (
                declared is not None
                and declared > SUPPORTED_CONFIG_VERSION
            ):
                base["ok"] = False
                base["error"] = (
                    f"referia_config_version={declared} is newer than "
                    f"supported {SUPPORTED_CONFIG_VERSION}"
                )
                base["category"] = "unsupported_config_version"
                base["suggested_fix"] = (
                    "Upgrade referia or lower referia_config_version."
                )
            elif declared is None and report.version_inferred != 0:
                msg = (
                    "missing referia_config_version; "
                    "run `referia migrate --root DIR --stamp-only --write`"
                )
                if mode == "error":
                    base["ok"] = False
                    base["error"] = msg
                    base["category"] = "missing_config_version"
                    base["suggested_fix"] = (
                        "Add referia_config_version: 1 or 2, or stamp "
                        "with referia migrate --stamp-only --write."
                    )
                elif mode == "warn":
                    base["warnings"].append(msg)
        else:
            base["dialect"] = {
                "version_declared": None,
                "version_inferred": None,
                "markers": [],
                "conflicts": [],
                "needs_normalise": False,
                "notes": ["YAML root is not a mapping"],
            }
        return base
    except Exception as exc:
        try:
            content  # noqa: B018 — ensure it is bound even on open() failure
        except NameError:
            content = ""

        lines = content.splitlines()
        line_no: int | None = None
        col_no: int | None = None
        try:
            mark = exc.problem_mark  # type: ignore[attr-defined]
            line_no = mark.line      # 0-indexed
            col_no = mark.column     # 0-indexed
        except AttributeError:
            pass

        context: list[str] = []
        if line_no is not None:
            start = max(0, line_no - 3)
            end = min(len(lines), line_no + 4)
            for i in range(start, end):
                marker = "→" if i == line_no else " "
                context.append(f"{marker} {i + 1:4d} | {lines[i]}")

        error_msg = str(exc)
        category, suggested_fix = _categorize_error(error_msg)

        return {
            **base,
            "ok": False,
            "error": error_msg,
            "line": line_no + 1 if line_no is not None else None,
            "column": col_no + 1 if col_no is not None else None,
            "category": category,
            "context": context,
            "suggested_fix": suggested_fix,
        }


# ---------------------------------------------------------------------------
# Root scanner
# ---------------------------------------------------------------------------

def scan_configs(
    root: str,
    *,
    version_enforcement: str | None = None,
) -> list[dict[str, Any]]:
    """Scan all ``_referia.yml`` files under *root* and return results.

    Results are sorted by ``relative_path``.  Each entry is a dict as
    described in the module docstring.
    """
    root_path = Path(root).expanduser().resolve()
    results = []
    for yml in sorted(root_path.rglob("_referia.yml")):
        results.append(
            _check_one(
                yml, root_path, version_enforcement=version_enforcement
            )
        )
    return results


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def _dialect_bucket(result: dict[str, Any]) -> str:
    """Classify a successful parse into a dialect summary bucket."""
    d = result.get("dialect") or {}
    inferred = d.get("version_inferred")
    declared = d.get("version_declared")
    if inferred == 0:
        return "v0"
    if d.get("conflicts"):
        return "mixed"
    if inferred == 1:
        return "v1_stamped" if declared is not None else "v1_unlabelled"
    if inferred == 2:
        return "v2_stamped" if declared is not None else "v2_unlabelled"
    return "unknown"


def format_text(results: list[dict[str, Any]], root: str) -> str:
    """Return a human-readable report string."""
    lines: list[str] = []
    root_abs = str(Path(root).expanduser().resolve())
    total = len(results)
    errors = [r for r in results if not r["ok"]]
    ok_count = total - len(errors)

    buckets = {
        "v0": 0,
        "v1_unlabelled": 0,
        "v1_stamped": 0,
        "v2_unlabelled": 0,
        "v2_stamped": 0,
        "mixed": 0,
        "parse_error": 0,
        "unknown": 0,
    }
    for r in results:
        if not r["ok"] and r.get("category") != "dialect_conflict":
            buckets["parse_error"] += 1
        else:
            buckets[_dialect_bucket(r)] += 1

    lines.append(f"Scanning {root_abs} ...")
    lines.append(f"  {total} config(s) found")
    lines.append("")
    lines.append(f"  \u2713 {ok_count:>4}  OK")
    lines.append(f"  \u2717 {len(errors):>4}  error(s)")
    warn_count = sum(len(r.get("warnings") or []) for r in results)
    lines.append(f"  ! {warn_count:>4}  warning(s)")
    lines.append("")
    lines.append("  Dialect:")
    lines.append(f"    v0              {buckets['v0']:>4}")
    lines.append(f"    v1 unlabelled   {buckets['v1_unlabelled']:>4}")
    lines.append(f"    v1 stamped      {buckets['v1_stamped']:>4}")
    lines.append(f"    v2 unlabelled   {buckets['v2_unlabelled']:>4}")
    lines.append(f"    v2 stamped      {buckets['v2_stamped']:>4}")
    lines.append(f"    mixed           {buckets['mixed']:>4}")
    lines.append(f"    parse error     {buckets['parse_error']:>4}")

    warned = [r for r in results if r.get("warnings")]
    if warned:
        lines.append("")
        lines.append("Warnings:")
        for r in warned:
            for w in r["warnings"]:
                lines.append(f"  ! {r['relative_path']}: {w}")

    if not errors:
        lines.append("")
        lines.append("All configs are valid.")
        return "\n".join(lines)

    lines.append("")
    for r in errors:
        sep = "\u2500" * 60
        header = f"\u2514\u2500 {r['relative_path']}"
        if r["line"] is not None:
            header += f"  (line {r['line']})"
        lines.append(header)
        lines.append(f"   Category : {r['category']}")
        # Show first line of error message only to keep output concise
        first_line = r["error"].splitlines()[0] if r["error"] else ""
        lines.append(f"   Error    : {first_line}")
        if r["context"]:
            lines.append("   Context  :")
            for ctx_line in r["context"]:
                lines.append(f"     {ctx_line}")
        if r["suggested_fix"]:
            # Word-wrap the fix hint at 70 chars
            import textwrap
            fix_lines = textwrap.wrap(r["suggested_fix"], width=70)
            lines.append(f"   Fix      : {fix_lines[0]}")
            for fl in fix_lines[1:]:
                lines.append(f"              {fl}")
        lines.append("")

    return "\n".join(lines)


def format_json(results: list[dict[str, Any]], root: str) -> str:
    """Return a JSON report string suitable for LLM consumption."""
    root_abs = str(Path(root).expanduser().resolve())
    errors = [r for r in results if not r["ok"]]
    warnings = [
        {"path": r["path"], "relative_path": r["relative_path"], "warning": w}
        for r in results
        for w in (r.get("warnings") or [])
    ]
    payload = {
        "root": root_abs,
        "total_scanned": len(results),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "results": results,
    }
    return json.dumps(payload, indent=2)
