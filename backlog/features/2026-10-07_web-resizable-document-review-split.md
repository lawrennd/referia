---
id: "2026-10-07_web-resizable-document-review-split"
title: "Web UI: resizable split between document viewer and review form"
status: "Proposed"
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

- [ ] A vertical drag handle sits between the document panel and the review
      form on desktop layouts.
- [ ] Dragging the handle redistributes horizontal space between the two panes
      (with sensible min widths so neither pane collapses to unusable).
- [ ] The chosen split survives HTMX record/`/record` swaps in the same page
      load (handle is outside the swapped fragment, or ratio is reapplied).
- [ ] Optional but preferred: remember the ratio in `localStorage` per browser.
- [ ] Keyboard-accessible resize is acceptable as a follow-on; mouse/trackpad
      drag is enough for the first cut.
- [ ] Narrow / single-column layouts remain usable (splitter disabled or hidden
      when panes stack).

## Implementation Notes

Likely touch points: `referia/web/templates/base.html` (or the panel chrome
outside `#review-panel`), CSS for the two-column layout, and a small amount of
JS for pointer drag + optional `localStorage`.

Keep the splitter chrome outside HTMX-swapped fragments where possible so
dragging state is not destroyed on every index change.

## Related

- CIP: 000B
- UX request from ai@cam teaching preliminary review (2026-10-07)

## Progress Updates

### 2026-10-07

Task created as Proposed after web PDF index-in-URL fix landed.
