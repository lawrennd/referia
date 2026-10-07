---
id: "2026-10-07_web-resizable-document-review-split"
title: "Web UI: resizable split between document viewer and review form"
status: "Completed"
priority: "Medium"
created: "2026-10-07"
last_updated: "2026-10-07"
category: "features"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- web
- ui
- layout
- accessibility
---

# Task: Resizable vertical split between documents and scoring

> Backlog tasks are DOING the work defined in CIPs (HOW).
> Linked CIP: 000B (web display).

## Description

In the web review UI the document pane (PDF / viewer material) and the
review/score form sit side by side. Reviewers often want more width for the
document while reading, then more width for the form while scoring.

Add a **draggable vertical splitter** (grab bar) between the two panes so the
relative widths can be adjusted. Persist the chosen ratio for the session
(and ideally across reloads via `localStorage`) so it does not reset on every
HTMX panel swap.

## Acceptance Criteria

- [x] A vertical drag handle sits between the document panel and the review
      form on desktop layouts.
- [x] Dragging the handle redistributes horizontal space between the two panes
      (with sensible min widths so neither pane collapses to unusable).
- [x] The chosen split survives HTMX record/`/record` swaps in the same page
      load (handle is outside the swapped fragment, or ratio is reapplied).
- [x] Optional but preferred: remember the ratio in `localStorage` per browser.
- [x] Keyboard-accessible resize is acceptable as a follow-on; mouse/trackpad
      drag is enough for the first cut.
- [x] Narrow / single-column layouts remain usable (splitter disabled or hidden
      when panes stack).

## Implementation Notes

Implemented with:

- `.col-splitter` between `.viewer-col` and `.review-col` in
  `review_panel.html` (`role="separator"`).
- Flex layout + `--viewer-pct` in `style.css` (hidden below 900px).
- Pointer drag + `localStorage` key `referia.split.viewerPct` in `base.html`,
  reapplied on `htmx:afterSettle` when `#review-panel` is swapped.

## Related

- CIP: 000B
- UX request from ai@cam teaching preliminary review (2026-10-07)

## Progress Updates

### 2026-10-07

Task created as Proposed after web PDF index-in-URL fix landed.

### 2026-10-07

Implemented splitter markup, CSS, and JS; marked Completed.
