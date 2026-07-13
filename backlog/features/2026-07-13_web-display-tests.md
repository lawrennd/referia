---
id: "2026-07-13_web-display-tests"
title: "Web display system: unit and integration tests"
status: "Proposed"
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

- [ ] `tests/test_web_reviewer.py` covers:
  - [ ] `WebReviewer` constructs from the gift example fixture
  - [ ] `set_value` / `get_value` round-trip for a text field
  - [ ] `set_index` changes the active record
  - [ ] `save_flows` writes to a temporary output file
  - [ ] `affected_widgets` returns expected columns after a change
- [ ] `tests/test_web_render.py` covers:
  - [ ] `render_widget` for each supported widget type returns HTML with the correct element and HTMX attributes
  - [ ] `render_viewer` renders a `display:` entry using field substitution
  - [ ] `render_viewer` renders a `liquid:` entry
  - [ ] Composite widget expansion produces the correct number of sub-widgets
- [ ] `tests/test_web_routes.py` covers (via `TestClient`):
  - [ ] `GET /` returns 200 with expected field names in HTML
  - [ ] `POST /field/{column}` updates the data and returns updated HTML
  - [ ] `GET /record/{index}` returns the review panel for a different record
  - [ ] `POST /save` returns a success status fragment
- [ ] All tests pass under `poetry run pytest`
- [ ] No existing tests broken

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
