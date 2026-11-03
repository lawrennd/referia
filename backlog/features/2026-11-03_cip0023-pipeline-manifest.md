---
id: "2026-11-03_cip0023-pipeline-manifest"
title: "CIP-0023: Pipeline manifest schema + formats study instance"
status: "Completed"
priority: "High"
created: "2026-11-03"
last_updated: "2026-11-03"
category: "features"
related_cips: ["0023"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- features
- multiverse
- cip0023
---

# Task: Pipeline manifest schema + formats study instance

> Linked CIP: 0023.

## Description

Define the Option A pipeline manifest (nodes, edges, per-knob cost class /
multiverse eligibility) and ship an instance for `dods-ai-dialogue` as
`_data/corpus/pipeline.yml`. Add referia helpers to load and validate it.

## Acceptance Criteria

- [ ] Documented schema for `nodes`, `edges`, and knob `cost_class` /
      `multiverse_eligible`
- [ ] Formats study `pipeline.yml` covers 01→11 plus Part B aggregate
- [ ] `load_pipeline_manifest` rejects cycles / unknown cost classes
- [ ] Unit tests for parse + validation

## Implementation Notes

- Prefer study-local YAML; discovery from input/output blocks is Phase 2
- Cost classes: `aggregate` | `refit` | `llm` | `display`

## Related

- CIP: 0023

## Progress Updates

### 2026-11-03

Task created; implementation started with CIP acceptance.
