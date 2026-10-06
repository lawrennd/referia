---
id: "2026-10-06_cip000F-extract-normaliser"
title: "CIP-000F: Extract normalise_referia_config from Interface"
status: "Completed"
priority: "High"
created: "2026-10-06"
last_updated: "2026-10-06"
category: "features"
related_cips: ["000F"]
owner: ""
dependencies:
- "2026-10-06_cip000F-detect-dialect"
tags:
- backlog
- cip000F
- yaml
- migration
---

# Task: Extract in-memory config normaliser

## Description

Move the silent key rewrites in `Interface.__init__` into
`normalise_referia_config(data) -> dict`. `Interface` should call detect then
normalise before template expansion and `super().__init__`.

## Acceptance Criteria

- [ ] `allocation` (+ `additional`) → `input`; `scores` → `output`;
  `scorer` → `review`; `global_consts` → `constants`; `globals` → `parameters`
- [ ] `converters` rewritten to `dtypes` where applicable
- [ ] Existing mixed-key errors preserved (`allocation`+`input`, etc.)
- [ ] `scorer` still emits DeprecationWarning until files migrate
- [ ] Composite `CriterionComment*` expansion remains runtime-only (not part
  of normalise for on-disk migrate)
- [ ] Unit tests: normalise(v1) detects as v2; `Interface(data=v1)` behaviour
  matches pre-refactor for same inputs

## Implementation Notes

Extract, do not change semantics. Keep conversion on load so unstamped v1
files still work.

## Related

- CIP: 000F

## Progress Updates

### 2026-10-06

Task created on CIP-000F acceptance.

### 2026-10-06 (implementation)

Implemented and covered by referia/tests/test_config_dialect.py.
