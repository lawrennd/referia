---
id: "2026-07-13_web-routes-and-templates"
title: "Web display system: HTMX routes and Jinja2 templates"
status: "Proposed"
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

- [ ] `GET /` renders the full review page for the current index (HTML response)
- [ ] `GET /record/{index}` returns the review panel HTML fragment for the given index
- [ ] `POST /field/{column}` accepts a form value, calls `WebReviewer.set_value()`, returns HTML fragments for all affected widgets
- [ ] `POST /save` calls `WebReviewer.save_flows()`, returns a status fragment
- [ ] `POST /populate/{field}` triggers a compute function and returns the updated widget fragment
- [ ] `GET /indices` returns the index selector widget fragment
- [ ] Jinja2 templates exist for:
  - [ ] `base.html` (page shell with HTMX `<script>` tag)
  - [ ] `review_panel.html` (index selector + viewer + review widgets)
  - [ ] `status.html` (save/populate feedback fragment)
- [ ] CSS in `referia/web/static/style.css` provides a clean, readable two-column layout (viewer left, review form right) with no external UI framework
- [ ] Index navigation updates the review panel without a full page reload (HTMX swap)
- [ ] Field edits update only the affected widget fragments (HTMX OOB swap or targeted swap)

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
