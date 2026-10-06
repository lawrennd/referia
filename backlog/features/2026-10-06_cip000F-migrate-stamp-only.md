---
id: "2026-10-06_cip000F-migrate-stamp-only"
title: "CIP-000F: referia migrate --stamp-only (surgical version insert)"
status: "Ready"
priority: "High"
created: "2026-10-06"
last_updated: "2026-10-06"
category: "features"
related_cips: ["000F"]
owner: ""
dependencies:
- "2026-10-06_cip000F-detect-dialect"
tags:
- backlog
- cip000F
- cli
- migrate
- versioning
---

# Task: Stamp-only migrate command

## Description

Add `referia migrate --root PATH --stamp-only` that inserts
`referia_config_version: N` (inferred 1 or 2) without changing any other
keys. Dry-run by default; `--write` performs a surgical insert that preserves
comments and key order.

## Acceptance Criteria

- [ ] Dry-run lists files that would be stamped and the inferred version
- [ ] `--write` inserts version only; all other content unchanged
- [ ] Skips files that already declare `referia_config_version`
- [ ] Skips / reports v0 proto files without writing
- [ ] Prefer ruamel.yaml or equivalent surgical edit (not full PyYAML dump)
- [ ] Unit/integration tests prove comments survive a stamp

## Implementation Notes

This is phase 2 of CIP-000F rollout. Must be safe to run over ~270 OneDrive
configs. Full dialect rewrite is a separate task.

## Related

- CIP: 000F

## Progress Updates

### 2026-10-06

Task created on CIP-000F acceptance.
