---
id: 0009
title: One server can host multiple review configs under a root
status: Ready
priority: High
created: '2026-10-07'
last_updated: '2026-10-07'
related_tenets:
- user-oriented-convenience
- document-centric-management
stakeholders:
- reviewers
- review-authors
tags:
- web
- routing
- multi-config
---
# REQ-0009: One server can host multiple review configs under a root

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

A single web server process must be able to discover and serve multiple `_referia.yml` configs under a configurable filesystem root, addressing each config by a stable URL path derived from its location.

Reviewers should navigate among related configs without starting a separate server for each file.

**Why this matters**: One process per `_referia.yml` does not scale for ecosystems of related reviews.

**Who benefits**: Users managing many thesis, grant, or application review configs under one tree.

## Acceptance Criteria

- [ ] Configs under a chosen root are addressable on one server via path-based URLs
- [ ] Landing or listing behaviour helps users find available configs
- [ ] Index or subindex selection can be expressed in a way that survives navigation between configs

## Notes

Extracted from CIP(s): CIP-000C.
Those CIPs document HOW this outcome is achieved; this requirement states the desired outcome only.

## References

- **Related Tenets**: user-oriented-convenience, document-centric-management
- **Implementing CIPs**: CIP-000C (linked from CIP `related_requirements`, not here)

## Progress Updates

### 2026-10-07
Requirement extracted from existing CIPs during requirements-framework bootstrap.
