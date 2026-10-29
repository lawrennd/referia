---
id: "0015"
title: "Formats Part A tables, Part B grounds, and validation run from chained referia configs"
status: "Proposed"
priority: "High"
created: "2026-10-29"
last_updated: "2026-10-29"
related_tenets:
- document-centric-management
- pragmatic-automation
- user-oriented-convenience
- explicit-implicit-separation
- template-driven-composition
stakeholders:
- Dialogue / public-engagement analysts
- Review authors
- Maintainers
tags:
- requirement
- dialogue
- formats
- grounds
- validation
---

# REQ-0015: Formats Part A tables, Part B grounds, and validation run from chained referia configs

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

After subject grain, an analyst can finish the chatbot-versus-workshop paper analyses from further chained `_referia.yml` configs that share the same `info/` stores. That means document-weighted type and lens shares with bootstrap intervals and Jensen–Shannon divergence on the lens profiles (Part A), basis coding of each extracted point and the experience / principle gaps by format (Part B), the chatbot question-type stress test, and the word-list experience floor. Own-words recode, stories-follow-stories, and the 1080-config multiverse remain later configs or the public package replay; they are not required for this outcome.

REQ-0010’s first deployment stopped at EMD geometry. This requirement is the formats-specific remainder that the draft paper actually reports.

**Why this matters**: *Document-centric management* keeps tables in named stores, not notebook side effects. *Pragmatic automation* uses an LLM only for grounds, not for the word list or JSD. *User-oriented convenience* lets the analyst serve each stage. *Explicit–implicit separation* keeps prompts in parameters. *Template-driven composition* reuses pack + grain + one-row façades.

**Who benefits**: Analysts reconstructing “An elicitation fallacy?” in referia; anyone who needs Table 1 / grounds numbers from the current grain rather than only from `Run(replay=True)`.

## Acceptance Criteria

- [ ] Document-weighted CBC and lens shares, with cluster-bootstrap intervals and JSD, are output columns of a named store after 04_grain
- [ ] Those shares use pack `doc_id` (conversation / workshop transcript), not pooled phrase counts
- [ ] Each extracted point can receive a basis label from a unit-level LLM call whose prompt lives in parameters
- [ ] Chatbot question-type shares are computed from unit context with no model call
- [ ] A word-list experience floor runs on each point’s own quote with no model call
- [ ] Compute is field-in / field-out; deleting the stage output and re-running the declared button recreates it
- [ ] Canonical frozen k-means labels and the 1080-config multiverse are not required for this outcome

## Notes

Headline experience 17.7% vs 4.1% comes from grounds, not from 04_grain. JSD 0.006 comes from Jess’s 11 lenses on frozen k=40; a referia grain with a different catalogue will not match that figure bit-for-bit.

## References

- Tenets as in YAML `related_tenets`
- REQ: [REQ-0010](./req0010_dialogue-pipeline-in-referia.md)
- CIP: [CIP-001E](../cip/cip001E.md)

## Progress Updates

### 2026-10-29

Requirement created (Proposed) once 01–04 of the formats study had run and 05–Part B were still missing.
