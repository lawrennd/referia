---
id: "2026-08-23_pandas-concat-empty-na-futurewarning"
title: "pd.concat of blank series rows raises FutureWarning for empty or all-NA columns"
status: "Completed"
priority: "Medium"
created: "2026-08-23"
last_updated: "2026-08-23"
category: "bugs"
related_cips: []
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- pandas
- series
---

# Bug: pandas concat FutureWarning when adding a series row

## Description

Adding a series row (blank review entry, new subseries line) emitted:

```
FutureWarning: The behavior of DataFrame concatenation with empty or
all-NA entries is deprecated. In a future version, this will no longer
exclude empty or all-NA columns when determining the result dtypes.
To retain the old behavior, exclude the relevant entries before the
concat operation.
```

The traceback pointed at `referia/assess/data.py` in `add_series_row()`:

```python
self._d[typ] = pd.concat([series_df, new_row])
```

The warning appeared twice when two series types (`writeseries` and
`series`) were updated. It fired when the existing series frame already
had numeric columns with values and the new row was all-NA (the usual
"add a blank row" path). `_append_row()` used the same concat pattern.

## Root cause

`add_series_row()` built the new row by assigning `None` to every column.
Those columns are all-NA. pandas 2.1+ currently ignores empty or all-NA
columns when deciding the result dtypes of `pd.concat`; that exclusion
is deprecated. Observed on pandas 2.3.1 (Anaconda) and pandas 3.0.3
(poetry).

## Fix

Added `concat_preserving_dtypes()` in `referia/assess/data.py`. It drops
all-NA columns from the incoming row before concat so the existing
frame's dtypes are used — the documented way to keep the old behaviour.
`add_series_row()` and `_append_row()` both use the helper.

Tests in `referia/tests/test_assess_data.py` treat `FutureWarning` as an
error for blank-row and partial-value appends.

## Follow-up

lynguine `CustomDataFrame.add_row()` and `set_value()` still concatenate
all-NA rows the same way. Promote the helper there if that warning
appears in infrastructure paths.

The warning seen in notebooks came from the *installed* package
(`site-packages/referia`), not the source tree. Reinstall or use an
editable install after this change.

## Acceptance Criteria

- [x] `add_series_row()` does not emit the empty/all-NA concat FutureWarning
- [x] `_append_row()` uses the same helper
- [x] Blank series rows still append and preserve existing numeric dtypes
- [x] Values passed to `add_series_row()` land on the new last row
- [x] Tests cover the helper and `add_series_row()` without FutureWarning

## Implementation Notes

Do not use `reindex()` to append a duplicate series index — series
frames allow repeated parent indices, and `reindex` would copy the
existing row rather than add a blank one.

## Related

- CIP: none (local pandas compatibility fix)
- Files: `referia/assess/data.py`, `referia/tests/test_assess_data.py`

## Progress Updates

### 2026-08-23

Warning reproduced: existing float column plus an all-NA new row
triggers it; dropping all-NA columns from the new row before concat
does not. Helper and tests added; `test_assess_data.py` 44 passed.
