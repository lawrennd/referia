---
id: "2026-10-23_cip0018-preserve-view-params"
title: "Preserve compose query params on HTMX fetches; page control to toggle stacked"
status: "Completed"
priority: "High"
created: "2026-10-23"
last_updated: "2026-10-23"
category: "features"
related_cips: ["0018"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-10-23_cip0018-view-query-allowlist"
tags:
- backlog
- features
- web
- htmx
- cip0018
---

# Task: Preserve view params and expose a stacked toggle

> Linked CIP: 0018.

## Description

HTMX index/field fetches and trailing-slash redirects must **preserve** the allowlisted view params the same way they already preserve `?index=`. Page chrome exposes ordinary links or a compact control (for example “Show inherited”) that sets or clears `compose=stacked`, so reviewers need not type the names.

Changing index while stacked must not snap back to `link`.

## Acceptance Criteria

- [ ] Trailing-slash redirects keep `compose`, `inherit_viewer`, `inherit_review` (and `index`)
- [ ] HTMX panel fetches after index change still include the allowlisted params
- [ ] A visible control sets `compose=stacked` and clears it back to today's view
- [ ] The stacked view does not reset when the reviewer moves to another record
- [ ] The control does not offer `writable` or path options

## Implementation Notes

- Follow the existing `?index=` preservation in `referia/web/routes.py` redirects.
- Bookmarkable: the control should be an href (or equivalent) that updates the query string, not only client state.

## Related

- CIP: 0018
- Depends on: `2026-10-23_cip0018-view-query-allowlist`

## Progress Updates

### 2026-10-23

Task created (Ready) when CIP-0018 was Accepted.

### 2026-10-23 (implementation)

Implemented on branch `cip0018-implement-stacked-inherit`. Tests in `tests/test_inherit_view.py` pass (32). Status Completed.
