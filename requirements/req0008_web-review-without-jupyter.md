---
id: 0008
title: Review interfaces are usable as web pages without Jupyter
status: In Progress
priority: High
created: '2026-10-07'
last_updated: '2026-10-07'
related_tenets:
- user-oriented-convenience
- document-centric-management
stakeholders:
- reviewers
- collaborators
- review-authors
tags:
- web
- display
- jupyter
---
# REQ-0008: Review interfaces are usable as web pages without Jupyter

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

`_referia.yml`-defined review workflows must be renderable as ordinary web pages for local (and eventually remote) use without requiring a running Jupyter kernel, while leaving the existing Jupyter path intact for expert reviewers who prefer notebooks.

Documents and assessment forms remain part of the same review surface.

**Why this matters**: Not every collaborator can or should run a Jupyter kernel to participate in a review.

**Who benefits**: Reviewers and collaborators who prefer an ordinary browser UI.

## Acceptance Criteria

- [ ] A review config can be served as a web UI without Jupyter
- [ ] The Jupyter review path continues to work for users who prefer it
- [ ] Core review actions (navigate, edit fields, persist) work in the web UI for supported configs

## Notes

Extracted from CIP(s): CIP-000B.
Those CIPs document HOW this outcome is achieved; this requirement states the desired outcome only.

## References

- **Related Tenets**: user-oriented-convenience, document-centric-management
- **Implementing CIPs**: CIP-000B (linked from CIP `related_requirements`, not here)

## Progress Updates

### 2026-10-07
Requirement extracted from existing CIPs during requirements-framework bootstrap.
