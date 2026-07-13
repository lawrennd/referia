---
id: "2026-07-13_web-reviewer-class"
title: "Web display system: WebReviewer class"
status: "Completed"
priority: "High"
created: "2026-07-13"
last_updated: "2026-07-13"
category: "features"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: ["2026-07-13_web-display-scaffold"]
tags:
- backlog
- web
- reviewer
- state-management
---

# Task: Web display system: WebReviewer class

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Implement `WebReviewer` in `referia/assess/web_review.py`. This class wraps
`Interface` and `CustomDataFrame` to provide a stateful review session for the
web backend, with the same core semantics as the existing `Reviewer` but
without any ipywidgets dependency.

## Acceptance Criteria

- [x] `WebReviewer(user_file, directory)` constructs successfully from a `_referia.yml`
- [x] `web_reviewer.set_index(index)` switches the active record
- [x] `web_reviewer.get_value(column)` returns the current value for a column
- [x] `web_reviewer.set_value(column, value)` updates `CustomDataFrame` and triggers combinator refresh
- [x] `web_reviewer.save_flows()` persists data to output files
- [x] `web_reviewer.load_flows(reload=True)` reloads data from source
- [x] `web_reviewer.get_widget_specs()` returns the normalised list of widget dicts from `Interface` (viewer + review sections)
- [x] `web_reviewer.affected_widgets(column)` returns the set of column names that need refreshing after `column` changes
- [x] `web_reviewer.index_list()` returns the list of valid record indices
- [x] No ipywidgets import anywhere in `web_review.py`

## Implementation Notes

`WebReviewer` should call `Interface.from_file()` and
`CustomDataFrame.from_flow()` just as `display.Scorer()` does today. The
`value_updated()` logic in `Reviewer` (combinator refresh, timestamps,
compute-on-change) should be replicated or extracted into a shared base.

A minimal starting point:

```python
class WebReviewer:
    def __init__(self, user_file="_referia.yml", directory="."):
        self._interface = Interface.from_file(user_file, directory)
        self._data = CustomDataFrame.from_flow(self._interface)
        self._sys = Sys(self._interface)
        self._index = self._data.index[0]
```

Consider whether a shared base class between `Reviewer` and `WebReviewer` is
appropriate at this stage, or whether that refactor belongs in a follow-on CIP.

## Related

- CIP: 000B
- PRs: 
- Documentation: 

## Progress Updates

### 2026-07-13

Task created following acceptance of CIP-000B.

### 2026-07-13 (completed)

Implemented `referia/assess/web_review.py` with full public API:
`index_list()`, `get_index()`, `set_index()`, `get_value()`, `set_value()`,
`save_flows()`, `load_flows()`, `get_widget_specs()`, `affected_widgets()`.
The `_value_updated()` helper replicates the timestamp and combinator logic
from `Reviewer.value_updated()` without any ipywidgets dependency.
23 unit tests in `tests/test_web_reviewer.py`, all passing.
