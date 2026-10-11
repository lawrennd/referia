---
id: "2026-10-11_preserve-scroll-across-record-switch"
title: "Preserve left/right scroll when switching records (web)"
status: "Completed"
priority: "Medium"
created: "2026-10-11"
last_updated: "2026-10-11"
category: "features"
related_cips: ["0010"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- features
- web
- htmx
- scroll
- cip0010
- retrospective
---

# Task: Preserve scroll across record switches

> Linked CIP: 0010 (web review chrome).  
> **Retrospective:** implementation began before this backlog existed; task filed to restore backlog-first process.

## Description

When the reviewer changes the Record selector in `side_by_side` layout, HTMX replaces `#review-panel` with `innerHTML`. That rebuild resets:

- Left `.viewer-col` scroll (independent `overflow-y: auto` pane)
- Right / window scroll (review form)

Open/closed `<details>` state already survives these swaps; scroll should too, so moving between records keeps the same visual place in document and form.

Out of scope for this task: PDF iframe internal scroll positions.

## Acceptance Criteria

- [x] Capture `.viewer-col.scrollTop` and `window.scrollY` on `htmx:beforeSwap` when target is `#review-panel`
- [x] Restore (clamped) after `htmx:afterSettle` (after layout/MathJax settle)
- [x] Index select uses HTMX 2 `focus-scroll:false` so focus management does not jump the page
- [x] Smoke-test: mid-scroll left and right survive a record change on a live `side_by_side` review
- [x] `inline_list` unaffected (no `.viewer-col` → no-op)

## Implementation Notes

- Pattern: mirror details-persistence IIFE in `referia/web/templates/base.html`
- Index select swap string in `referia/web/routes.py` `_render_index_selector`
- Double `requestAnimationFrame` after settle so sticky-height / MathJax handlers run first

## Related

- CIP: 0010
- PRs: #24 (CIP-0010 branch; this change may land as a follow-up commit)
- Plan: preserve panel scroll (session plan)

## Progress Updates

### 2026-10-11

Task created retrospectively. Capture/restore JS and `focus-scroll:false` already applied in `base.html` / `routes.py` before this file existed. Remaining: smoke-test on a live side_by_side review, then mark Completed.

### 2026-10-11 (smoke)

Verified on `http://127.0.0.1:8000/theses/examined/introduction/`: scrolled left `.viewer-col` and window, switched Record (Shumailov → Churamani); both scroll positions restored (`viewerPreserved` / `windowPreserved`). Overview `/` (inline_list) still loads. Note: long-running serve process still emits `hx-swap="innerHTML"` without `focus-scroll:false` until restart; JS restore alone was sufficient in the smoke test.
