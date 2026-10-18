---
id: "2026-10-18_align-compute-docs-vongole-intent"
title: "Align referia compute docs with vongole / lynguine layering"
status: "Proposed"
priority: "High"
created: "2026-10-18"
last_updated: "2026-10-18"
category: "documentation"
related_cips: ["0006"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- documentation
- vongole
- compute
- llm
---

# Task: Align referia compute docs with vongole intent

> Documentation cleanup that may proceed while lynguine CIP-0007 is still **Proposed**.
> Does not change referia’s inheritance to vongole (that waits on Accept + implementation).

## Description

Referia currently extends lynguine directly and hosts assessment + LLM compute. Lynguine CIP-0007 (revised 2026-10-18) documents the **target** middle layer `vongole`, but referia docs and tenets still say “promote to lynguine” as if that were the only home for general-purpose compute. Sphinx also still marks LLM as “Planned” though CIP-0006 is Closed.

Update referia docs/CIPs/tenets so layering is honest:

| Layer | Owns |
|-------|------|
| lynguine | Engine + access compute (incl. CIP-0013 document→units) |
| vongole (future) | Assessment libraries currently registered in referia |
| referia | Review-domain compute (LLM review/query, comments, document ops outside registry) |

## Acceptance Criteria

- [ ] `docs/usage/compute.rst` — remove or rewrite “LLM Integration (Planned)”; point at Closed CIP-0006 and live registry; mention optional `poetry install --with llm`
- [ ] `cip/cip0006.md` — add a short “Promotion path (post-closure)” note: generic LLM + assessment libraries → **vongole** (lynguine CIP-0004/0007, 2026-10-18); review-domain stays referia; lynguine is engine/access only
- [ ] `tenets/referia/progressive-augmentation.md` — examples mention vongole as the assessment (incl. generic LLM) promotion target where appropriate (not “promote LLM to lynguine”)
- [ ] `docs/llm_integration.md` / `docs/llm_pdf_review.md` — one-line layering pointer if they imply all LLM forever stays unstructured in referia
- [ ] README or architecture blurb (if any) does not claim referia is the permanent home for `word_count`-class helpers

## Implementation Notes

- Do **not** retarget `class Compute(lynguine…)` in this task.
- Link outward to lynguine CIP-0007 / REQ-0006 for the package split; do not duplicate the full design in referia.
- Companion lynguine task: `backlog/documentation/2026-10-18_align-compute-framework-docs-vongole-intent.md`

## Related

- lynguine CIP: 0007 (Proposed, revised 2026-10-18)
- referia CIP: 0006 (Closed)
- Tenet: progressive-augmentation

## Progress Updates

### 2026-10-18

Task created after cross-repo compute audit and lynguine CIP-0007 revision.
