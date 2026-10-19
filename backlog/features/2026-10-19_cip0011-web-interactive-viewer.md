---
id: "2026-10-19_cip0011-web-interactive-viewer"
title: "CIP-0011: Web PlotlyFigure viewer + field/highlight sync"
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
- web
- plotly
---

# Task: Web interactive viewer + bindings

## Description

Render `PlotlyFigure` / `StaticImage` under `viewer:` on the web panel. Wire
`plotly_click` to existing `/field/{column}` routes. Refresh review widgets when
viewer writes fields; restyle figures when `highlight.from_field` changes.

## Acceptance Criteria

- [x] `render_viewer_html` dispatches typed entries before Liquid `view_to_value`
- [x] Plotly.js loads when a figure entry is present
- [x] Click bindings POST to the same field routes review uses
- [x] Viewer-originated writes OOB-refresh review widgets for those fields
- [x] Review field changes can update figure highlight
- [x] Liquid-only configs unchanged

## Implementation Notes

No new layout. Use CDN Plotly.js (optional Python plotly not required for web).
Form flag `source=viewer` (or equivalent) so the written column itself can OOB-refresh.

## Related

- CIP: 0011

## Progress Updates

### 2026-10-19

Implemented web PlotlyFigure/StaticImage render, Plotly.js click → `/field` with
`source=viewer`, and highlight OOB on field change.
