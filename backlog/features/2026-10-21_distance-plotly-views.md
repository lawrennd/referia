---
id: "2026-10-21_distance-plotly-views"
title: "Plotly MDS scatter, topic×document heatmap, and EMD heatmap for distance Address"
status: "Proposed"
priority: "Medium"
created: "2026-10-21"
last_updated: "2026-10-21"
category: "features"
related_cips: ["0016"]
owner: "lawrennd"
dependencies:
- "2026-10-21_document-emd-compute"
tags:
- backlog
- cip0016
- cip0011
- plotly
- visualisation
- distance
---

# Task: Distance Plotly figure builders

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Add Plotly builders in `referia.util.plotly_figures` (CIP-0011 contract) for
document MDS scatter (click → `selected_doc`), topic×document heatmap of P,
pairwise EMD heatmap, and axis-correlate bars. Specs are written to output
columns; the viewer does not keep widget-only figure state.

Do not put Plotly knowledge in `mppca.py` (CIP-0012). These builders stay in
referia when CIP-0016 maths later moves to vongole.

## Acceptance Criteria

- [ ] `doc_mds_plotly_spec` — MDS coords, colour by group, `customdata.doc`
- [ ] Click binding `on.click_point` sets `selected_doc` on output
- [ ] `topic_document_heatmap_spec` — heatmap of P with grain `topic_labels`
- [ ] `emd_heatmap_spec` — pairwise EMD
- [ ] `axis_correlate_bars_spec` — Pearson of MDS axes vs topic shares
- [ ] Spec tests: keys and customdata aligned with `doc_ids_kept`
- [ ] Draft `04_distance` viewer binds these fields

## Implementation Notes

See [CIP-0016](../../cip/cip0016.md) Plotly section. Matplotlib from
`multilogue.viz` is not the referia payload.

Proposed only: do not implement until CIP-0016 is Accepted.

## Related

- CIP: 0016
- Viewer: CIP-0011
- Draft: OneDrive `applications/2026-10-21_dialogue-analysis/04_distance/`

## Progress Updates

### 2026-10-21

Task created as Proposed from CIP-0016.
