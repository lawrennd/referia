---
id: "2026-10-11_root-load-referia-yml"
title: "Root GET / loads {root}/_referia.yml when present"
status: "Ready"
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

- [ ] `GET /` loads `{root}/_referia.yml` when present
- [ ] Missing root config → existing CIP-000C listing unchanged
- [ ] Intermediate directory overviews can use the same rule where applicable
- [ ] Tests cover present vs absent root config

## Implementation Notes

- `referia/web/routes.py` — `index`, listing helpers
- Bump lynguine to a revision with CIP-000F + CIP-0010 (including Phase 3 before relying on wrapping `index: root`)

## Related

- CIP: 0010
- Depends on: lynguine CIP-0010 Phase 3 for named singleton overview configs

## Progress Updates

### 2026-10-11

Task created (Ready) from Accepted CIP-0010.
