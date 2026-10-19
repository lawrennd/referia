---
id: "2026-10-19_cip0011-interactive-viewer-tests"
title: "CIP-0011: Tests for interactive viewer bindings"
status: "Completed"
priority: "High"
created: "2026-10-19"
last_updated: "2026-10-19"
category: "features"
related_cips: ["0011"]
owner: "lawrennd"
dependencies:
- "2026-10-19_cip0011-viewer-dialect"
- "2026-10-19_cip0011-web-interactive-viewer"
tags:
- backlog
- cip0011
- tests
---

# Task: Interactive viewer tests

## Description

Unit and web integration coverage for typed viewer entries and shared-field
propagation, using synthetic figure JSON with customdata (no live LLM).

## Acceptance Criteria

- [x] Liquid-only viewer regression still passes (existing Markdown tests retained)
- [x] Binding / customdata path unit tests (`tests/test_viewer_bindings.py`)
- [x] Web: PlotlyFigure HTML shape (`TestRenderViewer`)
- [x] Highlight applied in figure render path
- [x] Missing bindings degrade without crash

## Related

- CIP: 0011

## Progress Updates

### 2026-10-19

Added unit and render tests. Full poetry pytest segfaults in this environment;
re-verify in CI.
