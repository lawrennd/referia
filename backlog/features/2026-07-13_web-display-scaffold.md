---
id: "2026-07-13_web-display-scaffold"
title: "Web display system: project scaffold and CLI entry point"
status: "Proposed"
priority: "High"
created: "2026-07-13"
last_updated: "2026-07-13"
category: "features"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- web
- fastapi
- scaffold
---

# Task: Web display system: project scaffold and CLI entry point

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Create the `referia/web/` package and wire up a minimal FastAPI application
that can be started from the command line. This is the foundation on which all
other web display tasks depend.

## Acceptance Criteria

- [ ] `referia/web/__init__.py` and `referia/web/app.py` exist
- [ ] `create_app(user_file, directory)` factory returns a FastAPI instance
- [ ] `GET /` returns a 200 response with a basic HTML page (even if mostly empty)
- [ ] `referia serve` CLI command starts the app with uvicorn (`poetry run referia serve`)
- [ ] `fastapi`, `uvicorn[standard]`, `jinja2`, `python-multipart` added to `pyproject.toml` dependencies
- [ ] Static files directory (`referia/web/static/`) served at `/static`
- [ ] Templates directory (`referia/web/templates/`) configured for Jinja2

## Implementation Notes

`pyproject.toml` scripts section should add:

```toml
[tool.poetry.scripts]
referia = "referia.cli:main"
```

`referia/cli.py` (or `referia/__main__.py`) dispatches to `referia serve`:

```python
# referia/web/app.py
def create_app(user_file="_referia.yml", directory=".") -> FastAPI:
    app = FastAPI()
    # configure templates, static files, include routers
    return app
```

The `serve` command should accept `--config`, `--directory`, `--host`, `--port`
options with sensible defaults (`localhost:8000`).

## Related

- CIP: 000B
- PRs: 
- Documentation: 

## Progress Updates

### 2026-07-13

Task created following acceptance of CIP-000B.
