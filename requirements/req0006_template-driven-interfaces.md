---
id: '0006'
title: Review interfaces support reusable composable patterns
status: Implemented
priority: High
created: '2026-10-07'
last_updated: '2026-10-07'
related_tenets:
- template-driven-composition
- user-oriented-convenience
stakeholders:
- review-authors
- reviewers
tags:
- templates
- configuration
- interface
---
# REQ-0006: Review interfaces support reusable composable patterns

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Interface configuration must allow defining a review pattern once and instantiating it many times with different parameters, including nested composition of simpler patterns into richer interfaces.

Supporting metadata such as columns for expanded fields should follow from the declared structure rather than manual repetition.

**Why this matters**: Define once, instantiate many: repeated review structure should not require copy-paste YAML.

**Who benefits**: Review authors building multi-chapter or multi-criterion interfaces.

## Acceptance Criteria

- [x] Parameterized templates can expand into repeated interface sections
- [x] Templates can nest or compose without invalid circular structure
- [x] Expanded fields produce the supporting columns needed for assessment data

## Notes

Extracted from CIP(s): CIP-0009.
Those CIPs document HOW this outcome is achieved; this requirement states the desired outcome only.

## References

- **Related Tenets**: template-driven-composition, user-oriented-convenience
- **Implementing CIPs**: CIP-0009 (linked from CIP `related_requirements`, not here)

## Progress Updates

### 2026-10-07
Requirement extracted from existing CIPs during requirements-framework bootstrap.
