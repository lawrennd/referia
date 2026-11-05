---
id: "2026-11-05_cip0023-map-meta-product"
title: "CIP-0023: Map referia writes declared pipeline_meta product"
status: "Ready"
priority: "High"
created: "2026-11-05"
last_updated: "2026-11-05"
category: "features"
related_cips: ["0023", "0024"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- features
- multiverse
- cip0023
- discovery
---

# Task: Map referia writes declared pipeline_meta product

> Linked CIP: 0023 (Phase 2 item 4 — map chrome as declared product).

## Description

Own interpretation chrome (`cost_class`, `multiverse_eligible`,
`paper_axis`, picker labels) on a map referia — hub `/`, a thin
`00_map`, or extended `11_multiverse` — whose **output** is a declared
store (e.g. `pipeline_meta.yml` / Class B `pipeline_meta:`).

Do not put those fields on upstream stage `parameters.yml`. Do not
keep them in a magical `_data/corpus/pipeline.yml`.

Migrate today’s overlay content (interpretation rows only) into that
product; seed or Populate once so hub and multiverse can declare the
store as input.

## Acceptance Criteria

- [ ] Schema for per-stage interpretation chrome documented in CIP-0023
      / self-describing YAML
- [ ] A formats-study referia writes the store via normal `output:` /
      Class B declaration
- [ ] Content covers at least the Phase 1 paper-axis knobs currently in
      `pipeline.yml` (definitions / weightings / exclusions / thresholds /
      rounds) plus existing cost-class annotations worth preserving
- [ ] No title/permalink/parameters_path duplication in the product
      (identity stays on stage frontmatter)

## Implementation Notes

- Prefer extending hub or `11_multiverse` over a new permalink unless
  both consumers need a neutral producer
- Class B key if not joined by `from_flow`; mirror CIP-0024 sidecar
  pattern
- Compute may ship a small helper that validates / normalises the meta
  rows for `compose_pipeline_manifest`

## Related

- CIP: 0023, 0024
- Depends on: Option B discovery already on the Option B branch

## Progress Updates

### 2026-11-05

Task created after CIP-0023 update (map chrome as product design).
