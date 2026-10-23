---
id: "2026-10-23_cip0018-stacked-inherit-tests"
title: "Tests for stacked inherit default, query allowlist, and read-only ancestors"
status: "Ready"
priority: "High"
created: "2026-10-23"
last_updated: "2026-10-23"
category: "features"
related_cips: ["0018"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-10-23_cip0018-interface-layers"
- "2026-10-23_cip0018-view-query-allowlist"
- "2026-10-23_cip0018-preserve-view-params"
- "2026-10-23_cip0018-stacked-web-specs"
- "2026-10-23_cip0018-inherited-section-render"
tags:
- backlog
- features
- tests
- inherit
- cip0018
---

# Task: Fixture chain tests for CIP-0018

> Linked CIP: 0018. Testing Strategy in the CIP is the source of cases.

## Description

Fixture chain of three `_referia.yml` files (grandparent viewer+review, parent viewer+review, child viewer+review), shared index, parent fields present on the child frame via inherit input.

Cover default, stacked, flags, rejected extras, HTMX param survival, and read-only persistence.

## Acceptance Criteria

- [ ] No params / `compose=link`: child specs only for review; parent link present; no inherited Section titles
- [ ] `compose=stacked`: ancestor sections above child in viewer and review; titles match ancestor `title`; order grandparent, parent, child
- [ ] `compose=stacked&inherit_review=0`: ancestor viewers only; child review unchanged
- [ ] `compose=stacked&writable=true` (or any path-like extra): ignored; ancestor review stays read-only; no extra files loaded
- [ ] `compose=not-a-mode`: treated as default `link`, not an error page
- [ ] Query params survive index change (HTMX) so the stacked view does not snap back
- [ ] `writable: false` in YAML: ancestor review controls are not persisted to the child output store even when stacked
- [ ] CIP-0010 `inline_list` still lists rows; stacked inherit does not flatten the working set

## Implementation Notes

- Prefer route/WebReviewer tests over a live browser unless an existing web fixture already covers query strings.
- Unknown query values must be asserted not to appear raw in HTML.

## Related

- CIP: 0018

## Progress Updates

### 2026-10-23

Task created (Ready) when CIP-0018 was Accepted.
