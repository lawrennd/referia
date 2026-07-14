---
id: "2026-07-14_web-change-event-unreliable"
title: "Per-field change events not reliably firing before Save; /save re-runs computes as side effect"
status: "Proposed"
priority: "High"
created: "2026-07-14"
last_updated: "2026-07-14"
tags: ["web", "htmx", "architecture", "compute", "slider"]
related_cips: []
---

# Bug: Per-field change events unreliable; Save re-runs computes unsafely

## Status

- [x] Identified
- [ ] Root-cause confirmed
- [ ] Fixed
- [ ] Tests added
- [ ] Closed

## Summary

The per-field `hx-trigger="change"` events that update in-memory state and
trigger computes are **not reliably firing before the Save button is clicked**.
A stopgap fix (`hx-include="#review-form"` on the Save button) makes
persistence work correctly, but introduces a new problem: the Save route now
re-runs `set_value` → `_value_updated` → computes for every field on every
Save, even when those computes already ran via the change-event path.

## Symptoms

- Slider changes are not reflected in dependent computed fields unless the user
  moves the slider, releases it, *and then* clicks Save as a separate gesture.
- In-memory state is not updated if the user moves a slider and clicks Save in
  one continuous motion (drag → release on the Save button).
- With the current stopgap, computes run twice when the change-event path did
  complete: once on change, once on Save.

## Root Cause

HTML `<input type="range">` elements fire the `change` event only on
**mouseup** — when the user physically releases the mouse button.  If the user:

1. Clicks on the slider track → depresses mouse button.
2. Drags the slider thumb to a new value.
3. Moves the mouse to the Save button *while still holding the button down*.
4. Releases on the Save button.

…the `change` event fires on the Save button's element (a `<button>`), not on
the slider.  HTMX's `hx-trigger="change"` on the slider never fires; the Save
POST fires without the slider's per-field POST having run.

Separately, `<textarea>` and `<input type="text">` fire `change` on blur (loss
of focus).  If the user types in a field and immediately clicks Save without
tabbing out first, the `change` event may not have fired either.

## Current Stopgap (and Its Problems)

`hx-include="#review-form"` was added to the Save button.  This causes HTMX to
include all form field values in the Save POST.  The `/save` route calls
`reviewer.set_value(col, value)` for each field before `save_flows()`.

**Problems with this stopgap:**

1. **Masks the underlying bug.** The change-event path is still unreliable.
   Silent failures in that path (e.g., failed POST, server error) are hidden
   because Save recovers.  OOB widget refreshes that should have appeared on
   change do not appear, but the user doesn't notice.

2. **Re-runs computes on Save.** `set_value` → `_value_updated` runs for every
   field.  For impure compute functions (LLM calls, timestamp writes, counter
   increments) this can produce different results or have unwanted side effects.

3. **Compute ordering is wrong.** On Save, all fields are processed in spec
   order.  On change, only the changed field and its dependents are processed.
   A combinator that depends on field A and field B, where B depends on A, may
   see an inconsistent intermediate state during Save if the ordering differs.

## Correct Fix

### Option 1 (Recommended) — Fix the trigger; simplify Save

Change the slider trigger to fire before the user can click Save:

```html
<!-- In render.py _htmx_field_attrs for range inputs: -->
hx-trigger="change, mouseup"
```

Or, add a small delay to catch the mouseup in all cases:

```html
hx-trigger="change, mouseup delay:50ms"
```

For `<textarea>` and `<input type="text">`:

```html
hx-trigger="change, blur"
```

`blur` fires when focus leaves the element, which covers the
"type → immediately click Save" case.

Then restore `/save` to:

```python
@router.post("/save")
async def save(request: Request):
    reviewer = _reviewer(request)
    try:
        reviewer.save_flows()
        return HTMLResponse('<span class="status-ok">&#10003; Saved</span>')
    except Exception as exc:
        ...
```

No form parsing, no `set_value`, no compute re-runs.

### Option 2 — Use `hx-sync` to serialise requests

Add to the Save button:

```html
hx-sync="closest form:queue last"
```

This tells HTMX to wait for all in-flight requests on the same form to
complete before sending the Save POST.  If the slider's per-field POST is still
in-flight when Save is clicked, HTMX queues the Save and waits.

Still restore `/save` to just `save_flows()`.

### Option 3 — Belt-and-braces without compute side effects

If belt-and-braces is still wanted, separate value-writing from compute
triggering in `/save`:

```python
# Apply raw form values directly, bypassing _value_updated
for spec in reviewer.get_review_specs():
    col = spec.get("field")
    if col and col in form:
        value = _coerce_form_value(form.get(col), spec)
        reviewer.set_raw_value(col, value)  # new method: no _value_updated
reviewer.save_flows()
```

This requires a new `set_raw_value` method on `WebReviewer`/`CustomDataFrame`
that writes the value without triggering computes.

## Investigation Needed

Before fixing, confirm:

1. **Reproduce the bug without the stopgap:** Temporarily remove `hx-include`
   from the Save button and verify that slider-then-Save fails to persist.

2. **Check textarea blur behaviour:** Does typing in a textarea and immediately
   clicking Save lose the typed value?

3. **Verify `value != old_value` guard coverage:** In `set_value`, does the
   guard prevent compute re-runs in all cases, including for timestamp
   combinators?

4. **Check HTMX version for `hx-sync` support:** Ensure the bundled HTMX
   supports `hx-sync` with `queue last` semantics.

## Acceptance Criteria

- Moving a slider and immediately clicking Save persists the correct value.
- Typing in a textarea and immediately clicking Save persists the typed text.
- Computes run exactly once per field change, not again on Save.
- If the change-event POST fails (server error), Save is blocked or warns
  rather than silently recovering.
- Tests verify the above using FastAPI TestClient with simulated HTMX headers.

## Progress Updates

### 2026-07-14
Bug identified during review of the `hx-include` stopgap fix.  Not yet fixed.
The stopgap restores persistence correctness but the architectural issues above
remain open.
