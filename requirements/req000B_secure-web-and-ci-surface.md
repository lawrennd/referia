---
id: 000B
title: Web and CI surfaces do not expose path injection or XSS defaults
status: Implemented
priority: High
created: '2026-10-07'
last_updated: '2026-10-07'
related_tenets:
- user-oriented-convenience
stakeholders:
- maintainers
- reviewers
- security
tags:
- security
- web
- ci
---
# REQ-000B: Web and CI surfaces do not expose path injection or XSS defaults

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

The web display layer and related GitHub Actions workflows must avoid path injection, unsafe reflected content, and overly broad workflow permissions. User-facing errors should be generic while details remain in server logs.

**Why this matters**: A convenient web review UI must not become an unsafe file or script surface.

**Who benefits**: Anyone serving review UIs locally or via CI-related workflows.

## Acceptance Criteria

- [x] User-controlled paths cannot escape intended review roots
- [x] User-facing error pages do not leak sensitive internals
- [x] Workflows use least-privilege permissions appropriate to their jobs

## Notes

Extracted from CIP(s): CIP-000E.
Those CIPs document HOW this outcome is achieved; this requirement states the desired outcome only.

## References

- **Related Tenets**: user-oriented-convenience
- **Implementing CIPs**: CIP-000E (linked from CIP `related_requirements`, not here)

## Progress Updates

### 2026-10-07
Requirement extracted from existing CIPs during requirements-framework bootstrap.
