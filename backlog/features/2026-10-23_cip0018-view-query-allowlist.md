---
id: "2026-10-23_cip0018-view-query-allowlist"
title: "Allowlisted compose / inherit_viewer / inherit_review query params"
status: "Completed"
priority: "High"
created: "2026-10-23"
last_updated: "2026-10-23"
category: "features"
related_cips: ["0018"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- features
- web
- query
- security
- cip0018
---

# Task: Parse allowlisted inherit view options

> Linked CIP: 0018. Display-only; CIP-000E untrusted request input.

## Description

Parse a small allowlist of view options on the review URL. Optional YAML `inherit.compose` is an author default. Precedence: query → YAML → `link`.

v1 allowlist (case-insensitive; other keys ignored):

| Param | Values | Default | Effect |
|-------|--------|---------|--------|
| `compose` | `link`, `stacked` | `link` | Inherit presentation |
| `inherit_viewer` | `0`, `1` | `1` when stacked, ignored otherwise | Include ancestor `viewer:` |
| `inherit_review` | `0`, `1` | `1` when stacked, ignored otherwise | Include ancestor `review:` |

Unknown or invalid values: ignore, log server-side, fall back. Do not 500 and do not echo the raw value into HTML.

**Forbid even if present:** `writable`, directories, filenames, paths, widget types, Liquid, field names, compute. `inherit.writable` stays a config fact.

Boolean params accept only `0`/`1` (and `true`/`false` if a second spelling is added).

## Acceptance Criteria

- [ ] No params and no YAML `compose` → `link` (today's view)
- [ ] `?compose=stacked` selects stacked; `?compose=link` forces link even if YAML says stacked
- [ ] `compose=not-a-mode` treated as default `link`, not an error page
- [ ] `?writable=true` and path-like extras are ignored; they do not change Interface loading or Save stores
- [ ] Invalid booleans fall back to the stacked defaults (`inherit_viewer`/`inherit_review` = 1)
- [ ] YAML `inherit.compose: stacked` is the author default when the query omits `compose`

## Implementation Notes

- Centralise parsing in one helper used by review routes (do not scatter enum checks).
- Do not introduce a `layout=` override here; that belongs with CIP-0010.

## Related

- CIP: 0018
- CIP: 000E (untrusted query)

## Progress Updates

### 2026-10-23

Task created (Ready) when CIP-0018 was Accepted.

### 2026-10-23 (implementation)

Implemented on branch `cip0018-implement-stacked-inherit`. Tests in `tests/test_inherit_view.py` pass (32). Status Completed.
