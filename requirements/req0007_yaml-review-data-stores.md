---
id: '0007'
title: Review data can be stored in YAML as well as Excel
status: Implemented
priority: Medium
created: '2026-10-07'
last_updated: '2026-10-07'
related_tenets:
- document-centric-management
- user-oriented-convenience
stakeholders:
- review-authors
- maintainers
tags:
- data-format
- yaml
- excel
---
# REQ-0007: Review data can be stored in YAML as well as Excel

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Review allocation and assessment data stores must support YAML files as an alternative to Excel workbooks, without forcing every legacy Excel workflow to migrate at once.

Where YAML is used, round-tripping of review data should preserve the fields the interface needs.

**Why this matters**: Text-friendly YAML aids review workflows that want diffable, git-friendly assessment data.

**Who benefits**: Review authors choosing storage formats for candidate and assessment tables.

## Acceptance Criteria

- [x] YAML can be used as an allocation or assessment data source in review configs
- [x] Excel-based configs continue to work for workflows that need them
- [x] YAML-backed reviews can load and save the fields required by the interface

## Notes

Extracted from CIP(s): CIP-000A.
Those CIPs document HOW this outcome is achieved; this requirement states the desired outcome only.

## References

- **Related Tenets**: document-centric-management, user-oriented-convenience
- **Implementing CIPs**: CIP-000A (linked from CIP `related_requirements`, not here)

## Progress Updates

### 2026-10-07
Requirement extracted from existing CIPs during requirements-framework bootstrap.
