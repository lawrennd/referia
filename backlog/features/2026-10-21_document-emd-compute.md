---
id: "2026-10-21_document-emd-compute"
title: "Port document histograms, EMD, MDS, and permutation tests as referia compute"
status: "Completed"
priority: "High"
created: "2026-10-21"
last_updated: "2026-10-21"
category: "features"
related_cips: ["0016"]
owner: "lawrennd"
dependencies:
- "2026-10-21_subject-grain-seed-fit"
tags:
- backlog
- cip0016
- compute
- emd
- mds
- permanova
- distance
---

# Task: Document-level EMD Address compute

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Port multilogue `distance.py` into referia as **pure** module functions
(`compute/distance.py`): document soft-topic histograms, topic means, cosine
ground cost, pairwise EMD, classical MDS, PERMANOVA, PERMDISP, and axis
correlates. After lynguine CIP-0014 pack, these are **row-local** on the
packed corpus + scores row. All results are output columns on
`document_distance.yml`. Add optional extra on the Assess package
(`referia[distance]` → `pot` today; `vongole[distance]` after CIP-0007).

No `document_distance_*.npy` sidecars. Constants `min_mass`, `n_perm`, `seed`,
and group field name come from `_referia.yml`.

## Acceptance Criteria

- [x] `document_soft_topic_distributions` writes `P`, `doc_ids_kept`, `doc_mass`
- [x] `topic_means_from_responsibilities` writes L2-normalised `topic_means`
- [x] `cosine_ground_cost` writes `ground_cost`
- [x] `emd_distance_matrix` writes `emd_matrix`; ImportError names the
      Assess extra (`referia[distance]` today) if POT is missing
- [x] `classical_mds` writes `mds_coords` (and explained / negative-ratio)
- [x] `permanova` / `permdisp` / `axis_correlates` write JSON-serialisable
      results plus Markdown field `distance_tests_md`
- [x] Optional façade `run_document_distance_analysis` writes the same columns
- [x] Core install does not require `pot`
- [x] Unit tests without POT for histograms, cost, MDS, permutation count

## Implementation Notes

See [CIP-0016](../../cip/cip0016.md). Soft R is the default histogram; hard
counts can wait. Group labels join on `doc_id` from `documents.yml` (Access
join). Do not invent a table-level compute mode. Maths is vongole-shaped;
Plotly builders are a separate task and stay in referia.

Proposed only: do not implement until CIP-0016 is Accepted.

## Related

- CIP: 0016
- Source: `multilogue/distance.py`
- Draft: OneDrive `applications/2026-10-21_dialogue-analysis/04_distance/`

## Progress Updates

### 2026-10-21

Task created as Proposed from CIP-0016.

Implemented `referia/assess/compute/distance.py` and `referia[distance]` extra.
