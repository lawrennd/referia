---
id: "2026-07-14_web-selector-keyerror"
title: "KeyError when navigating configs with subseries selector"
status: "Completed"
priority: "High"
created: "2026-07-14"
last_updated: "2026-07-14"
related_cips: []
tags: ["web", "subseries", "pandas", "keyerror"]
---

# Bug: KeyError When Navigating Configs with Subseries Selector

## Description

Any `_referia.yml` that defines a `series` with a `selector:` field (e.g.
`people/letters`, `people/achievements`) raised `KeyError` at two different points:

1. **On startup / primary index change** — `check_or_set_subseries()` in
   `referia/assess/data.py` called `subindices[selector][0]` using label-based
   indexing on a Series whose index is the primary key (person name strings).
   Integer label `0` is not present, so `KeyError: 0` was raised.

2. **On any page render** — `get_row_data()` in `referia/assess/web_review.py`
   called `df.loc[idx]` which, for a person with multiple sub-rows, returns a
   **DataFrame** (not a Series). The subsequent `for col in row.index` then
   iterated over *row index values* (person names), and `row[col]` attempted to
   look up a column whose name was the person's name — raising e.g.
   `KeyError: 'Saidu_Isah'`.

## Root Causes

- `data.py` used `series[0]` (label access) instead of `series.iloc[0]`
  (positional access).
- `web_review.py` `get_row_data()` did not handle the case where `df.loc[idx]`
  returns a `pd.DataFrame` (subseries scenario).

## Fixes Applied

### `referia/assess/data.py` — line 724

```python
# Before
self.set_subindex(subindices[selector][0])

# After
self.set_subindex(subindices[selector].iloc[0])
```

### `referia/assess/web_review.py` — `get_row_data()`

Added a `pd.DataFrame` check after `df.loc[idx]`. When multiple sub-rows exist,
the method now resolves the correct sub-row by matching `get_subindex()` against the
`get_selector()` column, falling back to `.iloc[0]` if no match is found.

## Verification

```
Loaded 214 people
  wa_Maina_Ciira: 111 columns, selector row OK
  Saidu_Isah: 111 columns, selector row OK
  Kazlauskaite_Ieva: 111 columns, selector row OK
All OK
```

## Related

- Feature: `2026-07-14_web-subseries-selector.md` — full sub-selector navigation UI
  still to be implemented.

## Progress Updates

### 2026-07-14
Bug identified and both fixes applied. Server now loads and renders the `letters`
config without error.
