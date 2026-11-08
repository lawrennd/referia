---
id: "2026-11-08_cip0026-llm-notebook-triage"
title: "CIP-0026 Phase C: LLM / thesis / notebook triage"
status: "Completed"
priority: "Low"
created: "2026-11-08"
last_updated: "2026-11-08"
category: "documentation"
related_cips: ["0026"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- documentation
- examples
- llm
- notebooks
---

# Task: Triage LLM, thesis, and notebook artefacts

> Backlog task for [CIP-0026](../../cip/cip0026.md) Phase C.

## Description

Decide keep / update / retire for `docs/examples/*.ipynb` and checkpoints.
Document LLM / thesis YAML snippets as secondary to `referia serve`; keep
`.py` scripts as optional API illustrations. Ensure env template pointers
stay accurate. Cross-link from examples index and LLM docs.

## Acceptance Criteria

- [x] Clear keep/update/retire decision for each `docs/examples/*.ipynb`
- [x] Checkpoints removed or ignored if not useful
- [x] LLM / thesis examples documented with serve-first guidance
- [x] `docs/llm_*.md` and examples index cross-links updated

## Implementation Notes

Prefer not to maintain two conflicting tutorials. Leave a one-line pointer
in the examples index if anything useful remains after retirement.

## Related

- CIP: 0026

## Progress Updates

### 2026-11-08

Task created; can parallelise with Phase A.

**Decisions:**
- Retire `docs/examples/test_*.ipynb` and tracked `.ipynb_checkpoints/`
  (local pytest scratchpads with hardcoded paths).
- Keep LLM / thesis YAML + `.py` as snippets; add `examples/README.md`
  and serve-first headers; update Sphinx index + `docs/llm_*.md`.
- No cheap serveable LLM directory (needs sample PDFs/data) — deferred.
