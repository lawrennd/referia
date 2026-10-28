---
id: "2026-10-28_cip001C-example-overview"
title: "examples/overview_inline_list sibling today/year catalog fixture"
status: "Completed"
priority: "Medium"
created: "2026-10-28"
last_updated: "2026-10-28"
category: "features"
related_cips: ["001C"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-10-28_cip001C-inherit-reuse"
- "2026-10-28_cip001C-group-month-none"
- "2026-10-28_cip001C-catalog-schedule-yaml"
tags:
- backlog
- features
- examples
- catalog
- tests
- cip001C
---

# Task: Example overview with sibling Today/Year fixture

> Linked CIP: 001C. Package-reproducible pattern without OneDrive.

## Description

Extend `examples/overview_inline_list/` (or a sibling example directory) so the CIP-001C pattern is testable in this repo:

- Root catalog: tall `yaml_directory`, `catalog-scores.yml` with `complete` / `due` / `event` / `notes`, `when` / `on_today`, seasonal filters on `when`
- Nested work configs with identity `date`, leftover leaf `due:`, and an interview `event`
- `today/` and `year/` view configs using `inherit.reuse`
- Source `exclude` for those view directories (once lynguine CIP-0018 lands)

Tests (web or Interface-level): seasonal window uses `when`; Today is OR-today; Year groups by month; Save on Today updates the shared score file; view configs are not catalog rows; candidate inherit without `reuse` still ignores parent review.

## Acceptance Criteria

- [ ] Example tree exists in the referia package and does not require OneDrive
- [ ] Fixture covers identity `date`, leftover `due:`, interview `event`, plus `today/` and `year/`
- [ ] Tests listed in CIP-001C Testing Strategy pass against this fixture (or a tmp_path copy of it)
- [ ] CIP-0010 `complete` checkbox / filter-clear / `include_start_directory: false` still pass

## Implementation Notes

- Prefer extending the existing overview example over a third catalog dialect
- Skip live OneDrive paths in tests
- Soft depend: lynguine CIP-0018 for bind + exclude; mark tests xfail only if that is still unreleased, do not mock bind in referia

## Related

- CIP: 001C
- CIP-0010 example overview
- Application task: `2026-10-28_cip001C-today-year-configs`

## Progress Updates

### 2026-10-28

Task created (Ready) from CIP-001C acceptance.

### 2026-10-28 (later)

Completed: `examples/overview_inline_list/` includes `today/` and `year/` plus tall scores.
