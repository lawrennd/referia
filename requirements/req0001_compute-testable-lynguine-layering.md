---
id: '0001'
title: Compute framework is testable and cleanly layered on lynguine
status: Implemented
priority: Medium
created: '2026-10-07'
last_updated: '2026-10-07'
related_tenets:
- progressive-augmentation
- explicit-implicit-separation
stakeholders:
- maintainers
- contributors
tags:
- compute
- testing
- lynguine
---
# REQ-0001: Compute framework is testable and cleanly layered on lynguine

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Referia's Compute class must extend lynguine without carrying dead or commented-out code that already lives upstream, and its methods must be reliably testable with clear parameter contracts relative to the parent implementation.

Reviewers and maintainers should be able to trust that Compute behaviour is intentional application-layer augmentation, not a fork of infrastructure.

**Why this matters**: Progressive augmentation and explicit layering keep referia's Compute extension removable and understandable.

**Who benefits**: Package maintainers and contributors verifying Compute behaviour against lynguine.

## Acceptance Criteria

- [x] Compute tests exercise referia methods against expected lynguine parent contracts
- [x] Referia Compute does not retain commented-out or duplicated code that was migrated to lynguine
- [x] Inheritance boundaries between referia and lynguine Compute are clear in tests and structure

## Notes

Extracted from CIP(s): CIP-0001, CIP-0002.
Those CIPs document HOW this outcome is achieved; this requirement states the desired outcome only.

## References

- **Related Tenets**: progressive-augmentation, explicit-implicit-separation
- **Implementing CIPs**: CIP-0001, CIP-0002 (linked from CIP `related_requirements`, not here)

## Progress Updates

### 2026-10-07
Requirement extracted from existing CIPs during requirements-framework bootstrap.
