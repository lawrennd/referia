---
id: "2026-07-15_cip000C-path-router"
title: "Add catch-all path router for config-based routing"
status: "Ready"
priority: "High"
created: "2026-07-15"
last_updated: "2026-07-15"
related_cips: ["000C"]
---

# Task: Add catch-all path router for config-based routing

## Description

Add a FastAPI catch-all route that maps URL paths to `_referia.yml` files
under the root directory.  The route handles all existing review actions
(record display, field update, save, populate, etc.) scoped under the config
path prefix.

## Acceptance Criteria

- `GET /{config_path:path}` resolves to `{root}/{config_path}/_referia.yml`
  by default.
- If the final path component ends in `.yml` it is treated as an explicit
  config filename (e.g. `_referia_draft.yml`); otherwise `_referia.yml` is
  appended.
- Path traversal outside the root is rejected with HTTP 400.
- If no `_referia.yml` (or named file) exists at the resolved path, HTTP 404
  is returned.
- Sub-routes for field update (`/field/{col}`), save, populate, etc. are
  scoped under the config prefix so they operate on the correct reviewer.

## Implementation Notes

- The existing single-config routes (registered at `/field/…`, `/save`, etc.)
  must continue to work unchanged when `root` is absent.
- In root mode, sub-routes could be implemented as query parameters or as
  `action` parameters on the config path route, e.g.
  `POST /people/letters/?action=save`.
- Alternatively, mount a sub-application per config (FastAPI `include_router`
  with a prefix).

## Related

- CIP: 000C
- Task: 2026-07-15_cip000C-create-app-root-refactor
