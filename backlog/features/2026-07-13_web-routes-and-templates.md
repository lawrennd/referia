---
id: "2026-07-13_web-routes-and-templates"
title: "Web display system: HTMX routes and Jinja2 templates"
status: "Completed"
priority: "High"
created: "2026-07-13"
last_updated: "2026-07-13"
category: "features"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: ["2026-07-13_web-widget-renderer"]
tags:
- backlog
- web
- htmx
- routes
- templates
---

# Task: Web display system: HTMX routes and Jinja2 templates

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Wire up the FastAPI routes that handle the full review interaction loop:
loading a record, updating a field, navigating to the next record, and saving.
Implement the Jinja2 templates and minimal CSS that produce a usable review
interface in the browser.

## Acceptance Criteria

- [x] `GET /` renders the full review page for the current index (HTML response)
- [x] `GET /record` returns the review panel HTML fragment for `?index=<value>` (HTMX partial swap)
- [x] `POST /field/{column}` accepts a form value, calls `WebReviewer.set_value()`, returns HTML fragments for all affected widgets via HTMX OOB swaps
- [x] `POST /save` calls `WebReviewer.save_flows()`, returns a status fragment
- [x] `POST /populate/{field}` skeleton route (compute wiring deferred to follow-on)
- [x] `GET /indices` returns the index selector widget fragment
- [x] Jinja2 templates exist for:
  - [x] `base.html` (page shell with HTMX `<script>` tag + auto-hide status JS)
  - [x] `review_panel.html` (index selector + viewer left / review form right)
  - (status fragments returned as inline HTML strings, no separate template needed)
- [x] CSS in `referia/web/static/style.css` provides clean two-column sticky-viewer layout with full widget styles
- [x] Index navigation updates the review panel without a full page reload (HTMX swap)
- [x] Field edits update only the affected widget fragments (HTMX OOB swap)

## Implementation Notes

Route file: `referia/web/routes.py`, registered with the FastAPI app via
`app.include_router(router)`.

A `WebReviewer` instance should be stored as FastAPI application state
(`app.state.reviewer`) so all routes can access it without re-loading on each
request.

HTMX pattern for field updates:

```html
<textarea
  name="Comment"
  hx-post="/field/Comment"
  hx-trigger="change"
  hx-target="#widget-Comment"
  hx-swap="outerHTML">
{{ value }}
</textarea>
```

The route returns a fresh rendered widget fragment; HTMX replaces the element
in-place. For dependent fields, use HTMX out-of-band swaps (`hx-swap-oob`).

CSS layout should mirror the logic in `referia/util/jupyter.py` (full-width
cells, no overflow scroll on the review column).

## Related

- CIP: 000B
- PRs: 
- Documentation: 

## Progress Updates

### 2026-07-13

Task created following acceptance of CIP-000B.

### 2026-07-13 (implementation)

Implemented:
- `referia/web/routes.py` — FastAPI `APIRouter` with all six routes; `WebReviewer` stored in `app.state.reviewer`; HTMX OOB swap helper `_make_oob()` for field-update side-effects
- `referia/web/app.py` — updated to instantiate `WebReviewer` on the `startup` event and `include_router(router)`
- `referia/web/templates/base.html` — page shell with HTMX CDN, auto-hide status JS, includes `review_panel.html`
- `referia/web/templates/review_panel.html` — two-column layout: index selector nav, sticky viewer column, review form column
- `referia/web/static/style.css` — full widget style library (textarea, text, slider, select, radio, checkbox, buttons) plus two-column sticky-viewer layout
- `WebReviewer.get_viewer_specs()`, `get_review_specs()`, `render_viewer_html()` helpers added to separate viewer from review specs
