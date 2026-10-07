---
id: 000A
title: LLM dependencies stay on supported secure release lines
status: In Progress
priority: High
created: '2026-10-07'
last_updated: '2026-10-07'
related_tenets:
- pragmatic-automation
- progressive-augmentation
stakeholders:
- maintainers
- security
tags:
- llm
- security
- dependencies
---
# REQ-000A: LLM dependencies stay on supported secure release lines

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

When LLM extras are used, their dependency constraints and code must stay on supported, security-patched release lines so known advisories can be closed without abandoning the declarative LLM compute capability.

Compatibility with the current LangChain major line is part of keeping that optional path viable.

**Why this matters**: Optional automation must not leave the project on unsupported, vulnerable dependency lines.

**Who benefits**: Maintainers responding to Dependabot and users of the optional LLM extras.

## Acceptance Criteria

- [ ] Optional LLM dependency constraints target patched supported majors
- [ ] LLM compute entry points remain compatible with the pinned major line
- [ ] Dependabot alerts for the LangChain stack can be closed once migration is verified

## Notes

Extracted from CIP(s): CIP-000D.
Those CIPs document HOW this outcome is achieved; this requirement states the desired outcome only.

## References

- **Related Tenets**: pragmatic-automation, progressive-augmentation
- **Implementing CIPs**: CIP-000D (linked from CIP `related_requirements`, not here)

## Progress Updates

### 2026-10-07
Requirement extracted from existing CIPs during requirements-framework bootstrap.
