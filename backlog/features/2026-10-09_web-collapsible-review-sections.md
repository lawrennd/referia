---
id: "2026-10-09_web-collapsible-review-sections"
title: "Web UI: collapsible review-form sections (chapter / heading groups)"
status: "Completed"
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
- htmx
- markdown
- templates
- scrolling
---

# Task: Collapsible sections in the review form (right pane)

> Backlog tasks are DOING the work defined in CIPs (HOW).
> Linked CIP: 000B (web display).

## Description

Document PDFs in the left pane already use `<details class="pdf-entry">` so
each file starts collapsed and can be opened without flooding the viewport.
Long review forms on the **right** — especially thesis chapter blocks expanded
from `templates:` / `thesis_section` — still render as one long scroll of
Markdown headings plus textareas and buttons.

Add the same expand/collapse affordance for **logical sections of the review
form**: chapter (or subsection) groups should be closed by default (or only
the first open), with a clear summary label, so reviewers can jump to the
chapter they are working on without scrolling through every other chapter’s
widgets.

This is primarily about the **assess form** (right column), not the document
viewer. Optionally extend the same pattern later to long `viewer:` Markdown
blocks that use `##` / `###` headings.

## Acceptance Criteria

- [x] Review-form sections that correspond to chapter / major heading groups
      can be collapsed and expanded in the web UI (native `<details>` /
      `<summary>` or equivalent).
- [x] Default presentation reduces scrolling pain: sections start **closed**,
      or at most one section starts open (document the choice).
- [x] Expanding a section reveals that section’s widgets (textareas, buttons,
      checkboxes, etc.); collapsing hides them without losing entered values
      still held in the form / HTMX state.
- [x] Open/closed state survives HTMX record / panel swaps in the same way PDF
      `<details.pdf-entry>` state is restored (`data-*-key` + existing
      `base.html` pattern), or an equally robust approach.
- [x] Works for template-instantiated chapter blocks (the common thesis
      case) without requiring authors to rewrite every field by hand.
- [x] Keyboard / accessibility: summary is focusable; collapsed content is
      not in the tab order while closed (native `<details>` satisfies this).
- [x] Single-column / narrow layouts remain usable.
- [x] Tests cover the HTML structure for at least one multi-section form
      (collapsed wrappers + summary labels).

## Implementation Notes

### Suggested approach (prefer this order)

1. **Reuse the PDF pattern**  
   Left pane already emits:
   ```html
   <details class="pdf-entry" data-doc-key="…">
     <summary>Label</summary>
     …
   </details>
   ```
   and `base.html` restores open/closed state across HTMX swaps. Mirror that
   for the form with e.g. `class="review-section"` and
   `data-section-key="…"`.

2. **Group widgets at render time (`render_form`)**  
   Today `render_form` concatenates `render_widget` output for the flat
   expanded spec list. After template expansion, chapter blocks typically
   start with a Markdown widget whose liquid is a heading
   (`### %section_name%` → `### Chapter 1`).  
   **Heuristic:** treat a Markdown (or Criterion) widget whose rendered /
   source text is a single `##` / `###` heading as a **section boundary**.
   Wrap that heading’s text as `<summary>` and nest following widgets until
   the next boundary (or end of form) inside `<details>`.  
   Skip wrapping for top-of-form chrome (Save is in the nav bar already) and
   for widgets that are not under a heading.

3. **Config opt-in / override (aligns with template-driven composition)**  
   Heuristics alone may misfire on short forms. Prefer an explicit hook when
   easy, for example:
   - on template instances: `collapsible: true` / `section: "Chapter 1"`, or
   - a small `type: Section` / `type: Details` wrapper in the pattern that
     expands to a details boundary during template instantiation.  
   Default for long template-expanded lists can still be “collapse by
   heading” so existing thesis configs benefit without edits.

4. **Styling**  
   Match `.pdf-entry summary` affordance (pointer, weight) under
   `.review-section` so the right pane feels consistent with the left.
   Ensure nested form controls keep existing spacing.

5. **Out of scope for the first cut (follow-ons)**  
   - Collapsing arbitrary Markdown *inside* a single viewer HTML blob by
     rewriting `h2`/`h3` after `markdown2html` (useful, but separate).  
   - Remembering which section was open **per record index** (nice later;
     global or per-config key is enough initially).  
   - Jupyter widget UI (web-only unless a shared abstraction appears).

### Risks

- OOB HTMX swaps target `#widget-…` ids **inside** closed `<details>`; that
  should still update the DOM. Confirm Populate / field refresh still works
  when the section is closed, and that opening afterward shows new values.
- `visible_if` sections that are `display:none` should not leave empty
  open details chrome; skip empty groups or keep the existing hide behaviour
  on the inner widgets.

## Related

- CIP: 000B
- Prior art: `referia/web/render.py` (`render_document_panel` PDF `<details>`),
  `referia/web/templates/base.html` (PDF open-state restore),
  backlog `2026-10-07_web-resizable-document-review-split`
- Documentation: none yet (compress into web UI notes when CIP-000B closes)

## Progress Updates

### 2026-10-09

Task created (Proposed) after thesis introduction review: Create/download
works, but long chapter blocks on the right remain painful to scroll;
PDFs on the left already collapse.

Implemented in `render_form`: heading-only `##`/`###` Markdown (and
Criterion) widgets open `<details class="review-section">` groups; explicit
`section: "Title"` also works. Open state persisted via
`referia.reviewSection.open` in `base.html`. Verified against
`theses/examined/introduction` (24 sections including Chapter 1–12).
Status → Completed.

### 2026-10-09 (follow-up)

Heuristic over-collapses non-chapter headings. Superseding approach:
**explicit declaration only**, with declared title replacing the Markdown
Chapter header — see
`2026-10-09_web-explicit-collapsible-sections`.
