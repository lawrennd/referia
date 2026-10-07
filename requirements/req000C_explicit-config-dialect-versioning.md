---
id: 000C
title: Config dialect and version are explicit and migratable
status: Validated
priority: Medium
created: '2026-10-07'
last_updated: '2026-10-07'
related_tenets:
- explicit-implicit-separation
- user-oriented-convenience
stakeholders:
- review-authors
- maintainers
tags:
- yaml
- config
- migration
---
# REQ-000C: Config dialect and version are explicit and migratable

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

`_referia.yml` dialect must be detectable and versionable. Convenience keys may still be accepted, but conversion into lynguine form should be an explicit, named process with optional stamping and migration rather than only silent rewrite on load.

**Why this matters**: Silent convenience rewrites hide which dialect a file uses and complicate evolution.

**Who benefits**: Review authors maintaining `_referia.yml` files across referia versions.

## Acceptance Criteria

- [x] Configs can declare a referia config version
- [x] Dialect detection and normalisation are available as explicit tooling
- [x] Authors can stamp or rewrite keys without relying solely on silent load-time conversion

## Notes

Extracted from CIP(s): CIP-000F.
Those CIPs document HOW this outcome is achieved; this requirement states the desired outcome only.

## References

- **Related Tenets**: explicit-implicit-separation, user-oriented-convenience
- **Implementing CIPs**: CIP-000F (linked from CIP `related_requirements`, not here)

## Progress Updates

### 2026-10-07
Requirement extracted from existing CIPs during requirements-framework bootstrap.
