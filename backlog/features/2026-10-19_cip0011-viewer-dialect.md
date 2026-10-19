---
id: "2026-10-19_cip0011-viewer-dialect"
title: "CIP-0011: Typed viewer entry dialect and binding helpers"
status: "Completed"
priority: "High"
created: "2026-10-19"
last_updated: "2026-10-19"
category: "features"
related_cips: ["0011"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- cip0011
- viewer
- bindings
---

# Task: Typed viewer entry dialect and binding helpers

## Description

Recognise interactive viewer entry types (`PlotlyFigure`, `StaticImage`) and parse
`on:` / `highlight:` bindings. Keep omitted-type Liquid/Markdown behaviour unchanged.
Provide helpers to resolve `from: customdata.*` paths from click payloads.

## Acceptance Criteria

- [x] Entries without `type:` / without `on:` remain one-way Liquid/Markdown
- [x] Helpers recognise `PlotlyFigure` and `StaticImage`
- [x] `on.click_point` → list of `set_field` / `from` actions
- [x] `highlight.from_field` / `mode` parsed without requiring `role:` annotations
- [x] Unit tests for parse + customdata path resolution

## Implementation Notes

Keep convention explicit in referia (placement + bindings). Do not push a field-role
type system into lynguine.

## Related

- CIP: 0011
- REQ: 000F

## Progress Updates

### 2026-10-19

Task created on Accept; implemented `referia/assess/viewer_bindings.py` and unit tests.
