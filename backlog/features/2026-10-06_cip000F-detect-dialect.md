---
id: "2026-10-06_cip000F-detect-dialect"
title: "CIP-000F: detect_config_dialect and DialectReport"
status: "Completed"
priority: "High"
created: "2026-10-06"
last_updated: "2026-10-06"
category: "features"
related_cips: ["000F"]
owner: ""
dependencies: []
tags:
- backlog
- cip000F
- yaml
- dialect
---

# Task: Detect referia config dialect

## Description

Add `referia/config/dialect.py` with a pure `detect_config_dialect(data) ->
DialectReport` that classifies a loaded `_referia.yml` dict as dialect v0 /
v1 / v2 without mutating it or touching the filesystem.

## Acceptance Criteria

- [ ] `DialectReport` exposes `version_declared`, `version_inferred`,
  `markers`, `conflicts`, `needs_normalise`, `notes`
- [ ] v1 markers detected: `allocation`, `additional`, `scores`, `scorer`,
  `global_consts`, `globals`, and `converters` on data specs
- [ ] v2 inferred when `input` / `output` / `review` present and no v1 markers
- [ ] Mixed v1/v2 slots reported as conflicts
- [ ] Proto `_config.yml` shapes (v0) noted, not normalised
- [ ] Unit tests with synthetic fixtures (no personal REF data)

## Implementation Notes

No I/O. Safe for `referia check`, tests, and `Interface`. See CIP-000F
dialect table.

## Related

- CIP: 000F

## Progress Updates

### 2026-10-06

Task created on CIP-000F acceptance.

### 2026-10-06 (implementation)

Implemented and covered by referia/tests/test_config_dialect.py.
