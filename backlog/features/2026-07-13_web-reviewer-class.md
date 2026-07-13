---
id: "2026-07-13_web-reviewer-class"
title: "Web display system: WebReviewer class"
status: "Proposed"
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

- [ ] `WebReviewer(user_file, directory)` constructs successfully from a `_referia.yml`
- [ ] `web_reviewer.set_index(index)` switches the active record
- [ ] `web_reviewer.get_value(column)` returns the current value for a column
- [ ] `web_reviewer.set_value(column, value)` updates `CustomDataFrame` and triggers combinator refresh
- [ ] `web_reviewer.save_flows()` persists data to output files
- [ ] `web_reviewer.load_flows(reload=True)` reloads data from source
- [ ] `web_reviewer.get_widget_specs()` returns the normalised list of widget dicts from `Interface` (viewer + review sections)
- [ ] `web_reviewer.affected_widgets(column)` returns the set of column names that need refreshing after `column` changes
- [ ] `web_reviewer.index_list()` returns the list of valid record indices
- [ ] No ipywidgets import anywhere in `web_review.py`

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
