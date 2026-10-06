---
id: "2026-10-06_strict-columns-duplicate-excel-headers"
title: "Dialect-aware strict_columns defaults (v1 false, v2 true)"
status: "Completed"
priority: "High"
created: "2026-10-06"
last_updated: "2026-10-06"
category: "bugs"
related_cips: ["000F"]
owner: ""
dependencies: []
tags:
- backlog
- bugs
- excel
- strict_columns
- dialect
- security
---

# Task: Default strict_columns by config dialect version

## Description

Opening http://127.0.0.1:8000/ref/output/ returned **503 Could not load
config** because referia currently defaults `strict_columns` to **True**.
The REF Outputs sheet has duplicate headers; pandas emits
`REF output identifier.1`, and strict mode rejects the load.

That default is wrong for living **v1** configs. lynguine already defaults
permissive (`False`). CIP-000F versioning lets us make the policy explicit:

| Dialect | Default `strict_columns` | Rationale |
|---------|--------------------------|-----------|
| **v1** (declared or inferred) | `false` | Legacy Excel / REF-style sheets often have extra or duplicated headers |
| **v2** | `true` | Canonical configs; opt out with `strict_columns: false` |
| Explicit YAML | always wins | Either level (top or data-spec) |

**Security / logging:** Do **not** dump column names, paths, or spreadsheet
contents into the server log as the primary fix. CIP-000E already keeps
exception text out of HTML (`/errors` shows type + “See server log”). Prefer
a short, non-sensitive operator message (e.g. category
`strict_columns_mismatch`) over verbose diagnostics in logs. Detailed
debug belongs behind an opt-in flag if needed later—not the default.

## Acceptance Criteria

- [x] When `strict_columns` is omitted: **v1 → False**, **v2 → True**
  (use declared version if present, else inferred dialect)
- [x] Explicit `strict_columns: true|false` in YAML overrides the default
- [x] REF output config (`referia_config_version: 1`) loads without editing
  the spreadsheet or adding `strict_columns: false`
- [x] A stamped/canonical v2 config without the key stays strict by default
- [x] Server log on load failure stays sparse (type / safe category); no
  column inventories or file payloads in default logging
- [x] Unit tests cover: omit key on v1, omit key on v2, explicit override
- [x] Update `TestStrictColumnsDefault` docstring/expectations to match
  this dialect-aware policy (today they document “default True”)

## Implementation Notes

Touchpoint: `referia/assess/data.py` `CustomDataFrame._finalize_df`
resolution when `strict_columns is None`. Read version from the interface
(`referia_config_version` already popped onto `Interface` as
`_referia_config_version`, or re-detect from config before pop).

Trigger case (for regression, not for logging detail):

- `~/Documents/ref/output/_referia.yml` + Outputs sheet duplicate
  `REF output identifier` / `DOI` headers

Do not treat “richer server logs” as the solution.

Implemented via:

- `Interface._referia_dialect_version` captured before normalisation
- `CustomDataFrame._resolve_strict_columns` / `_dialect_strict_columns_default`
- `effective_config_version()` helper in `referia.config.dialect`

## Related

- CIP: 000F
- CIP-000E (no exception text in HTML)
- Config: `~/Documents/ref/output/_referia.yml`

## Progress Updates

### 2026-10-06

Bug found on `/ref/output/`. Initially drafted as “informative error”;
retargeted to dialect-aware defaults + sparse logs after discussion.

### 2026-10-06 (later)

Implemented dialect-aware defaults and updated `TestStrictColumnsDefault`.
Status → Completed.
