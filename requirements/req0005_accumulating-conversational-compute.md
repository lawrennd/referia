---
id: '0005'
title: Compute results can accumulate and carry conversational context
status: Implemented
priority: Medium
created: '2026-10-07'
last_updated: '2026-10-07'
related_tenets:
- user-oriented-convenience
- pragmatic-automation
stakeholders:
- reviewers
- review-authors
tags:
- compute
- llm
- ui
---
# REQ-0005: Compute results can accumulate and carry conversational context

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Compute operations must support appending results to existing field values so prior analyses are not lost, and LLM functions must be able to include prior conversational or history context when configured.

Reviewers should be able to accumulate insight across runs without manual copy-paste into fields.

**Why this matters**: Reviewers iterate: they need history and append behaviour, not only replace-once fields.

**Who benefits**: Reviewers building multi-step LLM analyses and conversation-like assessment notes.

## Acceptance Criteria

- [x] Configured compute operations can append to existing values instead of only replacing them
- [x] LLM functions can incorporate prior history or conversational context when specified
- [x] History use remains bounded enough to avoid routine context overflows in normal use

## Notes

Extracted from CIP(s): CIP-0007, CIP-0008.
Those CIPs document HOW this outcome is achieved; this requirement states the desired outcome only.

## References

- **Related Tenets**: user-oriented-convenience, pragmatic-automation
- **Implementing CIPs**: CIP-0007, CIP-0008 (linked from CIP `related_requirements`, not here)

## Progress Updates

### 2026-10-07
Requirement extracted from existing CIPs during requirements-framework bootstrap.
