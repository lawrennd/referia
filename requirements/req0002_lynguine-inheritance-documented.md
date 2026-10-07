---
id: '0002'
title: Lynguine inheritance and APIs are discoverable in documentation
status: Implemented
priority: Medium
created: '2026-10-07'
last_updated: '2026-10-07'
related_tenets:
- progressive-augmentation
- user-oriented-convenience
stakeholders:
- contributors
- maintainers
tags:
- documentation
- sphinx
- lynguine
---
# REQ-0002: Lynguine inheritance and APIs are discoverable in documentation

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Documentation must make referia's inheritance from lynguine visible: which objects extend which bases, what is inherited versus overridden, and how the Sphinx API docs reflect that relationship.

A reader should not need to reverse-engineer the class hierarchy to know where review-specific behaviour lives.

**Why this matters**: Users and contributors need to understand what referia inherits versus what it adds.

**Who benefits**: Contributors extending referia and users reading API docs.

## Acceptance Criteria

- [x] Sphinx documentation covers key referia objects and their lynguine parents
- [x] Inheritance and override relationships are stated in docs, not only in code
- [x] Examples clarify application-layer vs infrastructure behaviour where it matters

## Notes

Extracted from CIP(s): CIP-0003, CIP-0004.
Those CIPs document HOW this outcome is achieved; this requirement states the desired outcome only.

## References

- **Related Tenets**: progressive-augmentation, user-oriented-convenience
- **Implementing CIPs**: CIP-0003, CIP-0004 (linked from CIP `related_requirements`, not here)

## Progress Updates

### 2026-10-07
Requirement extracted from existing CIPs during requirements-framework bootstrap.
