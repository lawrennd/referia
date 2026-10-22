---
author: "Neil D. Lawrence"
created: "2026-10-22"
id: "001A"
last_updated: "2026-10-22"
status: "In Progress"
compressed: false
related_requirements: ["0010"]
related_cips: ["0015", "0016", "0019"]
tags:
- cip
- vq
- grain
- codebook
- plotly
- assess
- parameters
title: "VQ codebook before lens Assess, with a Brownian projection walk"
---

# CIP-001A: VQ codebook before lens Assess, with a Brownian projection walk

> **Note**: CIPs describe HOW to achieve requirements (WHAT).
> Use `related_requirements` to link to the requirements this CIP implements.

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [x] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented
- [ ] Deferred - Postponed

## Summary

Insert a **vector quantisation (VQ)** stage between packed phrase embeddings and subject grain. K-means builds a large codebook: each **cluster** is a tight cell of nearby phrases. `03_grain` then finds **lenses** — broader thematic readings — on those codewords, not on the original points. Phrase-to-lens membership is \(QR\). Document histograms in `04_distance` still count phrases.

The VQ viewer is a **Brownian walk of 2-D projections** through the leading-variance subspace, with Play / Pause, a speed tied to captured variance, and each cell drawn as its centre plus 1-SD extent.

Addresses [REQ-0010](../requirements/req0010_dialogue-pipeline-in-referia.md). Uses CIP-0019 `fit_kmeans`. Does not change CIP-0016's histogram/EMD maths beyond composing \(Q\).

## Motivation

Phrase embeddings sit in \(d=3072\). Running MPPCA or a small-\(k\) partition directly on \(n \approx 10^3\) phrases mixes two jobs: collapsing near-duplicates, and reading themes. VQ does the first. Grain does the second on \(m \ll n\) codewords.

A static PCA scatter of 64 cells in 3072-d is one plane. A slow random walk of planes shows whether a cell is compact in many views or only in the PCA snapshot. Brownian motion on the Stiefel manifold of 2-frames is the right noise: isotropic in the tangent space, no preferred orbit.

## Detailed Description

### Two grains

| Word | Object | Typical size (Draghi) |
|---|---|---|
| Phrase | embedded extraction | \(n \approx 1028\), \(d=3072\) |
| **Cluster** | VQ codeword (k-means cell) | \(m \approx 64\)–\(128\) |
| **Lens** | 03 grain topic (MPPCA / k-means / agglomerative) | \(L\) small, interactive |

\(Q\) is \(n \times m\) one-hot (phrase \(\to\) cluster). \(R\) is \(m \times L\) (cluster \(\to\) lens). Phrase-level lens membership is \(QR\). `document_soft_topic_distributions` consumes the expanded rows plus `doc_ids`.

### Served config

`02_vq/` sorts between `02_embed` and `03_grain`. It is a one-row packed Assess (same grain as 03), not a tall phrase table.

- **input** `../info/records.parquet` (phrases, embeddings, doc_ids)
- **output** `../info/codebook.parquet` (centroids as `embeddings`, exemplar strings as `phrases`, `vq_mass`, `cluster_ids`, `vq_spec`)
- **parameters** `n_vq`, walk knobs (`vq_walk_speed`, `vq_walk_frames`, `vq_walk_subspace`, `vq_walk_linger`)

`03_grain` **input** becomes the codebook. `cluster_ids` is copied onto `scores.yml` (identity) so 04 can expand without a third store. Skip-if-\(R\) only when \(R\) rows match the codebook \(m\).

### Lens weights (03)

`lens_weight`: `uniform` (default) or `mass`.

- **uniform** — each codeword is one geometric point. The lens is about neighbourhoods.
- **mass** — k-means `sample_weight` and MPPCA row weights equal cell size. Large cells pull the lens. Agglomerative has no sample weights: error and name both knobs.

04 always recovers document mass via \(QR\), even when 03 used uniform. The 03 widget and the stage notebook both explain that split.

### Brownian projection walk

Do **not** send 3072-d vectors to the browser. PCA to `vq_walk_subspace` (default 8) — that is the variance the codebook actually has — then walk a 2-frame \(U \in \mathrm{St}(2,q)\):

1. Start on PC1–PC2.
2. Tangent Gaussian increment, scale \(\sigma =\) `vq_walk_speed`, optionally \(\sigma / \sqrt{v}\) when `vq_walk_linger` is on, where \(v\) is codebook variance in the current plane (linger in high-variance views).
3. QR to return to the Stiefel manifold; flip column signs for continuity.
4. Project phrases (subsampled), centroids, and per-cluster 1-SD ellipses (empirical 2-D covariance of members). Reuse `_ellipse_polyline`.

Store as Plotly `{data, layout, frames}` with **Play** / **Pause** `updatemenus` and a frame slider. `Plotly.react` in `base.html` currently passes only `data` and `layout`; it must `addFrames` or the buttons are dead.

Knobs live on the parameters store. Regenerating the walk is a Fit / dedicated Populate, not a hidden side effect of Save.

### Terminology

Say **VQ** and **cluster** for codebook cells; **lens** in 03 copy. Catalogue fields stay `topic_*` (CIP-0019). Do not call VQ cells topics.

## Implementation Plan

1. `subject_vq_fit` + codebook pack fields; `expand_vq_responsibilities` for 04.
2. `vq_projection_walk_plotly_spec`; Plotly frames in `reactPlot`.
3. `lens_weight` through `fit_kmeans` / `mppca_fit`; agglomerative rejects mass.
4. Application YAML: `02_vq`, retarget 03 input, primers in viewer **and** `assessment.ipynb`.

## Backward Compatibility

Default `lens_weight: uniform`. Phrase-level 03 scores whose \(R\) rows \(\neq m\) do not skip; they refit. 04 without `cluster_ids` keeps the CIP-0016 path when \(R\) already matches phrase \(n\).

## Testing Strategy

- VQ: `cluster_ids` length \(n\), \(m\) centroids, masses sum to \(n\).
- Walk spec: `frames` length, Play and Pause buttons, ellipse trace uses `None` separators, centroids present.
- Linger: high-variance plane steps are smaller than low-variance ones on a planted anisotropic cloud.
- `reactPlot` / parse: frames survive `parse_figure_spec`.
- Expand \(Q R\); mass-weighted k-means vs uniform; agglomerative + mass raises.

## Related Requirements

- [REQ-0010](../requirements/req0010_dialogue-pipeline-in-referia.md) — grain from config; knobs as parameters.

## Implementation Status

- [x] `subject_vq_fit` + \(QR\) expand
- [x] Brownian projection walk + Plotly frames
- [x] `lens_weight` uniform / mass
- [x] `02_vq` YAML, 03/04 wiring, viewer + notebook primers

## References

- Linde–Buzo–Gray / k-means as VQ on L2 embeddings (spherical k-means)
- Brownian motion on the Stiefel manifold via tangent noise + QR
- CIP-0019 k-means / grain catalogue
- CIP-0011 `PlotlyFigure`
- CIP-0016 document histograms
