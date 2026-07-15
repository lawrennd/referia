---
id: "2026-07-15_cip000C-create-app-root-refactor"
title: "Refactor create_app() to accept optional root directory"
status: "Ready"
priority: "High"
created: "2026-07-15"
last_updated: "2026-07-15"
related_cips: ["000C"]
---

# Task: Refactor create_app() to accept optional root directory

## Description

Currently `referia/web/app.py`'s `create_app()` factory function accepts
`user_file` (path to a specific `_referia.yml`) and `directory` (its containing
folder).  When a `root` directory is supplied instead, the server should not
pre-load a single reviewer at startup; instead it defers config loading to the
first request for each path.

## Acceptance Criteria

- `create_app()` gains an optional `root: str | None = None` parameter.
- When `root` is provided, `app.state.root` is set and `app.state.reviewer`
  is `None` (the catch-all router handles loading).
- When `root` is absent the existing single-config behaviour is unchanged.
- Existing tests continue to pass.

## Implementation Notes

- Keep both code paths (single-config and root-based) working simultaneously.
- `app.state.reviewer_cache: dict[str, WebReviewer]` should be initialised as
  `{}` when `root` is provided.
- The `_startup` event handler should skip pre-loading when `root` is set.

## Related

- CIP: 000C
