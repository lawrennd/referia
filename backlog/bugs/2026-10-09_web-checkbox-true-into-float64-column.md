---
id: "2026-10-09_web-checkbox-true-into-float64-column"
title: "Web UI: Checkbox True fails when pandas column dtype is float64"
status: "Proposed"
priority: "High"
created: "2026-10-09"
last_updated: "2026-10-09"
category: "bugs"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- web
- checkbox
- pandas
- dtype
- set_value
---

# Bug: Checkbox updates fail with `Invalid value 'True' for dtype 'float64'`

## Description

While reviewing `theses/examined/introduction` in the web UI (2026-10-09
~17:45), toggling a chapter checkbox failed. The server log
(`referia-server.log` under the OneDrive referia root) recorded:

```
ERROR:referia.web.routes:2026-10-09 17:45:20,483:Update failed column='ch1SummaryIncludeHistory'
…
TypeError: Invalid value 'True' for dtype 'float64'
```

### What happened (sequence)

1. The form posted a Checkbox/Flag field (`ch1SummaryIncludeHistory` —
   “Include custom query conversation as context” on Chapter 1).
2. `referia.web.routes._coerce_form_value` correctly turned the HTML form
   string into a Python `bool` (`True`).
3. `WebReviewer.set_value` → lynguine `CustomDataFrame.set_value` assigned
   that bool with pandas `.at[index, col] = value`.
4. The column’s dtype was already `float64` (typical when a series was
   created empty / all-`NaN` and never held real booleans). Pandas refused
   to store `True` in a float64 block and raised
   `LossySetitemError` → `TypeError: Invalid value 'True' for dtype 'float64'`.
5. The route logged `Update failed` and the UI status bar showed a generic
   error; the checkbox state did not persist.

This is independent of the collapsible-section work; it surfaces when any
Checkbox is toggled on a float64-backed column. Thesis `*IncludeHistory`
and similar flags are likely hits because those columns often appear only
after template expansion and start life as empty numeric series.

### Where it shows in the stack

- `referia/web/routes.py` — `root_update_field` / field update path
- `referia/assess/web_review.py` — `set_value`
- `lynguine/assess/data.py` — `set_value` → `self._d[typ].at[index, col] = value`

## Acceptance Criteria

- [ ] Toggling a Checkbox/Flag whose column is currently `float64` (or all
      NaN) succeeds and stores a boolean (or an agreed serialisable
      equivalent such as `True`/`False` in an object/`bool` dtype).
- [ ] Unchecking stores `False` (not only clearing to NaN), so the widget
      round-trips.
- [ ] Failure mode is covered by a unit/integration test (web coerce +
      set_value on a float64 column, or lynguine `set_value` alone if the
      fix lands there).
- [ ] Existing non-checkbox float columns are unchanged.

## Implementation Notes

**Likely fix layers (prefer one clear owner):**

1. **lynguine `set_value`** (infrastructure): when assigning a `bool` into a
   numeric/NaN column, upcast the column (e.g. to `object` or pandas
   boolean dtype) instead of raising. Aligns with “explicit, predictable”
   writes from application layers.
2. **referia web / WebReviewer** (application): before `set_value`, if the
   widget is Checkbox/Flag and the series dtype cannot hold bool, convert
   the column dtype. Use when lynguine change is deferred
   (progressive augmentation).

Avoid silently writing `1.0`/`0.0` unless that is already the on-disk
convention for that field — Jupyter checkboxes historically use bools.

**Reproduction**

1. `referia serve --root <OneDrive/referia>`
2. Open `theses/examined/introduction`, expand Chapter 1.
3. Toggle “Include custom query conversation as context”.
4. Observe status error; confirm traceback in `referia-server.log` for
   `ch1SummaryIncludeHistory` / `Invalid value 'True' for dtype 'float64'`.

## Related

- CIP: 000B (web field update path)
- Log: OneDrive `referia/referia-server.log` @ 2026-10-09 17:45:20
- Config: `theses/examined/introduction/_referia.yml` (`thesis_section`
  `%prefix%SummaryIncludeHistory` Checkbox)

## Progress Updates

### 2026-10-09

Observed in server log during live thesis introduction review; documented
as Proposed. Not fixed yet.
