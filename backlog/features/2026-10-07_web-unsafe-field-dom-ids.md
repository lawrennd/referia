---
id: "2026-10-07_web-unsafe-field-dom-ids"
title: "Web UI: safe DOM ids for field names with spaces (and load-time warning)"
status: "In Progress"
priority: "High"
created: "2026-10-07"
last_updated: "2026-10-07"
category: "features"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- web
- htmx
- populate
- validation
---

# Task: Safe widget DOM ids for non-CSS-safe field names

> Backlog tasks are DOING the work defined in CIPs (HOW).
> Linked CIP: 000B (web display).

## Description

Spreadsheet-oriented review configs often use field names with spaces
(e.g. `Importance Fairness`, `Notes or Comments`). Those names are valid as
Excel columns and Jupyter data keys, but **invalid as HTML ids / CSS
`#id` selectors**. HTMX out-of-band swaps use `querySelector`, so a response
targeting `#widget-Importance Fairness` never finds the textarea — the status
bar can show “Populated” while the box stays empty.

### Policy (layered)

| Layer | Behaviour |
|-------|-----------|
| **Core / Jupyter** | Do **not** reject or rename spaced field names. They are intentional for spreadsheet UX. Lynguine already warns separately about Liquid proxy variable names. |
| **Web renderer** | **Must** rewrite ids to a CSS-safe form (e.g. spaces → `_`) and percent-encode path segments in `hx-post` URLs. Correctness depends on this. |
| **Web load** | **Should** warn once when a config’s widget specs contain field names that need rewriting, so authors see the issue before clicking Populate. |

This keeps web constraints in the web layer (progressive augmentation /
explicit–implicit separation) without forcing Excel-friendly column names to
become programming identifiers.

## Acceptance Criteria

- [x] Widget container ids and PopulateButton `hx-indicator` selectors use a
      CSS-safe fragment derived from the field name (no raw spaces).
- [x] Populate / field `hx-post` paths percent-encode field names.
- [x] OOB populate refresh updates the target textarea for fields such as
      `Importance Fairness`.
- [x] Unit tests cover sanitisation, encoded URLs, and a one-shot rewrite
      warning at render time.
- [ ] On `WebReviewer` load (or first `get_widget_specs()`), scan review
      widget `field` / PopulateButton targets and log a clear warning for each
      distinct name that would be rewritten — without warning on every
      re-render of the page.
- [ ] Document the policy briefly (module docstring or short note near
      `_widget_dom_id` / `WebReviewer`) so future load-path validation does
      not “fix” this by rejecting spaced names in core.
- [ ] Optional: prefer camelCase / underscored field names in new example
      configs where spreadsheet display names are not required.

## Implementation Notes

**Done (commit `65b808f` and follow-ups):**

- `referia/web/render.py`: `_widget_dom_id()`, `_url_path_segment()`,
  render-time one-shot `WARNING` via `_warned_dom_ids`.
- Tests in `tests/test_web_render.py`.

**Remaining:**

- Add something like `warn_unsafe_widget_dom_ids(specs)` and call it from
  `WebReviewer` init / first widget-spec materialisation so `referia serve`
  logs the issue when the config loads.
- Decide whether to keep or thin the render-time warning once load-time
  coverage exists (backstop vs single site).

**Do not:**

- Fail config load for spaced names.
- Change lynguine mapping / Liquid proxy rules as part of this task.

## Related

- CIP: 000B
- Commit: `65b808f` — sanitise field names to CSS-safe HTML ids
- Symptom: Check fair / Populate shows status OK but fairness textarea empty
- Related lynguine noise: “Column … is not a valid variable name” for
  `*_modified` / `*_created` columns (separate concern)

## Progress Updates

### 2026-10-07

Diagnosed Fairness populate: LLM/status path succeeded; HTMX OOB failed
because `#widget-Importance Fairness` is not a valid selector. Implemented
DOM-id sanitisation + URL encoding + render-time warning. Remaining work is
load-time warning on `WebReviewer` and a short policy note.
