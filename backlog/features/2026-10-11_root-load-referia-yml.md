---
id: "2026-10-11_root-load-referia-yml"
title: "Root GET / loads {root}/_referia.yml when present"
status: "Completed"
priority: "High"
created: "2026-10-11"
last_updated: "2026-10-11"
category: "features"
related_cips: ["0010"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- features
- web
- root
- cip0010
---

# Task: Root GET / loads ordinary _referia.yml

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

CIP-0010: when `{root}/_referia.yml` exists, serve it like any other config review. Otherwise fall back to CIP-000C directory listing.

## Acceptance Criteria

- [x] `GET /` loads `{root}/_referia.yml` when present
- [x] Missing root config → existing CIP-000C listing unchanged
- [x] Intermediate directory overviews can use the same rule where applicable
- [x] Tests cover present vs absent root config

## Implementation Notes

- `referia/web/routes.py` — `index` tries `_root_reviewer("", …)` then falls back to listing; `_reviewer` serves root yml for unprefixed action routes
- Intermediate dirs already used the same load-or-list rule in `root_index` (CIP-000C)
- Bump lynguine to a revision with CIP-000F + CIP-0010 Phase 3 (`a87fb35` on main)

## Related

- CIP: 0010
## Progress Updates

### 2026-10-11

Task created (Ready) from Accepted CIP-0010.

### 2026-10-11 (later)

Completed: root `GET /` loads `{root}/_referia.yml` when present (listing fallback unchanged); unprefixed action routes serve the root config; lynguine lock at `a87fb35`.

### 2026-10-11 (tall-first)

Still complete. Overview presentation no longer requires wide_flatten / wrapping singleton index — see `2026-10-11_inline-list-same-page`.
