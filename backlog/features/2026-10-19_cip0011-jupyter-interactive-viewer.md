---
id: "2026-10-19_cip0011-jupyter-interactive-viewer"
title: "CIP-0011: Jupyter PlotlyFigure viewer + bindings"
status: "Completed"
priority: "High"
created: "2026-10-19"
last_updated: "2026-10-19"
category: "features"
related_cips: ["0011"]
owner: "lawrennd"
dependencies:
- "2026-10-19_cip0011-viewer-dialect"
tags:
- backlog
- cip0011
- viewer
- jupyter
- plotly
---

# Task: Jupyter interactive viewer + bindings

## Description

Extend `_create_viewer` to type-dispatch: Liquid/Markdown unchanged;
`PlotlyFigure` uses FigureWidget when plotly is available; wire clicks to
`set_value` and observe highlight fields for restyle.

## Acceptance Criteria

- [x] `_create_viewer` leaves Liquid/Markdown path unchanged
- [x] PlotlyFigure click → `set_value` per binding (same persist path as review)
- [x] Highlight field change restyles the figure
- [x] Missing plotly degrades gracefully (message / static fallback)
- [x] StaticImage renders as HTML image

## Implementation Notes

Optional import of plotly; do not hard-require it for all referia installs in v1
if web CDN path covers the primary target — document Jupyter optional dep.

## Related

- CIP: 0011

## Progress Updates

### 2026-10-19

Added `PlotlyFigureViewer` / `StaticImageViewer` and typed dispatch in `_create_viewer`.
