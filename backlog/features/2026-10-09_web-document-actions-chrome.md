---
id: "2026-10-09_web-document-actions-chrome"
title: "Web UI: move Create document buttons into fixed action chrome"
status: "Proposed"
priority: "Medium"
created: "2026-10-09"
last_updated: "2026-10-09"
category: "features"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- web
- ui
- documents
- htmx
- chrome
---

# Task: Relocate Create document actions into page chrome

> Backlog tasks are DOING the work defined in CIPs (HOW).
> Linked CIP: 000B (web display).

## Description

Create / Create Summary document buttons currently sit inside the left-pane
**Documents** panel (`render_document_panel` → `.document-actions`), above
the PDF list. On long review sessions they scroll away with the document
column and compete with PDF expand/collapse chrome.

They belong with other **session actions** (Save / Reload), not with the
document viewer content.

### Placement options (pick one when implementing)

**A. Top `panel-nav` actions (with Save / Reload)**  
Add the document-generation buttons into `.nav-actions` in
`review_panel.html` (right side of the fixed-feeling nav row that already
holds Save and Reload). Keeps one action strip; no new chrome.

**B. Fixed bottom action bar**  
A persistent bar at the bottom of the viewport (sibling idea to the
transient `#status-bar`, which is already `position: fixed; bottom: 0`).
Holds Create document actions (and optionally mirrors Save/Reload). Must
leave room for / stack with status feedback so downloads and “Updated /
Saved” messages remain readable.

**Recommendation to try first:** **A** — fewer surfaces, matches existing
Save/Reload grouping, avoids fighting the status bar. Fall back to **B**
if the top bar becomes overcrowded (many `documents:` / `summary_documents:`
entries).

## Acceptance Criteria

- [ ] Create / Create Summary document buttons are no longer the primary
      control cluster inside the scrolling Documents panel (PDF list /
      edit-pdf actions may stay with documents).
- [ ] Buttons remain available without scrolling the document column
      (top nav and/or fixed bottom chrome).
- [ ] HTMX behaviour unchanged: `POST /generate-document/{n}` /
      `/generate-summary-document/{n}`, status in `#status-bar`, download
      link when a file is written.
- [ ] Root-server path prefix rewriting still works for the relocated
      buttons.
- [ ] Layout does not obscure `#status-bar` success/error text or the
      download affordance after generation.
- [ ] Tests updated for wherever the buttons are rendered (template /
      render helpers).

## Implementation Notes

### Current code

- Buttons built in `referia/web/render.py` → `render_document_panel`
  (`.document-actions`).
- Injected via `document_html` into the left column of
  `referia/web/templates/review_panel.html`.
- Save / Reload live in `.nav-actions` in the same template (not via
  widget specs in the web panel path).
- `#status-bar` is fixed to the bottom in `style.css`.

### Suggested approach

1. Decide A vs B (default A unless nav is too crowded).
2. Pass document action button HTML (or structured entries) into the
   panel template separately from PDF/URL markup — e.g. split
   `render_document_panel` into document list vs action buttons, or
   render actions in the template from `list_document_entries`.
3. Keep PDF open/create-edit controls near the PDFs if that still makes
   sense; only relocate **generate document** actions.
4. CSS: reuse `.widget-button` / distinct class for document actions so
   they don’t look like Save (green) accidentally.

### Out of scope

- Changing generate/download backend behaviour.
- Moving PopulateButton / per-field compute controls.

## Related

- CIP: 000B
- Prior: document generate/download work (`POST /generate-document`,
  auto-download); Documents panel in `render_document_panel`
- Code: `referia/web/templates/review_panel.html` (`.nav-actions`),
  `referia/web/render.py` (`render_document_panel`),
  `referia/web/static/style.css` (`.status-bar`)

## Progress Updates

### 2026-10-09

Proposed after live review: Create document controls should sit in fixed
chrome (bottom bar like status, or with Save/Reload at the top), not only
inside the scrolling Documents panel.
