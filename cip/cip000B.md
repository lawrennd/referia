---
author: "Neil D. Lawrence"
created: "2026-07-13"
id: "000B"
last_updated: "2026-07-13"
status: "Accepted"
compressed: false
related_requirements: []
related_cips: ["0005", "0006"]
tags:
- cip
- web
- display
- rendering
- fastapi
- htmx
title: "Web Display System — Non-Jupyter Rendering Backend"
---

# CIP-000B: Web Display System — Non-Jupyter Rendering Backend

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [ ] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected
- [ ] Deferred

## Summary

Introduce a standalone web-based rendering backend for referia review
interfaces, so that `_referia.yml`-defined review workflows can be served as
ordinary web pages — locally first, with a clear path to remote hosting — without
requiring a running Jupyter kernel or any notebook infrastructure.

The existing Jupyter rendering path is left completely unchanged. The new web
backend reuses the existing `Interface` (config) and `CustomDataFrame` (data)
layers without modification, adding only a new rendering layer that serves HTML
form elements in place of ipywidgets.

## Motivation

The current display system is tightly coupled to Jupyter:

- Reviewers must have a Jupyter installation running to use the interface.
- Sharing a review interface with a non-technical collaborator means sharing a
  notebook, which requires setup and familiarity with Jupyter.
- Long-term or institutional use may require hosting the interface on a server,
  which Jupyter is poorly suited to (Voilà aside).
- The web browser is already the reviewer's window into the interface — removing
  the Jupyter intermediary would simplify the stack and improve stability.

The motivation is not to abandon Jupyter (which works well for a single
expert reviewer iterating on a complex workflow) but to offer an alternative
rendering target suited to:

- Simpler deployment for non-technical reviewers.
- Local desktop use without Jupyter overhead.
- Future remote/multi-user hosting scenarios.

## Detailed Description

### Architectural context

The current rendering pipeline is:

```
_referia.yml
    ↓ Interface.from_file()          [referia/config/interface.py]
    ↓ CustomDataFrame.from_flow()    [referia/assess/data.py]
    ↓ Reviewer(...)                  [referia/assess/review.py]
    ↓ WidgetCluster tree             [lynguine/assess/display.py]
    ↓ ipywidgets + IPython.display   ← Jupyter-specific
    ↔ bidirectional sync with CustomDataFrame columns
    → save_flows() / documents / URLs via Sys [referia/system.py]
```

The first three steps — `Interface`, `CustomDataFrame`, `Reviewer` — are
already independent of Jupyter in principle. The Jupyter coupling begins at
`WidgetCluster` and `ipywidgets`.

A web backend replaces only the bottom part of the stack:

```
_referia.yml
    ↓ Interface.from_file()          [unchanged]
    ↓ CustomDataFrame.from_flow()    [unchanged]
    ↓ WebReviewer(...)               [new: referia/assess/web_review.py]
    ↓ HTML form elements             [new: referia/web/ templates]
    ↔ bidirectional sync via HTMX HTTP requests
    → save_flows() / documents via Sys [unchanged]
```

### Technology choices

**FastAPI** for the application server:

- Clean async Python, minimal boilerplate.
- Handles local and remote hosting identically.
- Supports WebSocket for eventual real-time updates if needed.
- Active, well-documented, production-tested.

**HTMX** for reactivity:

- Field updates (changing a dropdown, typing in a text area) send small HTTP
  requests and receive HTML fragment responses — no JavaScript framework needed.
- The server stays authoritative over all state; the browser renders HTML.
- Keeps the frontend thin and the architecture easy to reason about.
- Eliminates a JavaScript build toolchain.

**Jinja2** for HTML templating:

- Already available in the Python ecosystem; FastAPI integrates it natively.
- Templates can mirror the `view_to_value` / liquid rendering already in
  `CustomDataFrame`, producing visually consistent output.

**Why not Voilà?**

Voilà converts Jupyter notebooks into standalone web apps but still requires a
Jupyter kernel. It keeps notebooks as the entry point, which means reviewers
still need to know which notebook to open, and deployment still carries Jupyter
infrastructure. It is a quick win for a prototype but not a clean architectural
separation.

**Why not Streamlit or Gradio?**

Both would require re-implementing widget definitions in a framework-specific
API, abandoning the declarative `_referia.yml` approach. The widget spec should
remain the single source of truth for the review interface.

**Why not a React SPA?**

A React frontend would require a JavaScript build chain and would split the
rendering logic between Python and TypeScript. HTMX achieves comparable
interactivity with server-side rendering only, which fits referia's
architecture better.

### Widget type mapping

Each widget type in `_referia.yml` maps to an HTML equivalent:

| `_referia.yml` type | HTML element |
|---|---|
| `Textarea` | `<textarea>` |
| `Text` | `<input type="text">` |
| `IntSlider` | `<input type="range">` with numeric display |
| `Dropdown` | `<select>` |
| `Checkbox` | `<input type="checkbox">` |
| `BoundedIntText` | `<input type="number" min= max=>` |
| `Markdown` (viewer) | Rendered HTML via Python `markdown` library |
| `SaveButton` | `<button hx-post="/save">` |
| `PopulateButton` | `<button hx-post="/populate/{field}">` |
| `IndexSelector` | `<select hx-get="/record/{index}">` |

Composite widgets (`CriterionCommentRaisesMeetsLowers`, etc.) expand to their
constituent HTML elements just as they expand to ipywidget clusters today,
using the same expansion logic in `Interface`.

### Session model

Each review session (one reviewer, one `_referia.yml`) is a FastAPI app
instance. The review state lives server-side in a `WebReviewer` object. The
browser holds no state beyond the current HTML document.

For local single-user use, a single session suffices. For remote multi-user
use (future), sessions would be keyed by user identity or token.

### HTMX interaction pattern

When a reviewer changes a field value:

1. HTMX sends `POST /field/{column_name}` with the new value.
2. `WebReviewer.set_value(column, value)` updates `CustomDataFrame`.
3. Any dependent fields (combinators, visibility rules, compute-on-change) are
   recalculated.
4. The server responds with updated HTML fragments for the affected widgets.
5. HTMX swaps the fragments into the page — no full reload.

Saving:

1. `POST /save` → `save_flows()` → writes output data files.
2. Response: a brief status message rendered in place.

Index navigation:

1. `GET /record/{index}` → re-renders the full review panel for the new record.
2. HTMX replaces the review panel in place.

### Document opening

`Sys.view_urls()` and PDF operations currently use `subprocess` / macOS
`appscript`. For the web backend:

- URLs open via a client-side `<a target="_blank">` link rendered in the
  document panel.
- PDF viewing: serve the PDF at `/document/{path}` and embed it in an `<iframe>`
  or link to it.
- PDF editing (page extraction) and Word generation remain server-side, with a
  download link returned on completion.

### Entry point

A new `referia/web/app.py` creates the FastAPI application:

```python
from referia.web.app import create_app

app = create_app(user_file="_referia.yml", directory=".")
# run with: uvicorn referia.web.app:app
```

A convenience CLI command:

```bash
referia serve --config _referia.yml
```

or, using `poetry run`:

```bash
poetry run referia serve
```

### Relationship to existing code

| Component | Treatment |
|---|---|
| `Interface` | Unchanged — used directly |
| `CustomDataFrame` | Unchanged — used directly |
| `Reviewer` | Unchanged — Jupyter path untouched |
| `WidgetCluster` / ipywidgets | Unchanged — Jupyter path untouched |
| `Sys` | Reused where applicable; document opening adapted |
| `referia/web/` | New package: `app.py`, `routes.py`, `templates/` |
| `referia/assess/web_review.py` | New: `WebReviewer` class |

`WebReviewer` will mirror the public interface of `Reviewer` where feasible
(same `set_value`, `get_value`, `save_flows`, `set_index` semantics) so that
shared logic can eventually be factored into a common base.

## Implementation Plan

1. **Skeleton FastAPI app** (`referia/web/`):
   - `app.py` with `create_app(user_file, directory)` factory
   - Static files and base Jinja2 template
   - `referia serve` CLI entry point via `pyproject.toml` script

2. **`WebReviewer` class** (`referia/assess/web_review.py`):
   - Wraps `Interface` and `CustomDataFrame`
   - `get_widget_specs()` returns normalised list of widget dicts
   - `set_value(column, value)` / `get_value(column)` / `set_index(index)`
   - `save_flows()` / `load_flows()`
   - `affected_widgets(column)` — returns columns to refresh after a change

3. **Widget-to-HTML renderer** (`referia/web/render.py`):
   - `render_widget(spec, data)` → HTML string per widget type
   - `render_viewer(view, data)` → rendered Markdown/Liquid HTML
   - Composite widget expansion (reuse `Interface` expansion logic)

4. **HTMX routes** (`referia/web/routes.py`):
   - `GET /` — full review page for current index
   - `GET /record/{index}` — review panel fragment for given index
   - `POST /field/{column}` — update one field, return affected fragments
   - `POST /save` — save flows, return status
   - `POST /populate/{field}` — run compute function, return updated fragment
   - `GET /document/{path:path}` — serve a PDF or document file

5. **Jinja2 templates** (`referia/web/templates/`):
   - `base.html` — page shell with HTMX script tag
   - `review_panel.html` — index selector + viewer + review widgets
   - `widget_*.html` — per-type widget fragments
   - `status.html` — save/populate feedback fragment

6. **CSS / layout** (`referia/web/static/`):
   - Minimal stylesheet matching the visual logic of the Jupyter CSS in
     `referia/util/jupyter.py`
   - No external UI framework required initially

7. **Dependencies**:
   - Add `fastapi`, `uvicorn`, `jinja2`, `python-multipart` to `pyproject.toml`
   - These are lightweight and do not conflict with existing Jupyter deps

8. **Documentation and CLI**:
   - Update `README.md` with `referia serve` usage
   - Add a simple example notebook-free workflow in `notebooks/` or `examples/`

## Backward Compatibility

The Jupyter rendering path (`referia/display.py`, `Reviewer`,
`referia/util/widgets.py`) is entirely unchanged. Existing notebooks continue
to work without modification. The web backend is additive.

No changes to `_referia.yml` format are required. The same configuration file
drives both rendering targets.

## Testing Strategy

- **Unit tests** for `WebReviewer`: load a minimal `_referia.yml` fixture,
  verify `set_value` / `get_value` round-trips, `save_flows` writes correctly.
- **Unit tests** for `render_widget`: for each widget type, verify the
  returned HTML contains the expected `<input>` / `<textarea>` / `<select>`
  with correct attributes.
- **Integration test** using FastAPI's `TestClient`: load the gift example
  (`notebooks/excel_gift_example/`), request `GET /`, verify the response
  contains expected field names; `POST /field/Score` with a value, verify
  `CustomDataFrame` is updated.
- **Manual smoke test**: `referia serve` from an existing review directory,
  navigate records, edit fields, save.

## Implementation Status

- [ ] Skeleton FastAPI app and CLI entry point
- [ ] `WebReviewer` class with core state management
- [ ] Widget-to-HTML renderer for basic widget types
- [ ] HTMX routes for field update and index navigation
- [ ] Jinja2 templates (base page + review panel)
- [ ] CSS layout
- [ ] Document serving route
- [ ] Composite widget expansion in web renderer
- [ ] Unit tests for `WebReviewer`
- [ ] Unit tests for `render_widget`
- [ ] Integration tests via `TestClient`
- [ ] `pyproject.toml` dependency additions
- [ ] README documentation for `referia serve`

## References

- `referia/assess/review.py` — canonical Jupyter `Reviewer` implementation
- `referia/config/interface.py` — widget spec expansion (reusable for web)
- `referia/util/widgets.py` — ipywidgets wrappers (Jupyter path; kept unchanged)
- `referia/util/jupyter.py` — CSS layout logic to mirror in web stylesheet
- `lynguine/assess/display.py` — `WidgetCluster` / `DisplaySystem` base
- [HTMX documentation](https://htmx.org/docs/) — attribute-driven AJAX
- [FastAPI documentation](https://fastapi.tiangolo.com/) — async Python web framework
- CIP-0005 — referia/lynguine layering and `from_flow` timing
- CIP-0006 — template-driven widget composition (expansion logic reused here)
