---
id: "2026-11-03_cip0023-axis-filter"
title: "CIP-0023: Selection axes filter for run_analysis_multiverse"
status: "Completed"
priority: "High"
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

# Task: Selection axes filter for run_analysis_multiverse

> Linked CIP: 0023.

## Description

Extend `run_analysis_multiverse` so Phase 1 paper axes
(definition / weighting / exclusion / threshold / round) can be toggled
via an `active_axes` (or equivalent) argument. Default all-on must match
today’s full aggregate product cardinality (given the same points).

## Acceptance Criteria

- [ ] All axes on ⇒ same `n_configs` as pre-CIP behaviour on fixtures
- [ ] Subset of axes ⇒ smaller product; markdown names active axes
- [ ] Wrapper passes row_args / selection flags from the multiverse page
- [ ] Unit tests for subset and default

## Implementation Notes

- Keep levels in `DEFINITIONS`, `WEIGHTINGS`, etc.; filter which dimensions
  enter `itertools.product`
- Non-executable refit/llm ticks are a UI gate, not this function’s job
  in Phase 1

## Related

- CIP: 0023

## Progress Updates

### 2026-11-03

Task created; implementation started with CIP acceptance.
