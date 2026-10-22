---
id: "2026-10-21_llm-extract-phrases"
title: "Register llm_extract_phrases compute (cache payload + phrase rows)"
status: "Completed"
priority: "High"
created: "2026-10-21"
last_updated: "2026-10-21"
category: "features"
related_cips: ["0015"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- cip0015
- compute
- llm
- phrases
---

# Task: LLM phrase extraction compute

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Register `llm_extract_phrases` so a chunk row’s `text` becomes short concern /
benefit / (formats) condition phrases. Prompt, sentinel, model, and kinds come
from constants. Write the raw payload to a named **cache** column
(`extraction_payload` only; gzip YAML). Phrase dicts explode into
`phrases.yml.gz` and are **not** persisted as a second cache list. Do not
write `extracted_*.json` or StageRunner jsonl as the analysis store.

Does not replace `llm_extract` (free-text comments).

## Acceptance Criteria

- [x] Compute is field-in / field-out: `(text, constants) → extraction_payload`
      plus a list of phrase dicts for explode
- [x] Sentinel and word-count drop rules are parameters, not hidden code
- [x] Phrase rows carry `phrase`, `kind`, `chunk_id`, `doc_id` (optional quote)
- [x] LLMManager diskcache, if used, is cost-only; payload is still in cache
- [x] Unit tests with a stub client (no live API); sentinels dropped
- [x] Draft `02_embed/_referia.yml` PopulateButton uses this name

## Implementation Notes

See [CIP-0015](../../cip/cip0015.md). Flatten list can reuse lynguine
`output.explode` (CIP-0014) on the payload field.

Proposed only: do not implement until CIP-0015 is Accepted.

## Related

- CIP: 0015
- Draft: OneDrive `dialogue-analysis/template/02_embed/`

## Progress Updates

### 2026-10-21

Task created as Proposed from CIP-0015.

Implemented `llm_extract_phrases` with a stub-client test; `02_embed` uses this name.
