---
id: "2026-07-14_web-template-expansion-missing"
title: "Web interface hides all conditional sections (visible_if flag columns missing from data)"
status: "Completed"
priority: "High"
created: "2026-07-14"
last_updated: "2026-07-14"
related_cips: []
tags: ["web", "templates", "rendering", "visible_if"]
---

# Task: Web interface hides conditional sections due to missing flag columns in data dict

## Description

When a `_referia.yml` uses the `templates:` section with `visible_if` conditions
on template instantiations (e.g. `visible_if: "abstractPresent"`), all of those
conditional sections were permanently hidden in the web interface — even when the
flag column was `True` in the data.

Initial analysis wrongly attributed this to `_flatten_entries` not handling
template expansion.  Investigation revealed that `Interface.__init__` correctly
expands all templates (both `template:` key form and built-in composite types
like `CriterionComment`) before the web interface processes the data.  The
`visible_if` attributes are applied to all expanded widget dicts.

## Actual root cause

`_current_data()` in `routes.py` built the data dict used by `render_form` by
iterating only over the widget specs and calling `reviewer.get_value(col)` for
each widget field.  Columns used in `visible_if` conditions (e.g.
`"abstractPresent"`, `"forewordPresent"`) that have no associated widget were
absent from this dict.

`render_form` then evaluated e.g. `data.get("abstractPresent")` → `None` →
`bool(None)` → `False` → widget hidden.  Every section with a `visible_if`
condition was therefore hidden regardless of its actual value in the data.

In Jupyter this did not occur because the `review.py` code read visibility
conditions directly from the full pandas DataFrame row.

## Fix

1. Added `WebReviewer.get_row_data()` — returns ALL columns for the current
   record as a plain dict (via `self._data.to_pandas().loc[idx]`), normalising
   `NaN` values to `None`.

2. Updated `_current_data()` in `routes.py` to start from `get_row_data()`
   (providing the full row baseline) and then override with widget-field values
   from `get_value()`.  This ensures any column referenced in `visible_if`
   conditions is available.

## Files changed

- `referia/assess/web_review.py` — `get_row_data()` method added
- `referia/web/routes.py` — `_current_data()` updated to start from `get_row_data()`
- `tests/test_web_reviewer.py` — `TestGetRowData` test class added
- `tests/test_web_routes.py` — `TestCurrentDataIncludesVisibleIfFields` added

## Acceptance Criteria

- [x] `visible_if: "flagColumn"` sections are visible when `flagColumn` is `True`
- [x] `visible_if: "flagColumn"` sections are hidden when `flagColumn` is absent/falsy
- [x] All 158 web interface tests pass
- [x] No regressions in existing behaviour

## Related

- Tenet: template-driven-composition
- Tenet: progressive-augmentation
