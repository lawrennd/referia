---
id: "2026-10-06_cip000F-check-dialect-report"
title: "CIP-000F: Extend referia check with dialect reporting"
status: "Ready"
priority: "Medium"
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
- cli
- check
---

# Task: Dialect section in `referia check`

## Description

Extend `referia check` so that, for every successfully parsed `_referia.yml`,
it reports inferred/declared dialect and conflicts. JSON output must include
dialect fields per file for agent consumption.

## Acceptance Criteria

- [ ] Text summary counts: v0 / v1 unlabelled / v1 stamped / v2 unlabelled /
  v2 stamped / mixed / parse errors
- [ ] JSON includes `version_declared`, `version_inferred`, `markers`,
  `conflicts` (or equivalent) per file
- [ ] Does not require Excel or path access
- [ ] Exit code remains non-zero for parse errors; dialect conflicts treated
  as errors; unlabelled versions are not errors until enforce phase

## Implementation Notes

Reuse `detect_config_dialect`. Builds on existing `referia/check.py`.

## Related

- CIP: 000F
- Related: `backlog/features/2026-07-16_referia-check-cli.md`

## Progress Updates

### 2026-10-06

Task created on CIP-000F acceptance.
