---
id: "0018"
title: "A corpus populate can run as rolling batches the reviewer can watch and pause"
status: "Proposed"
priority: "High"
created: "2026-10-29"
last_updated: "2026-10-29"
related_tenets:
- user-oriented-convenience
- pragmatic-automation
- explicit-implicit-separation
stakeholders:
- Reviewers
- Review authors
- Maintainers
tags:
- requirement
- web
- populate
- htmx
- llm
---

# REQ-0018: A corpus populate can run as rolling batches the reviewer can watch and pause

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Extract all, Embed all, Classify all, and the same populate-all family must be able to run as a **rolling** job: a bounded amount of work, then a visible update, then the next bound, until the working set is done or the reviewer pauses. The reviewer sees how far the run has got. Pause stops further batches without throwing away rows already written. Resume continues from unfilled rows.

REQ-0010 already says results live on declared stores, not RAM. REQ-0013 is a killable runtime. This requirement is the interactive loop: the browser is not asked to hold one POST for the corpus, and the reviewer is not asked to wait an hour to learn that HTMX failed.

**Why this matters**: *User-oriented convenience* is a progress bar and a Pause that work. *Pragmatic automation* bills the API in slices the reviewer can stop. *Explicit–implicit separation* keeps batch size in the button config, not in a hidden worker.

**Who benefits**: Anyone running Extract/Classify all on thousands of units; anyone whose laptop sleeps mid-run (the chain stops; resume is skip-filled).

## Acceptance Criteria

- [ ] Populate-all of a large working set proceeds as successive short steps, not one hour-long request
- [ ] A progress display shows done / total (and failures) while the run is in flight
- [ ] The reviewer can pause; further steps do not start; already-written rows remain
- [ ] Resume continues from rows that are still empty (Refresh cache remains the explicit redo)
- [ ] Closing the tab or sleeping the machine does not require a special job queue to remain consistent with pause: the next populate-all is resume
- [ ] Populate-all still means the full filtered working set, not the CIP-0020 listing page

## Notes

Mid-row cancel of an in-flight LLM call is REQ-0013 / CIP-001B, not this outcome. Pause is cooperative at batch boundaries.

## References

- Tenets as in YAML `related_tenets`
- REQ: [REQ-0010](./req0010_dialogue-pipeline-in-referia.md), [REQ-0013](./req0013_restartable-review-runtime.md)
- CIP: [CIP-0021](../cip/cip0021.md), [CIP-001D](../cip/cip001D.md)

## Progress Updates

### 2026-10-29

Requirement created (Proposed) after Extract all on 2013 units was one POST and CIP-001D left rolling/progress as the “preferred” path rather than the interaction.
