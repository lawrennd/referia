---
id: "2026-10-19_cip0017-lynguine-access-bake"
title: "CIP-0017: Replace build_records.py with a lynguine Access → Assess bake"
status: "Proposed"
priority: "Medium"
created: "2026-10-19"
last_updated: "2026-10-21"
category: "features"
related_cips: ["0015"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- cip0015
- lynguine
- access
- subject_grain_uq
---

# Task: Lynguine Access → Assess bake for subject_grain_uq

## Description

`examples/subject_grain_uq/build_records.py` currently does two stages in one
imperative script:

1. **Access** — fetch CIMT (or synthetic phrases), embed, PCA-reduce, write
   `info/records.yml` (phrases + embeddings).
2. **Assess seed** — fit soft MPPCA at k=1, write `info/scores.yml`
   (responsibilities, local \(U_q\) planes, EM / label defaults).

Referia already consumes those YAML stores via `_referia.yml` `input:` /
`output:`. The bake itself is not a lynguine flow: no Access config, no
explicit stage boundary, and regenerating either file requires running the
whole script.

Replace (or wrap) `build_records.py` with a lynguine-shaped pipeline so
Access artefacts and Assess seed are produced the same way the rest of the
stack expects — transparent data flow, question-agnostic Access, Assess fit
as a separate step.

## Acceptance Criteria

- [ ] Access path produces `records.yml` (or equivalent store) without running
      MPPCA fit — CIMT / synthetic / embeddings configurable
- [ ] Assess seed path fits k=1 soft MPPCA from Access output and writes
      `scores.yml` (gitignored), reusing `referia.assess.compute.mppca`
- [ ] Offline / CI still works (`--synthetic` or equivalent) without
      `OPENAI_API_KEY`
- [ ] Example README documents the flow; `build_records.py` is removed or
      becomes a thin CLI over the lynguine config
- [ ] Decision recorded: keep committed `records.yml` as a frozen Access
      snapshot, or gitignore and require bake before `serve`

## Implementation Notes

Possible shapes (pick one in the CIP / during implement):

1. **Lynguine Access config** that writes the input YAML (CIMT download +
   embed as Access compute / IO), then a small Assess precompute or
   `from_flow` that seeds `scores.yml`.
2. **Two CLI entrypoints** (`bake_access` / `bake_assess`) backed by shared
   helpers, still without full flow YAML — interim if flow IO for remote
   TSV + OpenAI needs new lynguine adapters.
3. **Promote reusable Access** (CIMT registry, embed→PCA) toward multilogue /
   pub-dialogue Access modules so referia only hosts Assess compute.

Keep AAA: Access must not encode Propose/Confirm or lens prompts; Assess
seed is question-agnostic geometry only (k=1 catalogue), matching multilogue
notebook 03 Layer B.

## Related

- CIP: 0015 (was 0012; Assess bake is extract / embed / seed fit)
- Pack: lynguine CIP-0014
- PR: #35
- Example: `examples/subject_grain_uq/`
- Draft: OneDrive `applications/2026-10-21_dialogue-analysis/`

## Progress Updates

### 2026-10-19

Task created from PR #35 discussion: `scores.yml` already gitignored and
recreated by bake; `records.yml` is also generated but still committed.
Retargeted to CIP-0012 (packaging / Access → Assess separation).

### 2026-10-21

Retargeted: extract / embed / `subject_grain_seed_fit` → CIP-0015;
pack (tall table → corpus row of arrays) → lynguine CIP-0014 Access IO
(not `pack_corpus_row` compute). CIP-0012 keeps plane-parameter storage vs
figure rebuild. Still Proposed — do not implement until those CIPs are
Accepted.
