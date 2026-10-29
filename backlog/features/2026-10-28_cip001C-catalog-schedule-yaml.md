---
id: "2026-10-28_cip001C-catalog-schedule-yaml"
title: "Root catalog YAML: due, event, notes, when, on_today"
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
- catalog
- yaml
- schedule
- cip001C
---

# Task: Root catalog YAML — due, event, notes, when, on_today

> Linked CIP: 001C. Application config lives in the OneDrive referia tree; keep a package-testable fragment in `examples/` via the sibling example task.

## Description

Extend the CIP-0010 tall catalog store and chrome so schedule is root-owned:

- `output.columns`: `complete`, `due`, `event`, `notes`
- Review widgets: existing `Checkbox`, `DatePicker`, `Text`, `SaveButton`
- Derived `when` (event else due) and `on_today` (event or due equals today) via `render_liquid` + `today` if Liquid can compare DatePicker `YYYYMMDD` to ISO `today`; new compute names only if it cannot
- Filters/sort/defaults window on `when`, not leaf `date`
- Root glob later gains `exclude: [today/**, year/**]` (lynguine CIP-0018); this task can add the keys once that lands, or leave a comment in YAML

Do not auto-copy leaf `date` into `due`. Seeding leftover leaf `due:` and interview `event` is the today/year configs task.

## Acceptance Criteria

- [ ] Root `_referia.yml` declares the four store columns and matching widgets
- [ ] Seasonal `filter_defaults` use `when: today-30d … today+30d` (or a documented forward-weighted window), `complete: false`
- [ ] `date` remains projected as identity and is not the default clock
- [ ] `when` / `on_today` match CIP-001C (coalesce; OR-today)
- [ ] DatePicker `YYYYMMDD` vs ISO `today` is either normalised in Liquid or given an ISO widget option — documented, not pretended
- [ ] Save updates `catalog-scores.yml`; leaf `_referia.yml` unchanged; `due_modified` / `event_modified` appear via existing per-field timestamps

## Implementation Notes

- Primary file: `~/Library/CloudStorage/OneDrive-Personal/referia/_referia.yml` (not this git repo)
- Package tests can use `examples/overview_inline_list/` (see `2026-10-28_cip001C-example-overview`)
- Prefer existing compute; do not add `coalesce_dates` / `date_equals_today` unless Liquid cannot express the contract
- `exclude` on the catalog source waits for lynguine `2026-10-28_cip0018-directory-source-exclude`

## Related

- CIP: 001C
- CIP-0010 root catalog
- lynguine CIP-0018

## Progress Updates

### 2026-10-28

Task created (Ready) from CIP-001C acceptance.

### 2026-10-28 (later)

Completed: tall `due` / `event` / `notes`; `when` / `on_today` derived in `WebReviewer.get_value`.
