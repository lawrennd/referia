---
id: "2026-10-06_cip000F-migrate-rewrite"
title: "CIP-000F: Full dialect rewrite migrate mode"
status: "Proposed"
priority: "Low"
created: "2026-10-06"
last_updated: "2026-10-06"
category: "features"
related_cips: ["000F"]
owner: ""
dependencies:
- "2026-10-06_cip000F-extract-normaliser"
- "2026-10-06_cip000F-migrate-stamp-only"
tags:
- backlog
- cip000F
- migrate
- dialect
---

# Task: Opt-in full key-rewrite migrate

## Description

Extend `referia migrate` (without `--stamp-only`) to apply
`normalise_referia_config` on disk: rewrite v1 keys to v2 and set
`referia_config_version: 2`. Dry-run default; `--write` with sibling
`.migrated.yml` or `--in-place` + `.bak`.

## Acceptance Criteria

- [ ] Dry-run shows keys that would change per file
- [ ] `--write` produces loadable v2 YAML; `Interface` loads before/after
- [ ] Default writes `_referia.migrated.yml`; `--in-place` keeps `.bak`
- [ ] Document that full rewrite may lose comments / reorder keys
- [ ] Does not expand `CriterionComment*` composites on disk
- [ ] Fixture test with synthetic v1 → v2

## Implementation Notes

Separate from stamp-only. Not required for versioning practice. REF layouts
may still fail path jail even after rewrite.

## Related

- CIP: 000F

## Progress Updates

### 2026-10-06

Task created on CIP-000F acceptance.
