---
id: "2026-08-19_cip000E-generic-errors-page"
title: "Generic messages on /errors and listing tooltips (CodeQL #21)"
status: "Completed"
priority: "High"
created: "2026-08-19"
last_updated: "2026-08-19"
category: "infrastructure"
related_cips: ["000E"]
owner: "lawrennd"
dependencies:
- "2026-08-18_cip000E-exception-exposure"
tags:
- backlog
- security
- codeql
- web
- cip000E
---

# Task: Generic messages on /errors and listing tooltips

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

CIP-000E made HTMX handlers and `HTTPException.detail` generic, and left `/errors` detailed as
an operator page. After alerts #13–#20 closed, CodeQL opened
[alert #21](https://github.com/lawrennd/referia/security/code-scanning/21)
(`py/stack-trace-exposure`) on `list_errors` returning that HTML.

Tighten the same CIP policy: the browser never sees exception text. Full `str(exc)` stays in
`referia-server.log` only. This is not a new CIP. Auth and who may reach `/errors` remain the
future hosting CIP already deferred by CIP-000E.

Remaining HTML sinks (targeted, not a full-repo review):

1. `GET /errors` table cells in `list_errors` (`referia/web/routes.py`) interpolating `e["error"]`
2. Directory-listing warning tooltip using `e["error"][:120]`
3. Registry writes that store `str(exc)` for those views (`_read_config_meta` `"_error"`,
   `_get_cached_reviewer` `load_errors`)

## Acceptance Criteria

- [x] `/errors` HTML contains no exception message text (generic cell copy, e.g. "See server log")
- [x] Directory-listing warning icon has no exception text in `title` (generic tooltip is fine)
- [x] Parse and load failures still appear as rows (path/config identity can remain)
- [x] Full exception text is logged with `log.exception` / `log.warning` (existing log path is enough)
- [x] Tests assert a distinctive exception string never appears in `GET /errors` or listing HTML
- [x] Existing `/errors` tests still pass (counts, banner, path listing) after copy changes
- [x] CIP-000E policy table updated: `/errors` is generic in the browser, detail in the log
- [ ] CodeQL alert #21 closes after merge (or next scan)

## Implementation Notes

Reuse `_esc` for remaining user-visible strings (titles, config paths). Do not put `str(exc)`
into HTML even escaped. The in-memory registry may keep a type or timestamp for the table;
it must not be the source of browser-visible exception text.

Do not add authentication in this task.

## Related

- CIP: [CIP-000E](../../cip/cip000E.md)
- Prior task: [2026-08-18_cip000E-exception-exposure](2026-08-18_cip000E-exception-exposure.md)
- Closure: [2026-08-18_cip000E-codeql-closure](2026-08-18_cip000E-codeql-closure.md)
- Code: `referia/web/routes.py` (`list_errors`, `_render_directory_listing`, `_read_config_meta`,
  `_get_cached_reviewer`)
- Tests: `tests/test_web_app.py` (error logging and `/errors` page)
- Alert: https://github.com/lawrennd/referia/security/code-scanning/21

## Progress Updates

### 2026-08-19

Task created as a CIP-000E follow-on after CodeQL #21. Status Proposed pending review.

Accepted and moved to In Progress for implementation.

Implemented: `/errors` and listing tooltips use "See server log."; parse meta stores
`_error: True`; load registry no longer stores `str(exc)`. Tests in `tests/test_web_app.py`.
CodeQL #21 remains until GitHub rescans `main`.
