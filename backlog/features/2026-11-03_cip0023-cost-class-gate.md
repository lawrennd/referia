---
id: "2026-11-03_cip0023-cost-class-gate"
title: "CIP-0023: Cost-class gate and eligibility helpers"
status: "Completed"
priority: "Medium"
created: "2026-11-03"
last_updated: "2026-11-03"
category: "features"
related_cips: ["0023"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-11-03_cip0023-pipeline-manifest"
tags:
- backlog
- features
- multiverse
- cip0023
---

# Task: Cost-class gate and eligibility helpers

> Linked CIP: 0023.

## Description

Helpers that classify selectable knobs / stages (`aggregate`, `refit`,
`llm`, `display`) and that expand a whole-stage tick to eligible
aggregate knobs only. Phase 1 Run refuses (clear message) when the
selection contains only non-executable ticks.

## Acceptance Criteria

- [ ] `expand_stage_selection` returns only `multiverse_eligible` +
      `aggregate` knobs
- [ ] Gate helper lists refused refit/llm ticks
- [ ] Unit tests for expand + refuse

## Implementation Notes

- Used by the multiverse page before Populate; may also warn in markdown
  output of a dry-run compute

## Related

- CIP: 0023

## Progress Updates

### 2026-11-03

Task created as Ready; implement alongside manifest helpers.
