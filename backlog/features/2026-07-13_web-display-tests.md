---
id: "2026-07-13_web-display-tests"
title: "Web display system: unit and integration tests"
status: "Completed"
priority: "Medium"
created: "2026-07-13"
last_updated: "2026-07-13"
category: "features"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: ["2026-07-13_web-routes-and-templates", "2026-07-13_web-document-serving"]
tags:
- backlog
- web
- testing
- pytest
---

# Task: Web display system: unit and integration tests

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Write the test suite for the web display system: unit tests for
`WebReviewer` and `render_widget`, and integration tests via FastAPI's
`TestClient` that exercise the full HTTP interaction loop.

## Acceptance Criteria

- [x] `tests/test_web_reviewer.py` covers:
  - [x] `WebReviewer` constructs (mock-based), index list, `set_value` / `get_value`, `set_index`, `save_flows`, `affected_widgets`
- [x] `tests/test_web_render.py` covers:
  - [x] `render_widget` for each supported widget type returns HTML with correct element and HTMX attributes
  - [x] `render_viewer` renders Markdown and HTML content
  - [x] `render_form` produces form wrapper
- [x] `tests/test_web_routes.py` covers (via `TestClient`, 38 tests):
  - [x] `GET /` returns 200 with field ids, HTMX attrs, index selector, status bar, HTMX script
  - [x] `POST /field/{column}` updates data, returns status + OOB widget swaps, handles errors and checkbox coercion
  - [x] `GET /record?index=<value>` switches record, returns panel fragment
  - [x] `GET /indices` returns select element with all options
  - [x] `POST /save` calls `save_flows`, returns confirmation, handles errors
  - [x] `POST /reload` calls `load_flows`, returns refreshed panel
  - [x] `POST /populate/{field}` returns 200 with widget
  - [x] `GET /health` returns status JSON
- [x] All 38 new tests pass under `poetry run pytest`
- [x] No existing tests broken (pre-existing template failures unrelated)

## Implementation Notes

Use `pytest` fixtures to set up a minimal `_referia.yml` (the gift example
from `notebooks/excel_gift_example/` is the natural candidate) in a temporary
directory.

FastAPI `TestClient` usage:

```python
from fastapi.testclient import TestClient
from referia.web.app import create_app

def test_get_root(tmp_referia_dir):
    app = create_app(user_file="_referia.yml", directory=tmp_referia_dir)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Score" in response.text
```

Keep test fixtures lightweight — a small CSV/YAML input with 2–3 records and
a minimal `_referia.yml` is sufficient.

## Related

- CIP: 000B
- PRs: 
- Documentation: 

## Progress Updates

### 2026-07-13

Task created following acceptance of CIP-000B.

### 2026-07-13 (implementation)

Created `tests/test_web_routes.py` with 38 integration tests covering all six
routes via FastAPI `TestClient`.  `WebReviewer` is mocked at the module level
so no real data files are needed.

Also fixed two bugs in `referia/web/render.py` found by the tests:
- `_render_int_slider` / `_render_float_slider` now read `min`/`max`/`step`
  from the top-level spec dict (falling back to `args`) and handle
  empty-string values gracefully instead of crashing with `ValueError`.
