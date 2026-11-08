---
id: "2026-11-08_cip0026-numeric-scoring-example"
title: "CIP-0026 Phase B: examples/numeric_scoring demo"
status: "Ready"
priority: "Medium"
created: "2026-11-08"
last_updated: "2026-11-08"
category: "features"
related_cips: ["0026"]
owner: "lawrennd"
dependencies:
- "2026-11-07_yaml-numeric-compute-primitives"
tags:
- backlog
- examples
- compute
- numeric
---

# Task: Add `examples/numeric_scoring/`

> Backlog task for [CIP-0026](../../cip/cip0026.md) Phase B.

## Description

Create a miniature offline scoring example that exercises YAML `add` /
`multiply` / `gte` (and related) compute once numeric primitives land.
Viewer shows derived fields; Save writes tall scores. No LLM.

## Acceptance Criteria

- [ ] `examples/numeric_scoring/` with README, `_referia.yml`, and `info/`
- [ ] Uses registered referia numeric compute (not embedded Python)
- [ ] Linked from `docs/examples/index.rst` and `docs/usage/compute.rst`
- [ ] Manual smoke: serve, Populate, Save, reload

## Implementation Notes

Depends on `2026-11-07_yaml-numeric-compute-primitives` (sibling branch
`referia-yaml-numeric`). Sketch layout in CIP-0026 Detailed Description.

## Related

- CIP: 0026
- Feature backlog: `2026-11-07_yaml-numeric-compute-primitives`

## Progress Updates

### 2026-11-08

Task created; blocked on numeric primitives merge or same-branch land.
