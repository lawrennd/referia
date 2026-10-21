---
id: "2026-10-21_subject-grain-seed-fit"
title: "subject_grain_seed_fit k=1 bake on a packed corpus row"
status: "Proposed"
priority: "High"
created: "2026-10-21"
last_updated: "2026-10-21"
category: "features"
related_cips: ["0015"]
owner: "lawrennd"
dependencies:
- "2026-10-21_llm-embed-phrases"
tags:
- backlog
- cip0015
- cip0012
- compute
- mppca
- subject_grain_uq
---

# Task: Seed k=1 MPPCA fit on a packed corpus row

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Register `subject_grain_seed_fit` (k=1 MPPCA writing `responsibilities` and
local \(U_q\) planes to `scores.yml`) as a **pure** row-local function on
the packed corpus row. This replaces the Assess half of
`examples/subject_grain_uq/build_records.py` and closes CIP-0012 bake debt
as specified in CIP-0015.

Pack (tall phrase table → one `records.yml` row with array cells) is
**lynguine CIP-0014 Access IO**, not this task. Seed fit reads those arrays
from the current row. Skip-if-already-fit is a field check, not a hidden
checkpoint. Do not register `pack_corpus_row`.

## Acceptance Criteria

- [ ] `subject_grain_seed_fit` reads packed `embeddings` / `phrases`; writes
      `responsibilities`, `uq_by_topic`, `topic_keys`, provisional labels /
      parent / tree
- [ ] Parameters `sigma2`, `sigma2_mode`, `k=1`, `em_accept` come from config
      or output fields
- [ ] `03_grain` precompute calls seed fit when `responsibilities` is empty
- [ ] Offline / stub path works without `OPENAI_API_KEY`
- [ ] `build_records.py` Assess writes become a thin wrapper or are scheduled
      for deletion (pack waits on lynguine CIP-0014)
- [ ] Unit tests: k=1 R rows sum to 1 (hand-packed synthetic row)

## Implementation Notes

Reuse `referia.assess.compute.mppca.mppca_fit`. Sibling task
`2026-10-19_cip0017-lynguine-access-bake` is the same Assess bake,
retargeted to CIP-0015 — implement once, close both. Pack criteria on that
sibling move to lynguine CIP-0014.

Proposed only: do not implement until CIP-0015 is Accepted.

## Related

- CIP: 0015
- CIP-0012 remaining work (Assess bake only)
- Pack: lynguine CIP-0014
- Backlog: `2026-10-19_cip0017-lynguine-access-bake`
- Draft: OneDrive `applications/2026-10-21_dialogue-analysis/03_grain/`

## Progress Updates

### 2026-10-21

Task created as Proposed from CIP-0015 (`pack_corpus_row` sketch). Retargeted
the same day: pack is lynguine CIP-0014; this task is seed fit only.
