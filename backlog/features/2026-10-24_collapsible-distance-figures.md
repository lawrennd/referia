---
id: "2026-10-24_collapsible-distance-figures"
title: "Collapsible Plotly figures on 05_distance"
status: "Completed"
priority: "Medium"
created: "2026-10-24"
last_updated: "2026-10-24"
category: "features"
related_cips: ["0014"]
owner: "lawrennd"
dependencies:
- "2026-10-24_ground-cost-heatmap"
tags:
- backlog
- cip0014
- plotly
- visualisation
- distance
- collapse
---

# Task: Collapsible Plotly figures on 05_distance

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

The 05_distance viewer stacked several Plotly diagrams (share heatmap,
pairwise EMD, pairwise ground cost, radar, MDS). Reviewers need to hide
some and keep others while inspecting. Wrap each figure (caption +
PlotlyFigure) in `type: Section` so it becomes an independent
`<details>` panel. Persist closed as well as open across HTMX record
swaps, and resize Plotly when a panel is opened.

Heading collapse (`collapse.headings`) cannot wrap a following
PlotlyFigure sibling, so this uses the existing viewer `type: Section`
chrome rather than CIP-0014 heading wrapping.

## Acceptance Criteria

- [x] Each 05_distance figure is a collapsible Section (l172, template; draghi viewer and review plots)
- [x] Viewer sections have `data-section-key="viewer/..."` so they do not collide with review keys
- [x] Session storage restores closed panels, not only open ones
- [x] Nested PlotlyFigures keep leaf ids for OOB updates (`iter_spec_leaves`)
- [x] Opening a section resizes Plotly plots inside it

## Implementation Notes

Viewer `type: Section` already defaults to open. Drop duplicate `###`
headings from the caption liquid so the `<summary>` is the only title.
`get_viewer_specs` must `preserve_sections=True` (it previously flattened
viewer Sections, so YAML wrapping had no effect). `has_plotly_viewer`
and `_viewer_highlight_oobs` walk `iter_spec_leaves` so Compute /
highlight still refresh figures nested in sections.

## Related

- CIP: 0014
- Documentation: `cip/cip0014.md`

## Progress Updates

### 2026-10-24

Implemented Section wrapping, viewer keys, persist closed, Plotly
resize on toggle, and tests.
