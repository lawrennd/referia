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

**Yes, for the immediate problem.**  The three issues above are real and the
fixes are targeted.

**Possible alternative approaches and their trade-offs:**

| Approach | Trade-off |
|---|---|
| Keep per-field `hx-trigger="change"` updates as the *only* path to in-memory state, rely on them having fired before Save | Fragile: browsers do not always fire `change` for sliders before a button click; requires careful ordering of HTMX requests |
| Optimistic UI: read the stored value from the DOM on Save via JavaScript | Requires more JavaScript; harder to test; increases coupling between front-end state and server |
| Use WebSocket / SSE for real-time sync | Significantly more complex; unnecessary for the batch-review use case |
| Make `/save` re-read from the output file after writing to confirm | Useful for audit but does not solve the root cause |

The chosen approach (include all form values in the Save POST and apply them
server-side before persisting) is the simplest correct solution: it makes the
Save button a complete, idempotent snapshot of reviewer state.

**Potential risks:**

- If a field is in the review spec but absent from the form (e.g. a hidden
  widget), the route silently skips it — by design, consistent with how HTML
  forms work.
- The coercion function handles only the widget types currently used.  New
  widget types should extend `_coerce_form_value` and add tests.

## Progress Updates

### 2026-07-14
Bug identified and fixed during interactive debugging session with the web
interface.  All three root causes confirmed.  Fixes applied and 10 regression
tests added.  All 52 tests in `test_web_routes.py` pass.
