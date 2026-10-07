---
id: '0003'
title: Column mappings arise during explicit flow processing
status: Implemented
priority: High
created: '2026-10-07'
last_updated: '2026-10-07'
related_tenets:
- explicit-implicit-separation
- progressive-augmentation
stakeholders:
- maintainers
- review-authors
tags:
- mapping
- dataflow
- lynguine
---
# REQ-0003: Column mappings arise during explicit flow processing

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Column-to-variable mappings must be established when data flows are processed, not as surprising side effects of object construction. Referia may add review-specific convenience, but that convenience must be handled explicitly in the application layer without fighting lynguine's flow timing.

Users should be able to predict when mappings exist and how interface mappings interact with identity defaults.

**Why this matters**: Implicit construction-time mappings conflict with lynguine's explicit flow model.

**Who benefits**: Review authors configuring interfaces and maintainers integrating with lynguine.

## Acceptance Criteria

- [x] Mappings are created during flow processing rather than solely in construction
- [x] Explicit interface mappings can override defaults without timing conflicts
- [x] Mapping behaviour is predictable and consistent with lynguine's access-assess-address model

## Notes

Extracted from CIP(s): CIP-0005.
Those CIPs document HOW this outcome is achieved; this requirement states the desired outcome only.

## References

- **Related Tenets**: explicit-implicit-separation, progressive-augmentation
- **Implementing CIPs**: CIP-0005 (linked from CIP `related_requirements`, not here)

## Progress Updates

### 2026-10-07
Requirement extracted from existing CIPs during requirements-framework bootstrap.
