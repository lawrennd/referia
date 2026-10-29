---
id: "0016"
title: "Phrase codes can be checked from a siding without touching the pipeline"
status: "Proposed"
priority: "Medium"
created: "2026-10-29"
last_updated: "2026-10-29"
related_tenets:
- pragmatic-automation
- explicit-implicit-separation
- user-oriented-convenience
stakeholders:
- Dialogue / public-engagement analysts
- Review authors
tags:
- requirement
- dialogue
- validation
- extract
---

# REQ-0016: Phrase codes can be checked from a siding without touching the pipeline

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

After phrase extract (and after grounds or grain, when those stores exist), an analyst can ask whether a discrete code is internally consistent — reconstructable from the phrase text by a simple model — without rerunning extract, grain, or Part A/B. Extract `kind`, Part B `basis`, and hard grain lens (argmax of phrase-level QR, not Name strings) share that reconstructability check. Each lives beside the main analysis, not as the next numbered stage. It reports whether reconstruction sits near chance, in a useful middle band, or at collapse, and it does not write transcript quotes into the check store.

**Why this matters**: *Pragmatic automation* prefers a cheap, inspectable model over another LLM pass. *Explicit–implicit separation* keeps the extract prompt in 02 and the check knobs in the siding. *User-oriented convenience* lets the analyst open one config when they distrust the kinds.

**Who benefits**: Anyone reading CBC shares from 06 who needs to know the extract kinds are a stable coding, not a coin-flip.

## Acceptance Criteria

- [ ] Named configs reconstruct extract `kind`, Part B `basis`, and hard grain lens from phrase text with cross-validation and write to named stores
- [ ] Chance, majority, and (when documents exist) document-grouped baselines sit beside the CV score
- [ ] Flags distinguish near-chance, useful consistency, and lexical collapse
- [ ] The check does not change `phrases.yml`, the pack, or 01–11 outputs
- [ ] Phrase text is not stored in the check output (identifiers of errors are enough)
- [ ] Compute is field-in / field-out; deleting the stage output and re-running the declared button recreates it

## Notes

This is not human validation, own-words recode, or the word-list floor (09). Those answer different questions. Reconstructability is a consistency check, not proof that the kinds match the paper's coding.

## References

- Tenets as in YAML `related_tenets`
- REQ: [REQ-0010](./req0010_dialogue-pipeline-in-referia.md), [REQ-0015](./req0015_formats-part-a-b-in-referia.md)
- CIP: [CIP-001F](../cip/cip001F.md)

## Progress Updates

### 2026-10-29

Requirement created (Proposed) as a siding on the formats study after 02_embed had labelled kinds.

Same reconstructability contract extended to Part B `basis` and hard grain lens (not Name strings).
