---
id: "2026-10-09_web-path-escape-load-error-hint"
title: "Web 503/load errors should distinguish PathEscape without leaking paths"
status: "Completed"
priority: "Medium"
created: "2026-10-09"
last_updated: "2026-10-09"
category: "bugs"
related_cips: ["000E", "000A"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- bug
- web
- path-jail
- PathEscapeError
- CIP-000E
---

# Task: Distinguish PathEscape load failures in the browser safely

> Backlog tasks are DOING the work defined in CIPs (HOW).
> Linked CIP: 000E (generic errors / no exception disclosure), 000A (path jail).

## Description

Opening configs such as `people/letters/` under root-server mode fails with
`PathEscapeError` when inherited data lives outside the serve root (e.g.
`$HOME/mlatcl/...`). The server log shows the real cause, but the browser only
sees a generic `503` / `"Could not load config"`.

Operators need a clearer signal that the failure is **path jail**, without
violating CIP-000E: do not put `str(exc)`, escaped absolute paths, or the
allowed-roots list into HTTP responses or the `/errors` HTML.

## Acceptance Criteria

- [x] When load fails with `PathEscapeError`, the 503 detail uses a **fixed**
      catalog sentence naming path / serve-root confinement (not `str(exc)`).
- [x] `/errors` load table shows the same fixed hint for `PathEscapeError` rows
      (config path + type + time remain; no exception payload).
- [x] Other load failures stay generic; unique markers in `str(exc)` never appear
      in 503 body, `/errors`, or the in-memory registry.
- [x] Full exception (with paths) remains in the server log via `log.exception`.
- [x] Tests cover PathEscape hint present + marker path absent.

## Implementation Notes

- Helper e.g. `_load_failure_detail(exc)` in `referia/web/routes.py` keyed by
  exception type name / `isinstance`.
- Suggested fixed text:
  `"Could not load config: a configured data path is outside the allowed serve roots. See server log and /errors."`
- Out of scope: `--allowed-root` CLI to widen the jail for external data homes.

## Related

- CIP: 000E, 000A
- Trigger: `GET /people/letters/` → PathEscape on `$HOME/mlatcl/mlatcl.github.io/_people/`
- Code: `referia/web/routes.py` (`_get_cached_reviewer`, `/errors`)

## Progress Updates

### 2026-10-09

Task created after letters 503 diagnosis; implement fixed catalog hints next.

### 2026-10-09 (implemented)

`_load_failure_detail` / `_load_failure_hint_for_type` in `routes.py`; 503 and
`/errors` use fixed PathEscape wording. Tests in `test_web_app.py`.
