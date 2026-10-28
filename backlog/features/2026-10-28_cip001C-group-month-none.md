---
id: "2026-10-28_cip001C-group-month-none"
title: "inline_list _group month and none"
status: "Completed"
priority: "High"
created: "2026-10-28"
last_updated: "2026-10-28"
category: "features"
related_cips: ["001C"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- features
- web
- inline_list
- grouping
- cip001C
---

# Task: inline_list `_group: month` and `_group: none`

> Linked CIP: 001C. Year overview groups by month of `when`; Today is a flat list.

## Description

`_INLINE_LIST_GROUP_BY` in `referia/web/routes.py` is currently `{directory, version}`. Unknown `_group` falls back to `directory`.

Add:

- `month` — bucket on `when` (YYYY-MM from parseable date; empty/unparseable → a single fallback bucket, not a crash)
- `none` — no grouping (flat working set)

Existing `directory` / `version` unchanged.

## Acceptance Criteria

- [ ] `_group: month` groups visible rows by calendar month of `when`
- [ ] Unparseable or missing `when` does not raise; those rows sit in a documented fallback bucket
- [ ] `_group: none` renders a flat list (no directory headings)
- [ ] Unknown `_group` still falls back to `directory`
- [ ] Seasonal root can keep `_group: directory`; Year uses `month`; Today uses `none`
- [ ] Tests: month buckets from `when`; Today ungrouped; unknown still `directory`

## Implementation Notes

- Touch: `referia/web/routes.py` (`_INLINE_LIST_GROUP_BY` / grouping helper). Jupyter inline_list should follow the same names if it shares the helper.
- Parse both ISO `YYYY-MM-DD` and DatePicker `YYYYMMDD` if `when` may be either after Liquid coalesce
- Do not add a calendar-grid named layout (out of scope)

## Related

- CIP: 001C
- CIP-0010 (`inline_list` grouping by directory)

## Progress Updates

### 2026-10-28

Task created (Ready) from CIP-001C acceptance.

### 2026-10-28 (later)

Completed: `_group` accepts `month` and `none`.
