---
id: "2026-10-23_viewer-visible-if"
title: "Honor visible_if on viewer: entries (web and Jupyter)"
status: "Completed"
priority: "Medium"
created: "2026-10-23"
last_updated: "2026-10-29"
category: "features"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- features
- web
- viewer
- visible_if
- jupyter
---

# Task: Honor visible_if on viewer entries

> Extends [2025-12-23_conditional-widget-visibility](2025-12-23_conditional-widget-visibility.md), which implemented `visible_if` for **review** widgets and templates. Viewer Liquid/HTML and Jupyter `_create_viewer` still ignore the key.

## Description

Review widgets already hide when `visible_if` is false, including against **inherited input** columns (parent output becomes child input when `inherit.writable: false`). Document-panel `editpdf` entries can carry the same key.

`viewer:` does not. Putting `visible_if: ch8Present` on a viewer Liquid block is accepted YAML and then ignored: `render_viewer()` / `render_viewer_tree()` never call `_visibility_style`, and Jupyter `_create_viewer` does not go through `extract_widget()`.

Typical use: hide chapter-specific viewer markdown (or inherited ancestor viewer blocks) when pdfpages says that chapter is absent, using the same Present flags already on the child row.

## Acceptance Criteria

- [x] `visible_if` on a `viewer:` entry uses the same rules as review widgets (string field name and `{field, equals}` / `{field, not}`)
- [x] False / missing condition omits or hides that viewer block on the web (including stacked inherit ancestor viewers)
- [x] True condition shows the block
- [x] Jupyter `_create_viewer` honours the same condition
- [x] Field updates that change a Present flag refresh viewer visibility (web OOB or equivalent), not only on full page load
- [x] Entries without `visible_if` are unchanged
- [x] Tests cover a viewer Liquid block gated on an inherited input column

## Implementation Notes

Reuse `_visibility_style` / `_checkbox_checked` in `referia/web/render.py`. Pass current row data into `render_viewer` / `render_viewer_tree` (today `render_viewer_html` evaluates Liquid but not visibility).

Do not skip the child's own hidden viewer from the DOM if HTMX needs to reveal it after a checkbox toggle — same `display:none` vs omit trade-off as review widgets. Inherited read-only ancestor viewers may omit.

Application YAML (e.g. `theses/examined/introduction`) can add `visible_if` on chapter-specific **viewer** entries once this lands. The viva header Liquid block should stay unconditional.

## Related

- CIP: 000B (web display)
- Backlog: `2025-12-23_conditional-widget-visibility` (review widgets; Completed)
- Application: `theses/examined/introduction/_referia.yml`, `theses/examined/pdfpages/_referia.yml`

## Progress Updates

### 2026-10-23

Task created with Proposed status after introduction stacked inherit: review `visible_if` already sees inherited Present flags; `viewer:` rendering does not.

### 2026-10-29

Accepted for implementation. Branch `backlog-2026-10-23-viewer-visible-if` from origin/main.

Implemented: `render_viewer` / `render_viewer_tree` apply `_visibility_style`; hidden viewers stay in the DOM with `display:none` so HTMX can reveal them. Field updates that match a viewer `visible_if` OOB-swap that viewer. Jupyter `_create_viewer` binds the same condition.
