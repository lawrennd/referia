---
id: "2026-10-23_cip0018-inherited-section-render"
title: "Render inherited Sections read-only with open-in-parent header link"
status: "Ready"
priority: "High"
created: "2026-10-23"
last_updated: "2026-10-23"
category: "features"
related_cips: ["0018"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-10-23_cip0018-stacked-web-specs"
tags:
- backlog
- features
- web
- inherit
- widgets
- cip0018
---

# Task: Render inherited Sections read-only

> Linked CIP: 0018. `inherit.writable: false` stays the default.

## Description

Inherited Sections use existing collapsible `<details>` (CIP-0014 persist keys still work). Under `compose=stacked`:

- Ancestor **viewer** is always display.
- Ancestor **review** widgets show existing values from the child's already-hstacked data.
- Those widgets are **read-only** unless that hop set `writable: true` **and** the field is in a store the child session may write. Do not quietly persist parent scores into the child's output file.
- Each inherited Section header has a small "open in parent" control with `?index=` for the current record, plus current view params.

`compose=stacked` never makes ancestor review editable via the query string.

## Acceptance Criteria

- [ ] Inherited Sections render as collapsible details with the ancestor title
- [ ] `writable: false` (default): ancestor review controls are not persisted to the child output store
- [ ] `?compose=stacked&writable=true` is ignored; ancestor review stays read-only
- [ ] Header "open in parent" includes `?index=` for the current record
- [ ] Side-by-side chrome unchanged: viewer pane stacks ancestor viewers; review pane stacks ancestor review

## Implementation Notes

- `writable: true` is the advanced case (parent output really is this session's writable store). Document it; tests must cover the false default.
- Stacked header link subsumes `2026-07-16_parent-assessor-link-index` for stacked mode only.

## Related

- CIP: 0018
- Related: `2026-07-16_parent-assessor-link-index` (still needed for `compose=link`)

## Progress Updates

### 2026-10-23

Task created (Ready) when CIP-0018 was Accepted.
