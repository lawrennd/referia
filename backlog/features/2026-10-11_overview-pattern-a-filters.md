---
id: "2026-10-11_overview-pattern-a-filters"
title: "Overview Pattern A presentation + general filters bar"
status: "Ready"
priority: "High"
created: "2026-10-11"
last_updated: "2026-10-11"
category: "features"
related_cips: ["0010"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-10-11_root-load-referia-yml"
- "2026-10-11_singleton-navigation-chrome"
tags:
- backlog
- features
- web
- filters
- wide-flatten
- cip0010
---

# Task: Overview Pattern A presentation + filters

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Wire the root/overview experience: tall discovery + tall `complete` scores (Pattern A), Liquid/`flattenKeys` / wide view names, Save on tall store, and a general collapsible `filters:` bar (boolean tristate, date range, categorical; default cleared). Example root `_referia.yml` + short docs. No `mode: catalog`.

## Acceptance Criteria

- [ ] Pattern A: filtered tall set → `flattenKeys` / wide view for Liquid; Save writes tall `complete`
- [ ] `filters:` declared in config; bar under panel-nav; collapsible; default clear
- [ ] Example root `_referia.yml` (wide_flatten + tall yaml/csv scores) documented
- [ ] Tests: overview load, tall Save, filters; assert no catalog mode flag
- [ ] Optional secondary `rows` Liquid path documented or deferred explicitly

## Implementation Notes

- Depends on lynguine Phase 3 wrapping `index` for `index: root` overview configs
- See CIP-0010 implementation status checklist

## Related

- CIP: 0010
- Depends on: `2026-10-11_root-load-referia-yml`, `2026-10-11_singleton-navigation-chrome`

## Progress Updates

### 2026-10-11

Task created (Ready) from Accepted CIP-0010.
