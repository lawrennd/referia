---
id: "2026-10-06_web-index-query-string-type"
title: "Web record navigation fails when the index is numeric"
status: "Completed"
priority: "High"
created: "2026-10-06"
last_updated: "2026-10-07"
category: "bugs"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- web
- index
- htmx
---

# Task: Coerce HTMX index query strings onto typed index labels

> Backlog tasks are DOING the work defined in CIPs (HOW).
> Linked CIP: 000B (web display). This is a bug in the current `/record`
> selector, not the CIP-000C positional-`index=` design.

## Description

Clicking a record in the web index `<select>` issues `GET /record?index=2`.
FastAPI types that query parameter as `str`. `WebReviewer.set_index` passes
it straight to lynguine, which requires `index in self.index` with pandas
identity. If the allocation index is integer (for example `Project number`
with values 1–13), `"2" in Index([1, 2, …])` is false and the route raises
`KeyError: Index "2" not found in data` (HTTP 500). HTMX does not swap the
panel.

String labels (`Kazlauskaite_Ieva`) work because the query string already
matches. Jupyter widgets pass Python values, so the same `_referia.yml` is
fine there. The configuration is not wrong.

Seen 2026-10-06 on
`applications/2026-10-06_ai-cam_ai-for-teaching/preliminary` with
`GET /record?index=2` → 500.

## Acceptance Criteria

- [x] `WebReviewer.set_index("2")` selects the row whose index label is
      integer `2` when that label exists.
- [x] String labels still work unchanged (`set_index("bob")`).
- [x] Ambiguous matches are not treated as positional offsets. `index=2`
      must mean the **label** `2` (or `"2"`), not `index_list()[2]`.
- [x] `GET /record?index=2` and the root-server equivalent return 200 and
      swap the panel when label `2` exists.
- [x] A missing label returns 404 (or a panel error), not an uncaught 500.
- [x] Unit tests cover integer, string, and missing labels.

## Implementation Notes

Put resolution in `WebReviewer.set_index` (or a helper it calls) so both
`get_record` routes share it:

1. If `index in self._data.index`, use it.
2. Else find the unique `idx` in `index_list()` with `str(idx) == str(index)`
   and pass that typed value to lynguine.
3. Else raise `KeyError` (routes catch and return 404).

Do **not** implement CIP-000C positional integers here
(`index=3` → fourth row). That would make a `Project number` dropdown of
`2` jump to the third row (usually project 3). If CIP-000C later wants
positional URLs, use a different parameter (`pos=`) or a documented
convention that does not collide with numeric labels.

Do not change lynguine `set_index` to accept `"2"` for `2`; HTTP strings
are an application-layer concern (explicit/implicit separation).

## Related

- CIP: 000B
- CIP: 000C (shareable `?index=` URLs; integer-as-positional conflicts with
  this bug — call that out when 000C is implemented)
- Task: `2026-07-15_cip000C-index-query-param.md`
- Not the same as `2026-07-14_web-selector-keyerror.md` (subseries `iloc`)

## Progress Updates

### 2026-10-06

Bug confirmed from `referia serve` logs while reviewing ai@cam teaching
proposals. Config uses integer `Project number` as index. Backlog created;
not yet implemented.

### 2026-10-07

Implemented: `WebReviewer._resolve_index_label` / `set_index` coerce
query-string labels; routes map `KeyError` to HTTP 404. Unit tests in
`test_web_reviewer.py` and `test_web_routes.py`.
