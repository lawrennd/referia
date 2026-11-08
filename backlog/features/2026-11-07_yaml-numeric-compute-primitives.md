---
id: "2026-11-07_yaml-numeric-compute-primitives"
title: "YAML numeric compute primitives (add/multiply/threshold)"
status: "Completed"
priority: "High"
created: "2026-11-07"
last_updated: "2026-11-08"
category: "features"
related_cips: []
owner: "lawrennd"
dependencies: []
tags:
- backlog
- compute
- numeric
- assessment-compute
- vongole-interim
---

# Task: YAML numeric compute primitives

> **Scale note:** Backlog (not CIP). Thin pure functions for scoring arithmetic in
> `_referia.yml`. Interim assessment compute pending vongole (lynguine CIP-0007).
> Do **not** register these in lynguine’s access registry.

## Description

Referia’s compute registry already exposes `sum`, `max`, `len`, and `map`.
Reviewers also need general-purpose numeric ops for scoring workflows:

- `add`, `subtract`, `multiply`
- threshold compare (`gte` / `lte`, or a single `threshold` with an operator arg)
- optional `matmul` / `dot` for criteria×weights style layouts

Implement as **pure functions** in a small module under
`referia/assess/compute/` (e.g. `numeric.py`), then register thin entries in
`Compute._compute_functions_list()`. Keep logic out of `__init__.py`.

These are assessment-level transforms. Long-term home is **vongole**
(lynguine CIP-0007); until vongole exists they live in referia, matching the
existing `sum` / `max` / `len` placement.

## Acceptance Criteria

- [x] Pure functions for `add`, `subtract`, `multiply` registered and callable from YAML `compute` / `PopulateButton`
- [x] Threshold compare registered (`gte`/`lte` or equivalent) returning a clear boolean or 0/1 suitable for scoring fields
- [x] Optional `matmul` or `dot` registered if a minimal ndarray/list API is practical without pulling new deps
- [x] Unit tests cover scalar and series/list inputs used by the compute arg resolver
- [x] No changes to lynguine’s `_compute_functions_list`
- [x] Docstring / registry `docstr` notes interim placement pending vongole

## Implementation Notes

- Follow the pattern of existing `sum` / `max` / `len` registrations in
  `referia/assess/compute/__init__.py` (~867–878).
- Prefer numpy/pandas ops already available via the stack; avoid new dependencies.
- Argument shape should match lynguine `prep` / `row_args` / `args` conventions
  used by other referia compute entries.
- Cross-link names into lynguine’s vongole inventory task when that table is updated:
  `lynguine/backlog/infrastructure/2026-10-18_inventory-referia-compute-for-vongole.md`.

## Related

- Lynguine CIP: 0007 (assessment compute → vongole; Proposed)
- Lynguine backlog: `2026-10-18_inventory-referia-compute-for-vongole`
- Companion docs (referia): `2026-11-07_document-numeric-compute-primitives`
- Companion docs (lynguine): `2026-11-07_fix-fictional-add-compute-examples`

## Progress Updates

### 2026-11-07

Task created after inventory of live compute registries. Implementation deferred
until this task is Ready and explicitly started.

### 2026-11-08

Implemented on `cip0026-examples-serve-numeric` (ported from worktree
`referia-yaml-numeric` / `backlog-2026-11-07-yaml-numeric-compute-primitives`):

- Module `referia/assess/compute/numeric.py` with `add`, `subtract`, `multiply`,
  `gte`, `lte`, `matmul`, `dot`
- Registry entries in `Compute._compute_functions_list()` (vongole-interim docstr)
- Tests in `tests/test_compute_numeric.py`
- Demo: `examples/numeric_scoring/` (CIP-0026 Phase B)
