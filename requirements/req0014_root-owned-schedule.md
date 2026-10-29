---
id: "0014"
title: "Reviewers can schedule and browse work on a root-owned timeline"
status: "Validated"
priority: "High"
created: "2026-10-28"
last_updated: "2026-10-28"
related_tenets:
- user-oriented-convenience
- explicit-implicit-separation
- template-driven-composition
stakeholders:
- Reviewers
- Review authors
tags:
- requirement
- web
- catalog
- schedule
- overview
- today
- year
---

# REQ-0014: Reviewers can schedule and browse work on a root-owned timeline

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

A reviewer serving a tree of review configs must be able to see **what needs attention when**, and to **edit that schedule and progress**, without treating the leaf config's identity date as a deadline.

Each review config remains a document of what the review *is* (title, description, when that instance was opened). When the work is due, when an event happens (an interview, a meeting), whether it is done, and a short progress note must live at the **root** of the tree as assessments the reviewer can change. Changing a deadline must not rewrite the leaf config, and the reviewer must be able to see that the deadline moved.

The same scheduled work must be browsable as three outcomes, not one overloaded list:

- **Today** — a dedicated review the reviewer can open, showing only work whose event or deadline is today, with today's items unmistakable.
- **Seasonal** — the existing root overview of active work in a near window.
- **Year** — a dedicated review that lays out the academic year so seasonal bursts (December undergraduate interviews, January PhD and MPhil) are visible as a plan.

Opening Today or Year must not invent a second catalogue of configs. Rows still open the real review.

**Why this matters**: *User-oriented convenience* — a listing that windows on the wrong date hides today's interview in a directory pile. *Explicit–implicit separation* — schedule is an application assessment, not an implicit meaning of leaf metadata. *Template-driven composition* — Today and Year are the same work, instantiated as distinct reviews, not hardcoded product modes.

**Who benefits**: Reviewers who live in a large OneDrive (or similar) tree of seasonal work; authors of overview configs who should not encode deadlines in every leaf file.

## Acceptance Criteria

- [x] A reviewer can set, change, and mark progress on a config's **complete-by** date, **happens-on** date, completion flag, and a short note **without editing that config's own file**
- [x] The leaf config's `date` remains identity (when that review instance was opened / which cohort it is) and is **not** the clock used to decide what is due or happening
- [x] After a deadline or event date changes, the reviewer can see **that it changed** (at least when it last moved), while the leaf identity date stays as it was
- [x] A **Today** review exists as its own openable config: it lists work whose event or complete-by date is today, ranked so today's items are obvious, each row linking to the real review
- [x] A **Year** review exists as its own openable config: it lays out scheduled work across the academic year grouped so monthly bursts are visible
- [x] The root seasonal overview continues to exist and uses the root-owned schedule (not leaf `date`) for its default window
- [x] Today and Year do not appear as items of work in the catalogue they are views of
- [x] Other calendars (talks, teaching, other git roots) are **not** required to be checked out into the review tree for this outcome; a later hub may federate them

## Notes

Leaf files that already carry a `due:` key are a migration hint, not the lasting store: once the root schedule has a value, that value wins. Per-candidate times (this afternoon's interviewee) stay inside the interview review; the root timeline answers *which reviews demand attention today*, not *who is at 15:00*.

Talks and similar GitHub-backed calendars keep their own event dates in their own trees. This requirement does not ask one catalogue to ingest another repository.

## References

- Tenet: [user-oriented-convenience](../tenets/referia/user-oriented-convenience.md)
- Tenet: [explicit-implicit-separation](../tenets/referia/explicit-implicit-separation.md)
- Tenet: [template-driven-composition](../tenets/referia/template-driven-composition.md)
- Related: [REQ-0009](./req0009_multi-config-web-hosting.md), [REQ-000E](./req000E_named-layout-compositions.md)
- CIP-0010 (tall catalog + `complete`; this requirement extends the writable store and the views over it)

## Progress Updates

### 2026-10-28

Requirement created (Proposed). Paired with CIP-001C (root-owned schedule; sibling Today and Year reviews).

### 2026-10-28 (later)

CIP-001C Accepted. Status In Progress. Lynguine discovery bind/exclude is lynguine REQ-000F / CIP-0018; this requirement's outcomes still hold. Backlog created; implementation not started.

### 2026-10-28 (validated)

CIP-001C Closed after live `/today/` check. Status Validated. Formal guide: `docs/usage/catalog_schedule.rst`.
