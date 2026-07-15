---
id: "2026-07-15_web-nan-in-empty-fields"
title: "Empty cells render as 'nan' in web interface text areas and other widgets"
status: "Completed"
priority: "High"
created: "2026-07-15"
last_updated: "2026-07-15"
related_cips: []
---

# Bug: Empty cells render as 'nan' in web interface

## Description

When a data cell is empty (pandas `NaN`), the web interface renders the
string `"nan"` in text areas, dropdowns, and other widgets instead of an
empty value.

## Root cause

The Jupyter interface calls `remove_nan(series.to_dict())` before passing
values to widgets (`review_new.py`, line 256).  NaN is therefore stripped
from the entire row before any widget sees it.

The web interface calls `WebReviewer.get_value(field)` which returns the raw
DataFrame value.  `float('nan')` then passes through `str()` in the HTML
renderer, producing the literal string `"nan"`.

## Affected widgets

- `Textarea` / text inputs — show `"nan"` as content
- Potentially `Dropdown` — may fail to match any option
- Potentially `FloatSlider` / `IntSlider` — may show unexpected value

## Fix

In `WebReviewer.get_value()`, normalise NaN to a sensible empty value before
returning, consistent with how Jupyter handles it via `remove_nan()`:

```python
def get_value(self, field: str):
    val = super().get_value(field)
    if _is_nan(val):
        return ""   # or None — check what each widget type expects
    return val
```

A shared helper `_is_nan(val)` should cover `float`, `numpy.float*`,
`numpy.datetime64`, and `pd.NaT` (mirrors `lynguine.util.misc.is_nan`).

This keeps the fix in referia's own layer (explicit-implicit-separation
tenet) without touching lynguine.

## Future CIP consideration

If both Jupyter and web should benefit from identical normalisation, move the
fix into `lynguine.assess.data.CustomDataFrame.get_value()`.  That requires
a CIP (progressive-augmentation tenet — changes to infrastructure need
design review).

## Acceptance criteria

- Empty spreadsheet cells display as empty strings in text areas (not `"nan"`)
- Saving an empty field does not write the string `"nan"` to the data store
- Jupyter behaviour is unchanged
- Unit test: `WebReviewer.get_value()` returns `""` when the underlying cell
  is `NaN`
