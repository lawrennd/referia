---
id: "2026-10-21_llm-embed-phrases"
title: "Register llm_embed compute writing embedding on the phrase row"
status: "Proposed"
priority: "High"
created: "2026-10-21"
last_updated: "2026-10-21"
category: "features"
related_cips: ["0015"]
owner: "lawrennd"
dependencies:
- "2026-10-21_llm-extract-phrases"
tags:
- backlog
- cip0015
- compute
- embeddings
- llm
---

# Task: Embed phrases as a row column

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Register `llm_embed` so each phrase row gets an L2-normalised `embedding`
column. Model and optional PCA dimension come from constants. The vector lives
on the phrase row (cache or output), not a sidecar `.npy` or a private Embedder
hash directory as the only copy.

## Acceptance Criteria

- [ ] Reads `phrase` (or a configured text field); writes `embedding` (list of
      floats, L2-normalised)
- [ ] Optional `pca_dim` from constants reduces the stored vector
- [ ] Batching inside one call is allowed; no module-level queue as analysis
      state
- [ ] LLMManager cost cache is optional and insufficient as the store
- [ ] Unit tests with a fake client; vectors have unit L2 norm
- [ ] Draft `02_embed` PopulateButton names `llm_embed`

## Implementation Notes

See [CIP-0015](../../cip/cip0015.md). Add embeddings API on `LLMManager` if
missing. CIP-0006: referia first, do not promote to lynguine in this task.

Proposed only: do not implement until CIP-0015 is Accepted.

## Related

- CIP: 0015
- Depends on: `2026-10-21_llm-extract-phrases` (phrase rows exist)
- Draft: OneDrive `applications/2026-10-21_dialogue-analysis/02_embed/`

## Progress Updates

### 2026-10-21

Task created as Proposed from CIP-0015.
