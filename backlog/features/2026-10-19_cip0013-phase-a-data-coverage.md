---
id: "2026-10-19_cip0013-phase-a-data-coverage"
title: "CIP-0013 Phase A: CustomDataFrame (data.py) coverage"
status: "Completed"
priority: "High"
created: "2026-10-19"
last_updated: "2026-10-19"
category: "features"
related_cips: ["0013"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- cip0013
- tests
- coverage
---

# Task: Phase A — `data.py` coverage

## Description

Raise branch coverage of `referia/assess/data.py` to ≥ 50% (measured with
`tests/` + `referia/tests/`) via focused unit tests for column helpers,
element get/set, index pre/post compute, and `automapping`.

## Acceptance Criteria

- [x] `data.py` ≥ 50% branch coverage under CIP-0013 measurement command
- [x] New tests under `tests/test_assess_data_coverage.py`
- [x] No regressions in existing assess data tests

## Implementation Notes

Prefer synthetic `CustomDataFrame` frames with `colspecs` over full
`from_flow` demos. Mock `compute_pre` / `compute_post` when testing
`set_index`. Also covered: `add_column` / `drop_column` paths,
`concat_preserving_dtypes`, `_finalize_df` selector/fields, subseries
helpers. Fixed `drop_column` KeyError message typo (`column` →
`column_name`).

## Related

- CIP: 0013

## Progress Updates

### 2026-10-19

Task created; implementation started on branch `cip0013-assess-coverage`.

### 2026-10-19 (complete)

`data.py` at **51%** branch coverage (both trees + new tests). Marked
Completed.
