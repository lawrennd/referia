---
id: "2026-10-11_inline-list-same-page"
title: "display.layout inline_list — same-page list, rows, filter/sort"
status: "In Progress"
priority: "High"
created: "2026-10-11"
last_updated: "2026-10-11"
category: "features"
related_cips: ["0010"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-10-11_root-load-referia-yml"
tags:
- backlog
- features
- web
- jupyter
- display
- layout
- filters
- sort
- cip0010
---

# Task: Same-page list via display.layout inline_list

> Linked CIP: 0010 (tall-first). REQ-000E named layouts.
> Supersedes: `2026-10-11_overview-pattern-a-filters`.

## Description

Implement the simplified overview chrome: lynguine supplies **tall** discovery + tall scores; referia `display.layout: inline_list` shows the whole working set on one page.

When `layout` is `inline_list`:

1. Inject Liquid **`rows`** (list of dicts for the filtered+sorted tall working set) into the viewer.
2. Render ordinary **`review:`** widgets **once per visible row** (tall `set_index(key)` + `set_value(field)` under the hood).
3. **Hide** the index selector; show **filter + sort** on tall column names instead.
4. Default layout remains `side_by_side` (today’s two-column chrome).

No `mode: catalog`. No required `wide_flatten`. Same behaviour contract on **web and Jupyter**.

## Acceptance Criteria

- [x] Config accepts `display.layout: side_by_side | inline_list` (default `side_by_side`); unknown names fail clearly
- [x] Under `inline_list`, viewer Liquid can `{% for row in rows %}` with `row.<column>` from tall input and output columns
- [x] Under `inline_list`, `review:` widgets appear per visible row; edits persist tall scores (e.g. `complete`)
- [x] Under `inline_list`, index selector is hidden; `filters:` + `sort:` drive the working set (tristate boolean, date_range, categorical; default clear)
- [ ] Works on web; Jupyter gets the same behavioural contract (list + filter/sort, not one-row browsing as primary chrome)
- [x] Example root `_referia.yml`: tall `yaml_directory` + tall output + `inline_list` + filter/sort (descendants-only when lynguine option lands)
- [x] Tests: list render, tall Save, filter/sort shrink/reorder `rows`; no catalog mode flag
- [ ] `side_by_side` reviews unchanged except where they opt into `filters:` / `sort:`

## Implementation Notes

- **lynguine:** `include_start_directory: false` landed in lynguine (`2026-10-11_directory-include-start-directory`)
- **referia:** `WebReviewer` / `review_panel.html` / `render.py` / routes — field POST carries row key via `hx-vals`
- Precedent for list-of-dicts in Liquid: series `entries`
- Filter/sort are part of this task (they *are* list navigation), not a separate product mode
- Singleton auto-hide for `side_by_side` remains `2026-10-11_singleton-navigation-chrome` (REQ-000D)

## Related

- CIP: 0010
- Supersedes: `2026-10-11_overview-pattern-a-filters`
- Depends on: `2026-10-11_root-load-referia-yml`
- Soft depend: lynguine `2026-10-11_directory-include-start-directory` (done)
- Sibling: `2026-10-11_singleton-navigation-chrome`

## Progress Updates

### 2026-10-11

Task created (Ready) after tall-first design shift — replace Pattern A / wide_flatten overview plan.

### 2026-10-11 (web vertical slice)

In Progress — web path implemented:
- `get_display_layout` / `get_rows` / `working_indices` + filter state on `WebReviewer`
- viewer Liquid `rows` injection under `inline_list`
- `review_panel.html` single-column list; per-row forms; filter/sort bar; `/filters` routes
- field updates accept `index` from `hx-vals`; scoped widget DOM ids
- Unit tests for layout, rows, filter/sort, render scoping
- Remaining: Jupyter list chrome; smoke-test example under `examples/overview_inline_list/`
- Example added: `examples/overview_inline_list/`
- Web chrome now directory-listing style: CIP-000C-like filter bar, `<ul>` rows with
  leading Complete checkbox + title/date/desc, compact extras for other review fields
