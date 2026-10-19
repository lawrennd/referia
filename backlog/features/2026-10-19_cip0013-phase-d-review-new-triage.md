---
id: "2026-10-19_cip0013-phase-d-review-new-triage"
title: "CIP-0013 Phase D: review_new.py triage"
status: "Completed"
priority: "Medium"
created: "2026-10-19"
last_updated: "2026-10-19"
category: "features"
related_cips: ["0013"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- cip0013
- tests
- coverage
---

# Task: Phase D — `review_new.py` triage

## Description

Decide whether to cover or remove/fold the parallel `review_new.py`
Reviewer. Production entry (`referia.display`) uses `review.py`;
`review_new` is only lightly exercised (create_viewer dispatch).

## Acceptance Criteria

- [x] Written triage decision in CIP-0013
- [x] If keep: no deep coverage investment this CIP; existing dispatch
      smoke retained
- [x] If remove: follow-on CIP/backlog created (not blocking 0013 close)

## Implementation Notes

**Decision (2026-10-19):** Defer deep coverage. Keep module as a parallel
fork for now; do not treat its ~13% coverage as blocking the package
target. Candidate for fold/delete in a later CIP. Package excl.
`review_new` is **71%** (target ≥65%).

## Related

- CIP: 0013

## Progress Updates

### 2026-10-19

Triage recorded: defer deep tests; retain create_viewer smoke only.
Marked Completed.
