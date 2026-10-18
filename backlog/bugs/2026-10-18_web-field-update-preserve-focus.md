---
id: "2026-10-18_web-field-update-preserve-focus"
title: "Preserve focus when web field update records (stop OOB rebuild stealing caret)"
status: "In Progress"
priority: "High"
created: "2026-10-18"
last_updated: "2026-10-18"
category: "bugs"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- bug
- web
- htmx
- focus
- status-bar
- oob
- affected_widgets
- CoE
---

# Bug: Web field update steals focus to the green status bar

> Backlog tasks are DOING the work defined in CIPs / CoE follow-ups (HOW→DO).
> Spawned by CoE `coe/2026-10-18_web-field-update-steals-focus.md`.
> Related CIP: 000B (web display; `affected_widgets` stub).

## Description

When a reviewer leaves a field in `referia serve`, HTMX posts to
`/field/{column}`, shows `✓ Updated` in the fixed green `#status-bar`, and
OOB-replaces **every** form widget because `WebReviewer.affected_widgets`
conservatively returns all field-bearing columns. The control that just
received focus is destroyed, so the caret vanishes and attention is drawn to
the green toast.

The green status feedback is intentional. Destroying the focused control is
not.

## Acceptance Criteria

- [x] Field HTMX swaps that target `#status-bar` use
      `hx-swap="innerHTML focus-scroll:false"` (same discipline as the record
      index select). Apply consistently to other status-bar posts where cheap
      (Save / Reload / Populate) unless a reason not to is documented.
- [x] `POST /field/{column}` (and root-prefixed equivalent) does **not**
      OOB-replace the triggering column’s widget. Prefer also skipping any
      currently focused widget if detectable without fragile heuristics; at
      minimum never rebuild the field that fired the request.
- [x] Optional interim: narrow `affected_widgets` enough that unchanged
      independent fields are not rebuilt on every blur — without blocking on a
      full dependency-graph CIP.
- [x] Green `✓ Updated` toast still appears on successful update.
- [x] Computed / timestamp / combinator side-effects that *do* depend on the
      changed column still refresh (do not regress real dependent updates).
- [x] Unit/route test(s): response OOB set excludes the triggering column;
      existing OOB tests updated accordingly.
- [ ] Smoke: edit field A, Tab (or click) to field B — B keeps focus while the
      status toast may still show.

## Implementation Notes

Likely touch points:

- `referia/web/render.py` — `_htmx_field_attrs` swap string
- `referia/web/routes.py` — `update_field` / `root_update_field` OOB loop;
  optionally `_make_oob` / exclude list
- `referia/assess/web_review.py` — `affected_widgets` (interim exclude of
  `column`, or slightly less conservative set)
- `tests/test_web_routes.py` — OOB expectations currently assume all affected
  names are returned

Out of scope for this task (optional later CIP): full widget dependency graph
for `affected_widgets` (already deferred in the method docstring).

Related prior art: `backlog/features/2026-10-11_preserve-scroll-across-record-switch.md`
(`focus-scroll:false` on index select).

## Related

- CoE: `coe/2026-10-18_web-field-update-steals-focus.md`
- CIP: 000B
- Docs: `backlog/documentation/2026-07-14_web-interface-event-architecture.md`
- Prior: `2026-10-11_preserve-scroll-across-record-switch`

## Progress Updates

### 2026-10-18

Task created from CoE after operator report of focus jump to green status bar
on field leave. No code change yet — backlog-first.

### 2026-10-18 (status)

Moved Proposed → Ready → In Progress; starting implementation.

### 2026-10-18 (implementation)

Applied `focus-scroll:false` on field/status-bar HTMX swaps; `update_field` /
`root_update_field` skip OOB for the triggering column. Route tests updated.

### 2026-10-18 (narrow affected_widgets)

First patch was insufficient: skipping only the triggering field still
OOB-replaced the *newly focused* field (and every other widget). Narrowed
`affected_widgets` to `visible_if` dependents + combinator widget fields.
Live smoke after serve restart.
