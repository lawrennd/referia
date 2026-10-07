---
id: '0004'
title: Reviewers can run LLM-backed analysis via declarative compute
status: Implemented
priority: High
created: '2026-10-07'
last_updated: '2026-10-07'
related_tenets:
- pragmatic-automation
- user-oriented-convenience
stakeholders:
- reviewers
- review-authors
tags:
- llm
- compute
- automation
---
# REQ-0004: Reviewers can run LLM-backed analysis via declarative compute

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Review workflows must be able to invoke LLM-backed summarisation, extraction, and related text operations through the existing declarative compute specification, as an optional capability that degrades gracefully when LLM tooling is unavailable.

Humans remain in control: automated outputs are reviewable and editable.

**Why this matters**: Automation should help humans review when it adds value, without forcing code changes for each prompt.

**Who benefits**: Review authors configuring `_referia.yml` and reviewers using PopulateButton-style workflows.

## Acceptance Criteria

- [x] LLM compute functions are available through declarative config where configured
- [x] LLM capability is optional; reviews work without it installed or enabled
- [x] Automated outputs can be inspected and overridden by the human reviewer

## Notes

Extracted from CIP(s): CIP-0006.
Those CIPs document HOW this outcome is achieved; this requirement states the desired outcome only.

## References

- **Related Tenets**: pragmatic-automation, user-oriented-convenience
- **Implementing CIPs**: CIP-0006 (linked from CIP `related_requirements`, not here)

## Progress Updates

### 2026-10-07
Requirement extracted from existing CIPs during requirements-framework bootstrap.
