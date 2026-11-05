---
id: "2026-11-05_cip0023-hub-discovered-dag"
title: "CIP-0023: Hub index shows discovered DAG with click → permalink"
status: "Ready"
priority: "Medium"
created: "2026-11-05"
last_updated: "2026-11-05"
category: "features"
related_cips: ["0023"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-11-05_cip0023-compose-from-meta-store"
tags:
- backlog
- features
- multiverse
- cip0023
- hub
---

# Task: Hub index shows discovered DAG with click → permalink

> Linked CIP: 0023 (Phase 2 item 4 — hub map).

## Description

On formats-study `index.md` (`permalink: /`), show the same discovered
pipeline DAG as the primary Access map. Node click navigates to that
stage’s permalink (unlike `11_multiverse`, where click sets
`focus_stage`).

Keep the existing `inline_list` of stages as a secondary table of
contents. Optionally style orphan/seed reads (constants, documents)
as a distinct node class when the figure API allows.

## Acceptance Criteria

- [ ] Hub precomputes `pipeline_dag_figure` (composed manifest)
- [ ] Plotly (or equivalent) click → navigate to node `permalink`
- [ ] Multiverse click behaviour unchanged (`focus_stage`)
- [ ] Hub copy states topology is discovered from declared stores
- [ ] Smoke: `/` renders DAG without LLM keys

## Implementation Notes

- Reuse `pipeline_dag_figure`; add a click-action mode or hub-specific
  binding (CIP-0011 Plotly click actions)
- May land after meta-store compose so cost badges on hover remain
  meaningful; can ship with topology-only if meta not ready

## Related

- CIP: 0023
- Depends on: `2026-11-05_cip0023-compose-from-meta-store` (soft: can
  prototype on discovery-only compose)

## Progress Updates

### 2026-11-05

Task created after CIP-0023 update (map chrome as product design).
