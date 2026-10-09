---
id: "2026-10-09_web-checkbox-true-into-float64-column"
title: "Web UI: Checkbox True fails when pandas column dtype is float64"
status: "Completed"
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

- [x] Toggling a Checkbox/Flag whose column is currently `float64` (or all
      NaN) succeeds and stores a boolean (or an agreed serialisable
      equivalent such as `True`/`False` in an object/`bool` dtype).
- [x] Unchecking stores `False` (not only clearing to NaN), so the widget
      round-trips.
- [x] Failure mode is covered by a unit/integration test (web coerce +
      set_value on a float64 column, or lynguine `set_value` alone if the
      fix lands there).
- [x] Existing non-checkbox float columns are unchanged.

## Implementation Notes

**Fix (referia progressive augmentation):** override
`referia.assess.data.CustomDataFrame.set_value` to call `_update_type`
before `super().set_value`. When a Python/`numpy` bool is written into a
numeric non-bool column, upcast to pandas nullable `"boolean"`. String
into numeric still upcasts to `"object"` (existing behaviour).

lynguine remains the long-term home if this is generalised; referia owns
the review-facing path today.

## Related

- CIP: 000B (web field update path)
- Log: OneDrive `referia/referia-server.log` @ 2026-10-09 17:45:20
- Config: `theses/examined/introduction/_referia.yml` (`thesis_section`
  `%prefix%SummaryIncludeHistory` Checkbox)

## Progress Updates

### 2026-10-09

Observed in server log during live thesis introduction review; documented
as Proposed. Not fixed yet.

### 2026-10-09 (fixed)

Implemented in `referia.assess.data.CustomDataFrame.set_value` +
`_update_type`. Tests in `referia/tests/test_assess_data.py`. Status →
Completed.
