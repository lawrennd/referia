---
id: "2026-07-13_web-widget-renderer"
title: "Web display system: widget-to-HTML renderer"
status: "Completed"
priority: "High"
created: "2026-07-13"
last_updated: "2026-10-06"
category: "features"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: ["2026-07-13_web-reviewer-class"]
tags:
- backlog
- web
- rendering
- widgets
- html
---

# Task: Web display system: widget-to-HTML renderer

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Implement `referia/web/render.py` with functions that translate a widget spec
dict (as produced by `WebReviewer.get_widget_specs()`) and current data values
into HTML strings. This is the equivalent of `WidgetCluster.display()` for the
web backend.

## Acceptance Criteria

- [x] `render_widget(spec, value)` returns correct HTML for each widget type:
  - [x] `Textarea` → `<textarea>`
  - [x] `Text` → `<input type="text">`
  - [x] `IntSlider` / `BoundedIntText` → `<input type="range">` / `<input type="number">`
  - [x] `Dropdown` → `<select>` with `<option>` elements
  - [x] `Checkbox` → `<input type="checkbox">`
  - [x] `Markdown` (viewer) → rendered HTML via Python `markdown` library
  - [x] `SaveButton` / `ReloadButton` → `<button>` with appropriate HTMX attributes
  - [x] `PopulateButton` → `<button hx-post="/populate/{field}">`
- [x] `render_viewer(view_spec, data)` renders liquid/display viewer entries to HTML
- [x] Composite widget types (`CriterionCommentRaisesMeetsLowers` etc.) expand correctly via existing `Interface` expansion logic
- [x] Each rendered widget includes the correct HTMX attributes for live field updates (`hx-post`, `hx-target`, `hx-trigger`)
- [x] `visible_if` conditions are respected (hidden widgets rendered with `display:none` or excluded)

## Implementation Notes

The widget-to-HTML mapping from CIP-000B:

| `_referia.yml` type | HTML element |
|---|---|
| `Textarea` | `<textarea name="{column}" hx-post="/field/{column}" hx-trigger="change">` |
| `Dropdown` | `<select name="{column}" hx-post="/field/{column}" hx-trigger="change">` |
| `Markdown` (viewer) | `<div class="viewer">` + markdown-rendered content |
| `SaveButton` | `<button hx-post="/save" hx-target="#status">Save</button>` |

Composite expansion: call `Interface`'s existing expansion methods on the spec
before dispatching to `render_widget`, reusing the same logic that
`extract_review()` in `review.py` uses today.

Liquid viewer rendering can call `CustomDataFrame.view_to_value()` directly —
this is already Jupyter-independent.

## Related

- CIP: 000B
- PRs: 
- Documentation: 

## Progress Updates

### 2026-07-13

Task created following acceptance of CIP-000B.

### 2026-10-06

Marked Completed. `referia/web/render.py` and `tests/test_web_render.py` cover
the widget types above; cluster flattening lives in `WebReviewer._flatten_entries`.
CIP-0006 template expansion still happens in `Interface` before render.
