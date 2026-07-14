---
id: "2026-07-14_web-save-not-persisting"
title: "Web interface Save button did not persist updated field values"
status: "Completed"
priority: "High"
created: "2026-07-14"
last_updated: "2026-07-14"
related_cips: []
tags: ["web", "htmx", "fastapi", "persistence", "forms"]
---

# Bug: Web interface Save button did not persist updated field values

## Status

- [x] Identified
- [x] Root-cause confirmed
- [x] Fixed
- [x] Regression tests added
- [ ] Closed (pending review)

## Summary

After editing a field in the web review interface (e.g. moving the Score slider) and
clicking **Save**, the value returned to its previous state on reload.  The file on
disk was not updated.

## Symptoms

- User edits a slider or textarea in the browser.
- User clicks the Save button.
- The status bar confirms "Saved".
- On reload (or on next session), the original value is shown; the edit is lost.
- The `scores.yml` (or Excel) output file is unchanged.

## Root Cause Analysis

Three separate but compounding problems combined to cause the failure.

### Problem 1 — Save button carried no form data (`hx-include` missing)

The HTMX Save button issued a `POST /save` with **no body**.  HTMX only
auto-includes the value of the element that triggered the request; the other
widgets (slider, textarea) were not included.

`render.py` rendered the button as:

```python
f'<button hx-post="/save" hx-target="#status-bar" hx-swap="innerHTML">'
```

Because `hx-include` was absent the server received an empty form on every
Save click.  The in-memory reviewer state was never updated with the
user's edits.

### Problem 2 — `/save` route did not read form data at all

Even if the form values had arrived, the original `/save` handler only called
`reviewer.save_flows()` without first reading `request.form()`.  There was no
code to apply incoming form fields to the in-memory state before persisting.

### Problem 3 — HTML form strings not coerced to the correct Python type

HTML form submissions always deliver values as strings.  An `IntSlider` value
of `7` arrived as the string `"7"`.  Without explicit coercion `set_value`
stored `"7"` (a string) in the DataFrame; on reload this mis-typed value
could appear as `NaN` or raise a comparison error.

This same issue existed in the `/field/{column}` per-field update route, but
was masked there because the slider's `change` event often was not firing
reliably before Save was clicked.

### Secondary factor — `python-multipart` not installed in the active environment

`await request.form()` in FastAPI requires the `python-multipart` library.
It was declared in `pyproject.toml` but not installed in the user's conda
environment.  The missing library caused a `WARNING: Save failed: The
python-multipart library must be installed …` error that was silently swallowed
(only appearing in the status bar as a generic "Save failed" message).

## Fix

### 1. Add `hx-include="#review-form"` to the Save button (`render.py`)

```python
return (
    f'<button class="widget-button save-button" '
    f'hx-post="/save" hx-target="#status-bar" hx-swap="innerHTML" '
    f'hx-include="#review-form">'
    f"{_escape(label)}</button>"
)
```

`#review-form` is the `id` of the `<form>` element that wraps all review
widgets, so HTMX now captures every current widget value in the Save POST.

### 2. Update `/save` to apply form values before saving (`routes.py`)

```python
@router.post("/save")
async def save(request: Request):
    reviewer = _get_reviewer(request)
    form = await request.form()
    for spec in reviewer.get_review_specs():
        col = spec.get("field")
        if col and col in form:
            raw = form.get(col)
            value = _coerce_form_value(raw, spec)
            reviewer.set_value(col, value)
    reviewer.save_flows()
    ...
```

### 3. Add shared `_coerce_form_value` helper (`routes.py`)

```python
def _coerce_form_value(raw: Any, spec: dict | None) -> Any:
    if spec is None:
        return raw
    widget_type = spec.get("type", "")
    if widget_type in {"Checkbox", "Flag"}:
        return bool(raw and raw not in {"false", "off", "0", ""})
    if widget_type in {"IntSlider", "BoundedIntText", "IntText"}:
        try:
            return int(raw)
        except (TypeError, ValueError):
            return raw
    if widget_type in {"FloatSlider", "BoundedFloatText", "FloatText"}:
        try:
            return float(raw)
        except (TypeError, ValueError):
            return raw
    return raw
```

This is used by both `/save` and `/field/{column}`.

### 4. Install `python-multipart` in the active environment

```bash
pip install python-multipart
```

(Also declared as a dependency in `pyproject.toml`.)

## Tests Added

`tests/test_web_routes.py`:

- `TestGetRoot::test_save_button_includes_form_values` — Save button HTML
  must contain `hx-include="#review-form"`.
- `TestPostSave::test_save_applies_form_values_before_saving` — `set_value`
  is called for every form field *before* `save_flows`.
- `TestPostSave::test_save_applies_int_slider_as_integer` — `IntSlider`
  value arrives as `int`, not `str`.
- `TestPostSave::test_save_without_form_data_still_calls_save_flows` —
  Empty form is safe (no crash, save still happens).
- `TestCoerceFormValue::*` — 10 unit tests covering `IntSlider`, `FloatSlider`,
  `Checkbox`, `Textarea`, unknown types, and malformed input.

## Review: Was This the Right Fix?

**Partially.** The fix restored persistence correctness (values are now saved
correctly) and the type coercion (`_coerce_form_value`) was clearly missing and
needed.  However the "apply all form values on Save" approach has two
significant problems that make it the wrong long-term solution.

### Problem A — It buries the actual bug in the per-field `change` path

The fact that `hx-include` was *necessary* to make Save work means the
per-field `hx-trigger="change"` events were **not reliably updating in-memory
state before Save was clicked**.  That is a bug in the primary update path.

The `hx-include` fix makes the symptoms disappear without fixing the root cause.
If the change-event path is unreliable, it will continue to fail silently —
computed field refreshes (OOB swaps) will not appear in the browser, but the
user will not notice because Save eventually applies the value correctly.

### Problem B — Re-running computes on Save has unintended side effects

The `/save` route calls `reviewer.set_value(col, value)` for every form field,
which calls `_value_updated`, which runs combinator computes and updates
timestamps.  This means **computes run twice** when the full change-event path
did fire:

1. Once when the `change` event fires → `/field/{column}` → `set_value` →
   `_value_updated` → computes.
2. Again when Save fires → `/save` → `set_value` → `_value_updated` →
   computes.

The `value != old_value` guard in `set_value` prevents re-running if the stored
value is identical.  But this guard is not sufficient for:

- **Timestamps** (e.g. `modified_at`): a combinator that writes the current
  time will produce a *different* value each time it runs.  The guard checks the
  *input* field value, not the computed timestamp.  If the input field value
  hasn't changed but `modified_at` is updated, the guard correctly suppresses
  the re-run — but only if the `if value != old_value` check is on the correct
  field.  This needs careful verification.
- **LLM computes** (via `PopulateButton`): not triggered by `set_value` today,
  but if compute integration is ever wired through `_value_updated`, running LLM
  calls twice would be costly and could produce different outputs each time.
- **Any impure compute function**: one that reads external state, increments a
  counter, or writes to a secondary file.

### What the correct fix looks like

The underlying problem is that `<input type="range">` (slider) fires `change`
only on **mouseup**, not during drag.  If the user drags a slider and clicks
Save in a single mouse gesture (without releasing the slider first), the
`change` event may not fire before the Save POST.

Correct fixes, in order of preference:

1. **Fix the slider trigger** — use `hx-trigger="change mouseup"` or a
   `mouseup` listener specifically on range inputs so the per-field POST always
   fires before Save.  Then remove the "apply form values" logic from `/save`
   entirely; `/save` calls only `reviewer.save_flows()`.

2. **Use `hx-sync` to serialise requests** — add
   `hx-sync="closest form:queue last"` to the Save button so HTMX waits for all
   in-flight field-update requests to complete before firing the Save POST.
   Then `/save` does not need to re-apply values.

3. **Separate value-setting from compute-triggering in `/save`** — if `/save`
   must apply form values as a fallback, it should write raw values directly
   into the data store (bypassing `_value_updated`) rather than going through
   `set_value`.  This avoids re-running computes at the cost of slightly more
   complex code.

### Current status

The fix in this commit is a pragmatic stopgap that restores correctness for
the common case.  It should be revisited:

- The per-field `change` event reliability needs investigation and fixing.
- The `/save` route should be reverted to `reviewer.save_flows()` only once the
  change-event path is trustworthy.
- The compute-safety of the current `/save` implementation needs verification
  against the `value != old_value` guard in `set_value`.

See also: `backlog/documentation/2026-07-14_web-interface-event-architecture.md`

## Progress Updates

### 2026-07-14
Bug identified and fixed during interactive debugging session with the web
interface.  All three root causes confirmed.  Fixes applied and 10 regression
tests added.  All 52 tests in `test_web_routes.py` pass.
