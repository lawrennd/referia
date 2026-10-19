---
id: "000F"
title: "Interactive viewer components can share context fields with review"
status: "Proposed"
priority: "High"
created: "2026-10-19"
last_updated: "2026-10-19"
related_tenets:
- explicit-implicit-separation
- user-oriented-convenience
- template-driven-composition
- document-centric-management
- pragmatic-automation
- progressive-augmentation
stakeholders:
- Review authors
- Reviewers
- Maintainers
- Dialogue / soft-geometry consumers
tags:
- requirement
- viewer
- review
- display
- ui
- web
- jupyter
- plotly
- interaction
---

# REQ-000F: Interactive viewer components can share context fields with review

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Today `viewer:` content is read-only: row data renders to Liquid or Markdown for the human eye, while only `review:` widgets read and write the shared field store. Authors must be able to place **interactive subject-facing components** in `viewer:` (for example figures of soft geometry) that participate in that same field store: events may write **context** fields, and those writes must refresh any `review:` widgets bound to the same fields. Conversely, review edits to shared fields must be able to restyle interactive viewer entries (for example highlight).

This is a **viewer contract** change, not a new layout region. Existing named compositions (including `side_by_side`) remain sufficient for the common case of look-at surface beside assessment. Passive Liquid/Markdown viewer entries remain valid and one-way. Interactivity is opt-in per entry.

Field **roles** (judgment, context, explore, derived) are authoring concepts. In v1 they are **implicit** from widget placement and bindings: no mandatory `role:` annotation. The convention must be documented in referia so the convenience stays explicit in the application layer.

**Why this matters**: *User-oriented convenience* lets authors bind plots to assessment without a parallel ontology. *Explicit–implicit separation* keeps that convention in referia docs/CIP, not in lynguine. *Template-driven composition* favours reusable viewer entry types over one-off JS. *Document-centric management* keeps the viewer subject-facing (documents and geometry) and review as assessments out. *Pragmatic automation* allows compute/multilogue figure payloads while judgment stays in review widgets. *Progressive augmentation* extends viewer render paths; optional field-role metadata and vongole helpers can follow later.

**Who benefits**: Review authors building geometry- or figure-led workflows (including mixture-of-PPCA style topic exploration); reviewers who select subject context in the viewer and record judgment in the form; maintainers who keep one field bus.

## Acceptance Criteria

- [ ] Passive-only / Markdown / Liquid viewer entries remain one-way; existing configs without interactive entries behave as today
- [ ] Authors can declare interactive viewer entries that write **context** fields via declared bindings
- [ ] Viewer-driven field writes refresh `review:` widgets bound to the same fields (viewer → review propagation via the shared store)
- [ ] Review edits to shared fields can restyle interactive viewer entries (e.g. highlight)
- [ ] Roles are **not** required as YAML annotations in v1; convention is placement + bindings
- [ ] Interactive viewer is not the sole home of judgment criteria (no plot-only scoring dialect without a `review:` field that holds the score)
- [ ] Explore/view parameters may appear on viewer components when they only affect perception of the subject
- [ ] Web and Jupyter honour the same binding contract (transport may differ)
- [ ] Soft-geometry / MPPCA-style workflows are a supported motivating case, not a special product mode
- [ ] No new top-level `visualiser:` slot or new `display.layout` name is required for v1

## Notes

**Viewer vs review (intent):** Viewer explores the subject and may write selection/context/navigation. Review records judgment. Shared field names are fine; which YAML block owns the *widget* encodes the job.

**Persist:** Judgment and context fields use the same persist path as today’s review edits when listed in output / referenced by bindings. Ephemeral explore UI (zoom, hover-only) need not persist. Provenance graphs (“set by plot click”) are out of scope for this requirement’s v1 outcome.

**Not this requirement:** Creating the `vongole` package; moving dialogue libraries into referia; inventing a three-pane prose | plot | form layout (promote only if stacking viewer entries fails).

Implements via CIP-0011 (Proposed). Complements REQ-000E (layout composition unchanged) and CIP-0010 (`side_by_side` / `inline_list`).

## References

- Tenet: [explicit-implicit-separation](../tenets/referia/explicit-implicit-separation.md)
- Tenet: [user-oriented-convenience](../tenets/referia/user-oriented-convenience.md)
- Tenet: [template-driven-composition](../tenets/referia/template-driven-composition.md)
- Tenet: [document-centric-management](../tenets/referia/document-centric-management.md)
- Tenet: [pragmatic-automation](../tenets/referia/pragmatic-automation.md)
- Tenet: [progressive-augmentation](../tenets/referia/progressive-augmentation.md)
- CIP: [CIP-0011](../cip/cip0011.md) (HOW)
- Related: [REQ-000E](./req000E_named-layout-compositions.md), [CIP-0010](../cip/cip0010.md), [CIP-000B](../cip/cip000B.md)

## Progress Updates

### 2026-10-19

Requirement created (Proposed) from interactive-viewer design discussion; paired with CIP-0011 Proposed.
