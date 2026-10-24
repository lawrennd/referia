---
id: "2026-10-24_consistent-distance-leaf-order"
title: "Leaf-order heatmaps with EMD and cosine ground cost"
status: "Completed"
priority: "Medium"
created: "2026-10-24"
last_updated: "2026-10-24"
category: "features"
related_cips: ["0016"]
owner: "lawrennd"
dependencies:
- "2026-10-21_document-emd-compute"
- "2026-10-21_distance-plotly-views"
tags:
- backlog
- cip0016
- plotly
- seriation
- emd
- clustering
- distance
---

# Task: Consistent-distance leaf order

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Pearson clustering of the share matrix P treats lenses as orthonormal: moving
mass from T0 to T1 costs the same as T0 to T6. That geometry is inconsistent
with the simplex EMD already used for document distance. Leaf-order the
topic×document heatmap (and matching radar) with the same measures:

- columns: topic-mean cosine ground cost (`ground_cost`)
- rows: pairwise EMD under that cost (`emd_matrix`)

Expose this as an explicit option on the clustering function rather than
hard-wiring Pearson. Isolated heatmap calls without those matrices keep
Pearson columns and barycenter rows so existing Draghi tests still pass.

## Acceptance Criteria

- [x] `_leaf_order` accepts `distances=` (square or condensed); that
      geometry wins over Pearson / cosine of the share matrix
- [x] `_seriate_share_matrix` accepts `col_distances` and `row_distances`
- [x] Distance façade passes cosine ground cost and pairwise EMD when those
      matrices are square and have a positive off-diagonal
- [x] Degenerate / missing / wrong-shape distances fall back to Pearson
      columns and barycenter rows
- [x] Isolated `topic_document_heatmap_spec(P)` without distances keeps the
      Pearson + barycenter default
- [x] Viewer captions state adjacent rows mean small transport cost, not
      similar Pearson share profiles
- [x] Unit tests for supplied distances vs fallback (`test_plotly_distance.py`,
      `test_compute_distance.py`)

## Implementation Notes

`_leaf_order` still uses average-linkage plus Bar-Joseph
(`optimal_leaf_ordering`). The change is which distance it clusters, not the
ordering algorithm.

Façade helper `_distance_matrix_for_seriation(M, n)` returns `None` when the
matrix is missing, the wrong shape, or all-zero (POT absent), so the
heatmap does not replace barycenter with a degenerate all-tied order.

YAML captions live in OneDrive `dialogue-analysis/{template,l172-worksheet1,draghi-competitiveness}/05_distance/_referia.yml`. CIP-0016 Plotly
section records the optional kwargs.

## Related

- CIP: 0016
- Compute: `referia/assess/compute/distance.py`
- Figures: `referia/util/plotly_figures.py`
- Prior tasks: `2026-10-21_document-emd-compute`, `2026-10-21_distance-plotly-views`

## Progress Updates

### 2026-10-24

Task created to document work already on the CIP-0016 branch.

`_leaf_order(..., distances=)` and `_seriate_share_matrix(..., row_distances=, col_distances=)` added. Façade wires EMD and ground cost. 53 tests in `test_plotly_distance.py` and `test_compute_distance.py` passed.
