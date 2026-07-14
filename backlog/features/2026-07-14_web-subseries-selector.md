---
id: "2026-07-14_web-subseries-selector"
title: "Web interface sub-selector navigation for subseries data"
status: "Proposed"
priority: "Medium"
created: "2026-07-14"
last_updated: "2026-07-14"
related_cips: []
tags: ["web", "subseries", "navigation", "ux"]
---

# Task: Web Interface Sub-Selector Navigation for Subseries Data

## Description

Some `_referia.yml` configurations use a `series` with a `selector:` field, meaning
each primary index entry (e.g. a person's name) has multiple sub-rows — one per
selector value (e.g. one row per letter written, one per achievement logged).

In the Jupyter interface, a second dropdown appears automatically to let the reviewer
navigate between sub-entries for the current primary index. The web interface has no
equivalent: it silently picks one sub-entry and provides no way to switch between them.

### Current behaviour

- A person with three letters has three sub-rows in the series data.
- The web interface renders the form for the first sub-row only.
- There is no UI to navigate to the second or third letter.
- Saving a new sub-row (e.g. drafting a new letter) is also impossible from the web UI.

### Desired behaviour

- When the active `_referia.yml` has a subseries (i.e. `get_selector()` returns a
  non-None value), a second `<select>` element appears in `.panel-nav`, to the right
  of the primary index selector.
- The sub-selector lists all available sub-entries for the current primary index, using
  the selector field values (e.g. `Number`, `Achievement Number`) as option labels.
- Changing the sub-selector updates the form to show that sub-entry's data (HTMX
  reload of `#review-panel`).
- The sub-selector persists across primary index changes: after switching to a new
  person, it snaps to the first sub-entry for that person (or the most recent, matching
  existing Jupyter behaviour).

## Acceptance Criteria

- [ ] A sub-selector `<select>` appears in the nav bar when and only when
      `reviewer.get_selector()` returns a non-None value.
- [ ] The sub-selector is populated with all subindex values for the current primary
      index (from `reviewer.get_subindices()`).
- [ ] Selecting a value in the sub-selector calls `reviewer.set_subindex(value)` and
      triggers a panel reload via HTMX.
- [ ] After a primary index change, the sub-selector resets to the first sub-entry for
      the new primary index.
- [ ] The currently active sub-entry is pre-selected in the dropdown on every render.
- [ ] If there is only one sub-entry, the dropdown may be hidden or shown as
      read-only (UX decision at implementation time).

## Implementation Notes

### Backend changes

1. **`WebReviewer`** — expose two new methods:
   - `get_subindex_list() -> list` — returns sorted list of subindex values for the
     current primary index (wraps `get_subseries()[selector]`).
   - `has_subseries() -> bool` — returns `True` when `get_selector()` is not None and
     the current index has >0 sub-entries.

2. **`/navigate` route** (or extend existing `/record/{index}`) — accept an optional
   `subindex` query parameter. Call `reviewer.set_subindex(subindex)` before rendering.

3. **`routes.py` `_current_data()`** — already fixed to call `get_row_data()`, which
   now correctly selects the active sub-row. No additional change needed here.

### Frontend changes

4. **`review_panel.html`** — add a second `<select id="subindex-select">` inside
   `.panel-nav`, rendered only when `has_subseries` is True. Populate with
   `subindex_list`, marking the active subindex as `selected`.
   Use `hx-get="/record/{index}"` with `hx-vals` carrying the chosen subindex.

5. **`style.css`** — style the sub-selector consistently with `.index-select`.

### Edge cases

- Primary index with a single sub-entry: still render the sub-selector (aids awareness)
  but consider styling it differently (greyed out / read-only).
- Navigation to a primary index whose sub-entry list is empty (new record): auto-create
  a sub-row using `add_series_row()` logic, matching existing Jupyter behaviour.
- Subseries `selector` field values may be integers (e.g. `Number = 3`): render as
  strings in the dropdown but parse back to the correct type before calling
  `set_subindex`.

## Related

- Bug: `2026-07-14_web-selector-keyerror.md` (the immediate `KeyError` that was fixed
  by using `.iloc[0]` in `get_row_data()` and `check_or_set_subseries()`).
- Config examples that need this: `people/letters/_referia.yml`,
  `people/achievements/_referia.yml`.

## Progress Updates

### 2026-07-14
Task created. The blocking `KeyError` in `get_row_data()` has been fixed so the page
loads; sub-selector navigation remains unimplemented.
