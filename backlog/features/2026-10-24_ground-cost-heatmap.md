---
id: "2026-10-24_ground-cost-heatmap"
title: "Pairwise ground-cost heatmap for lens–lens distances"
status: "Completed"
priority: "Medium"
created: "2026-10-24"
last_updated: "2026-10-24"
category: "features"
related_cips: ["0016"]
owner: "lawrennd"
dependencies:
- "2026-10-24_consistent-distance-leaf-order"
tags:
- backlog
- cip0016
- plotly
- visualisation
- distance
- ground-cost
---

# Task: Pairwise ground-cost heatmap

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

`cosine_ground_cost` is already computed and used as column distances for
the share heatmap, but there was no Plotly figure of the k×k lens–lens
matrix itself. Add `ground_cost_heatmap_spec`: Bar-Joseph leaf order of
that same matrix, so the lowest-distance lenses sit next to each other
and the blue cells concentrate on the diagonal. This is the
corresponding figure to pairwise EMD.

## Acceptance Criteria

- [x] `ground_cost_heatmap_spec` Bar-Joseph-orders the cosine ground-cost matrix
- [x] Façade writes the spec as an output column
- [x] `05_distance` viewer shows it after pairwise EMD (template, l172; draghi review)
- [x] Caption states that lowest-distance lenses are clustered
- [x] Unit tests: sibling lenses adjacent; packed length includes the spec

## Implementation Notes

Reuse `_square_distance_heatmap_spec` with `emd_heatmap_spec`. Append
the spec as the last façade return value so existing packed indices stay
valid. Do not change Pearson/barycenter defaults on isolated heatmap
calls without distances.

## Related

- CIP: 0016
- Prior: [2026-10-24_consistent-distance-leaf-order](./2026-10-24_consistent-distance-leaf-order.md)

## Progress Updates

### 2026-10-24

Task created and completed with the builder, façade wiring, YAML figures,
and tests.
