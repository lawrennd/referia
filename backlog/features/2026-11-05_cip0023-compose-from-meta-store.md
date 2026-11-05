---
id: "2026-11-05_cip0023-compose-from-meta-store"
title: "CIP-0023: Compose DAG from discovery + frontmatter + pipeline_meta"
status: "Ready"
priority: "High"
created: "2026-11-05"
last_updated: "2026-11-05"
category: "features"
related_cips: ["0023", "0024"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-11-05_cip0023-map-meta-product"
tags:
- backlog
- features
- multiverse
- cip0023
- discovery
---

# Task: Compose DAG from discovery + frontmatter + pipeline_meta

> Linked CIP: 0023 (Phase 2 item 4).

## Description

Teach `compose_pipeline_manifest` (and Compute wrappers) to:

1. Take topology from `discover_pipeline_edges`
2. Take identity (`title`, `permalink`) from stage frontmatter
3. Take interpretation chrome from a **declared** `pipeline_meta`
   store on the consuming interface (not `_data/corpus/pipeline.yml`)

Fall back: if meta store absent, compose topology + identity only
(param table may be empty). Delete formats-study
`_data/corpus/pipeline.yml` once consumers are wired.

## Acceptance Criteria

- [ ] `compose_pipeline_manifest` accepts declared meta rows / path;
      ignores retired corpus `pipeline.yml` overlay
- [ ] Hub and `11_multiverse` declare the meta store; wrappers load via
      CIP-0024 helpers
- [ ] Unit tests: discovery + meta merge; missing meta still draws DAG
- [ ] Formats study: `pipeline.yml` removed; DAG + stage param table
      still work from meta product

## Implementation Notes

- Keep Option A full-manifest load only as legacy fallback when
  discovery finds no stages
- Golden-compare edge set vs previous discovered graph (topology
  unchanged by this task)

## Related

- CIP: 0023, 0024
- Depends on: `2026-11-05_cip0023-map-meta-product`

## Progress Updates

### 2026-11-05

Task created after CIP-0023 update (map chrome as product design).
