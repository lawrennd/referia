---
id: "2026-10-18_web-field-update-steals-focus"
title: "Web field update OOB refresh destroys focused control; green status bar feels like focus target"
class: 1
owner: "Neil D. Lawrence"
status: "Analysed"
created: "2026-10-18"
last_updated: "2026-10-18"
incident_date: "2026-10-18"
spawned_cips: []
spawned_backlog:
  - "2026-10-18_web-field-update-preserve-focus"
spawned_requirements: []
tags:
  - coe
  - web
  - htmx
  - focus
  - status-bar
  - oob
  - affected_widgets
---

# CoE: Web field update steals focus to the green status bar

> **Correction of Error** (CIP-0016). CoEs are orthogonal to the WHY→WHAT→HOW→DO
> hierarchy. They examine where the hierarchy broke and produce items at the appropriate
> level to fix it. The CoE itself does not implement fixes — it produces outputs (CIPs,
> backlog tasks, requirements, tripwires) that are implemented separately.
>
> Blameless: focus on process, tooling, and design — not people.
>
> Analysis depth: Class 0 may abbreviate Timeline, Incident questions, and 5 Whys.
> Class 1+ should complete them in full.

## Summary

On 2026-10-18, while reviewing under `referia serve`, moving focus out of a
field (so the update is recorded) briefly makes focus disappear toward the
green bottom status bar (`✓ Updated`). The green toast is intentional HTMX
feedback into `#status-bar`. The focus loss is not: `POST /field/{column}`
returns that status **and** OOB-replaces every field widget via
`affected_widgets()`, which currently returns **all** field-bearing columns.
The control the user just entered is destroyed mid-focus. Recurrence
prevention: field swaps must not replace the focused (or triggering) widget,
and should use `focus-scroll:false` like the record selector already does.

## Severity

**Class**: 1

- Class 0 — Internal only, easily reversible. No user-facing impact.
- Class 1 — Maintainer/contributor workflow impact (not yet externally impactful).
- Class 2+ — External impact: downstream users, deployed behaviour, customer/legal exposure.

**Blast radius**: Any review edited via `referia serve` where leaving a
text-like field (`change, blur`) or changing a control triggers
`POST /field/{column}`. Jupyter widget path unaffected (no `#status-bar` /
OOB rebuild). Worse on dense forms because every widget is rebuilt on each
field leave.

## Impact

Operator tabbing or clicking between review fields sees a momentary loss of
caret/focus and a green flash at the bottom of the page. Typing rhythm and
keyboard navigation are interrupted. No data loss — values still record — but
the UI feels broken and slows review throughput.

## Timeline

- CIP-000B — Web layer ships `affected_widgets(column)` as a conservative
  “refresh all field widgets” stub; docstring defers a finer dependency graph
- 2026-07-14 — Event architecture docs describe status-bar primary target +
  OOB refreshes for affected widgets
- 2026-10-11 — Record-switch scroll work adds HTMX `focus-scroll:false` on the
  index select; field `hx-swap` left as plain `innerHTML`
- 2026-10-18 — Operator reports focus briefly jumps to the green bar when
  moving between fields after an update is recorded
- 2026-10-18 — Root cause confirmed: status-bar swap + full-form OOB rebuild
  destroys the newly focused control; CoE + backlog opened before code fix

## Evidence / metrics

- `_htmx_field_attrs` (`referia/web/render.py`): `hx-target="#status-bar"`,
  `hx-swap="innerHTML"` (no `focus-scroll:false`); text fields use
  `change, blur`
- `update_field` (`referia/web/routes.py`): returns
  `<span class="status-ok">✓ Updated</span>` plus `_make_oob` for every
  `affected_widgets(column)`
- `WebReviewer.affected_widgets` (`referia/assess/web_review.py`): returns all
  specs with `"field"`; documents deferred finer graph
- `#status-bar` fixed bottom, green on `.status-ok`
  (`referia/web/static/style.css`, `base.html` visibility JS)
- Contrast: index select already uses `hx-swap="innerHTML focus-scroll:false"`
  (`routes.py` ~440); backlog
  `2026-10-11_preserve-scroll-across-record-switch`

## What happened

Leaving a field correctly posts an update and shows success feedback, but the
response also rebuilds the entire form as OOB swaps. The element that received
focus after blur is replaced, so focus drops while the green status toast
appears — perceived as focus moving to the bar.

## Incident questions

### Detection

1. **When did you learn there was impact?**
   - 2026-10-18, during live web reviewing when moving focus after a field update.
2. **How did you learn there was impact?**
   - Operator report; confirmed by tracing HTMX field attrs → `update_field` →
     `affected_widgets` OOB path.
3. **How can we reduce the time-to-detect in half?**
   - Add an automated or smoke check: after simulating blur+focus on consecutive
     fields, the second control still owns `document.activeElement` (or its
     replacement preserves focus by not swapping that id).

### Diagnosis

4. **What was the underlying cause of the impact?**
   - Full-form OOB widget replacement on every field POST, plus HTMX focusing /
     scrolling toward the primary swap target (`#status-bar`) without
     `focus-scroll:false`.
5. **Was an internal activity underway during the incident?**
   - Yes — normal review entry under `referia serve`.
6. **How can we reduce the time-to-diagnose in half?**
   - Document in web event architecture: “status-bar feedback must never imply
     destroying the focused widget”; link field-update swaps to the same
     focus-scroll discipline as record switch.

### Mitigation

7. **When did impact return to pre-incident levels (or when will it)?**
   - When the spawned backlog task lands: field updates no longer OOB-replace
     the focused/triggering control, and field swaps use `focus-scroll:false`.
8. **How does the owner know the system/process is properly restored?**
   - Tabbing A→B after editing A keeps caret in B; green toast may still appear;
     unit/route tests assert triggering (and ideally focused) column omitted from
     OOB set or marked preserve.
9. **How did you determine where and how to mitigate?**
   - Matched symptoms to `#status-bar` + OOB; contrasted with existing
     `focus-scroll:false` on index select; read `affected_widgets` docstring.
10. **How can we reduce the time-to-mitigate in half?**
    - Treat “preserve focus/scroll on HTMX swap” as a checklist item for every
      new `hx-target` / OOB path, not only record switch.

## 5 Whys

1. **Why** does focus seem to jump to the green bar?
   - Because the focused input is destroyed while `#status-bar` becomes the
     visible HTMX update.
2. **Why** is the focused input destroyed?
   - Because the field POST OOB-swaps every widget returned by `affected_widgets`.
3. **Why** does `affected_widgets` return every field?
   - Because CIP-000B shipped a conservative stub and deferred a dependency graph.
4. **Why** was that safe enough to ship without focus criteria?
   - Because acceptance focused on “computed side-effects refresh,” not keyboard /
     focus continuity during blur-triggered posts.
5. **Why** did the later scroll/`focus-scroll` work not cover field updates?
   - Because it scoped to record-panel `#review-panel` / index select, not
     `_htmx_field_attrs` / `/field/{column}`.

**Root cause(s)**: Conservative all-widget OOB refresh without an interim
“do not replace the active control” rule, plus incomplete generalization of
HTMX `focus-scroll:false` from record switching to field updates. The green
status bar is correct feedback; pairing it with full-form rebuild makes focus
loss look like the bar stole focus.

## Traceability artifacts missing or incorrect

- [ ] Missing tenet (WHY)
- [ ] Missing requirement (WHAT)
- [ ] Missing CIP (HOW) — full dependency graph remains a deferred design; not
      required to fix focus steal
- [x] Missing backlog task (DO) — no task for preserve-focus on field update
- [ ] Incorrect/forbidden link direction
- [x] Template/runtime drift — event architecture implies “affected” refreshes;
      runtime refreshes *all* fields and kills focus
- [x] Other: `focus-scroll:false` applied to index select (2026-10-11) but not
      field / save / populate status-bar swaps

## Follow-up outputs

### Backlog tasks

- [x] Preserve focus on web field update (exclude focused/triggering widget from
      OOB; `focus-scroll:false` on field status swaps) — owner: Neil D. Lawrence —
      `backlog/bugs/2026-10-18_web-field-update-preserve-focus.md`

### CIPs

- None for now. A follow-on CIP for a real `affected_widgets` dependency graph
  remains optional (already noted in `web_review.py`); escalate only if narrowing
  refresh without full graph proves insufficient or unsafe.

### Requirements

- None

### Validation tripwires

- [ ] Route/unit test: `POST /field/{column}` OOB set does not include the
      triggering column (and documents focused-column policy) — owner: Neil D.
      Lawrence — implement with the backlog task
- [ ] Smoke: tab from field A to B after edit; B retains focus while status toast
      may still show — owner: Neil D. Lawrence

## Checklist

- [x] Severity class assigned
- [x] Single-threaded owner named
- [x] Summary written (stand-alone)
- [x] Impact documented
- [x] Timeline documented (required Class 1+; optional Class 0)
- [x] Incident questions answered (Detect / Diagnose / Mitigate)
- [x] 5 Whys completed (abbreviated OK for Class 0; full for Class 1+)
- [x] Missing/incorrect traceability artifacts identified
- [x] Follow-up outputs listed with owners (and created)
- [x] CoE status updated to Analysed once outputs are created
- [ ] CoE status updated to Closed once outputs are implemented
