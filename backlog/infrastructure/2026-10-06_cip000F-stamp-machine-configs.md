---
id: 2026-10-06_cip000F-stamp-machine-configs
title: 'CIP-000F: Stamp referia_config_version on living machine configs'
status: Completed
priority: High
created: '2026-10-06'
last_updated: '2026-10-06'
category: infrastructure
related_cips:
- 000F
owner: lawrennd
dependencies:
- 2026-10-06_cip000F-migrate-stamp-only
tags:
- backlog
- cip000F
- migrate
- one-shot
---

# Task: Machine-wide stamp pass

## Description

After `--stamp-only` lands, run it (dry-run then `--write`) over living
config roots on this machine so practice with versioning starts immediately:

- `~/Library/CloudStorage/OneDrive-Personal/referia`
- `~/Documents/ref`
- Any other roots agreed at run time

Record counts stamped / skipped / failed. Do not rewrite dialect keys.

## Acceptance Criteria

- [x] Dry-run reviewed before `--write`
- [x] All successful parses under chosen roots either already stamped or
  receive `referia_config_version: 1` or `2`
- [x] No comment-loss / mass reformat of YAML
- [x] Summary counts committed or noted in this task’s progress updates
- [x] v0 / unreadable files listed and left alone

## Implementation Notes

Operational one-shot after the CLI exists. Prefer surgical stamp. Do not
include personal Excel/PDF content in the referia git repo.

## Related

- CIP: 000F

## Progress Updates

### 2026-10-06

Task created on CIP-000F acceptance. Status Proposed until stamp-only CLI
is Ready/Completed.

### 2026-10-06

Stamp-only CLI landed; this operational pass is Ready.

### 2026-10-06 (machine stamp)

Stamped all 314 `_referia.yml` under `/Users/neil` (Caches/Containers/venvs pruned):

- stamped_v1: 226
- stamped_v2: 88
- errors: 0

Roots included OneDrive referia (279), Documents/ref (11), refdemo, Downloads,
lawrennd notebooks/projects, old_lawrennd copies, private, teaching.
Proto `_config.yml` files were not stamped (separate name; migrator skips v0).
