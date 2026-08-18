---
id: "2026-08-18_cip000E-exception-exposure"
title: "Stop returning exception text to the browser (CodeQL #13–#20)"
status: "Completed"
priority: "High"
created: "2026-08-18"
last_updated: "2026-08-18"
category: "infrastructure"
related_cips: ["000E"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- security
- codeql
- web
- cip000E
---

# Task: Stop returning exception text to the browser

## Description

CodeQL `py/stack-trace-exposure` alerts **#13–#20** flag HTMX handlers in `referia/web/routes.py`
that interpolate `str(exc)` into HTML or `HTTPException.detail`. HTML-escaping (`_esc`) does not
fix information disclosure.

CIP-000E policy: reviewers see a short generic message; full exceptions go to `log.exception`.
The `/errors` page stays detailed (operator-facing).

Affected handlers (single-config and root-mode duplicates): field update, save, reload, populate,
and `_get_cached_reviewer` / `_resolve_config_path` HTTPException details.

## Acceptance Criteria

- [x] Shared helpers such as `_user_error_html` and `_log_route_error` exist and are used by both
      single-config and root-mode routes
- [x] HTMX error responses contain no exception message text
- [x] `HTTPException.detail` strings are generic (no `{exc}` interpolation)
- [x] Tests assert failing save/reload/populate returns generic HTML (mock the reviewer)
- [x] Existing web route tests still pass
- [ ] CodeQL alerts #13–#20 close after merge (or next scan)

## Implementation Notes

Keep `_esc` for remaining user-visible strings (titles, YAML metadata). Do not strip detail from
`/errors`. Treat this as an invariant for any future authenticated hosting.

## Related

- CIP: [CIP-000E](../../cip/cip000E.md)
- Code: `referia/web/routes.py`
- Tests: `tests/test_web_routes.py`

## Progress Updates

### 2026-08-18

Task created when CIP-000E was Accepted.

Implemented: `_user_error_html` / `_log_route_error` on field, save, reload, and populate
handlers (single-config and root). `_resolve_config_path` and `_get_cached_reviewer` return
generic HTTP details. `/errors` still shows full exception text. Tests in `tests/test_web_routes.py`
assert `"disk full"` and `"no such column"` never reach the browser.
