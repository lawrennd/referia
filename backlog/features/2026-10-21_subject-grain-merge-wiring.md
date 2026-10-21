---
id: "2026-10-21_subject-grain-merge-wiring"
title: "Optional merge in subject grain (deferred; not in first four configs)"
status: "Proposed"
priority: "Low"
created: "2026-10-21"
last_updated: "2026-10-21"
category: "features"
related_cips: ["0012"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- cip0012
- subject_grain_uq
- merge
- deferred
---

# Task: Wire merge in subject grain

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

multilogue can merge topics in Python; referia `subject_grain_uq` only wires
Propose split / Confirm / Undo / Name. This task is deferred step 13 of
REQ-0010 — **not** in the first four dialogue configs. Keep a Proposed marker
so merge is not forgotten, and so `03_grain/_referia.yml` comments stay honest.

Do not implement as part of CIP-0015 / CIP-0016 first pass.

## Acceptance Criteria

- [ ] Design recorded (new CIP or CIP-0012 amendment) before code
- [ ] Merge is field-in / field-out: catalogue writes to `scores.yml` only
- [ ] Confirm / Undo semantics for merge match split (snapshot + restore)
- [ ] First four dialogue configs remain runnable without merge

## Implementation Notes

Exists in multilogue; not in referia. `03_grain` draft comments mark merge as
not wired. Wait for grain split loop to be stable in the dialogue pipeline
before accepting a merge CIP.

## Related

- CIP: 0012 (grain packaging; merge is extra Assess UX)
- Deferred REQ-0010 step 13
- Draft: OneDrive `applications/2026-10-21_dialogue-analysis/03_grain/`

## Progress Updates

### 2026-10-21

Task created as Proposed. Explicitly deferred from the first deployment.
