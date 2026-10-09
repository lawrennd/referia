---
id: 2026-07-14_web-documents-not-rendered
title: Web interface does not render or execute documents section (email, letter,
  docx)
status: Ready
priority: Medium
created: '2026-07-14'
last_updated: '2026-10-09'
related_cips:
- '000B'
tags:
- web
- documents
- email
- docx
- letter
- generation
owner: lawrennd
category: bugs
dependencies:
- 2026-07-13_web-document-serving
---

# Bug: Web Interface Does Not Render or Execute the `documents` Section

## Description

`_referia.yml` files can define a `documents:` section that specifies output artefacts
to generate from review data — most commonly:

- `type: email` — compose and open a draft email in Outlook (or similar) with
  Liquid-templated subject, To, body, etc.
- `type: letter` — generate a PDF letter via LaTeX.
- `type: docx` — generate a Word document from Liquid-templated Markdown content.

In the Jupyter interface these appear as action buttons (one per document spec).
Clicking a button evaluates the Liquid templates against the current record and
triggers the appropriate generation/delivery action.

In the web interface the `documents:` section is **not processed at all**: no buttons
are rendered and no generation routes exist.

## Observed Behaviour

`people/letters/_referia.yml` defines three document specs (`email`, `letter`, `docx`).
None of these produce any visible button or route in the web interface.

## Expected Behaviour

Each document spec should produce an action button in the review panel. Clicking it
should:

1. Evaluate all Liquid templates in the spec against the current record's data.
2. Execute the appropriate generation action:
   - **email** — open a pre-filled draft in the system mail client (or return a
     `mailto:` URL / call the Outlook COM bridge as in Jupyter).
   - **letter** — run the LaTeX pipeline and return a download link for the PDF.
   - **docx** — render via existing `Sys.create_docx` and return a download link.
3. Report success or failure in the status bar.

## Implementation Notes

This is **not a standalone CIP**. CIP-000B already scoped server-side Word/PDF
generation with a download link on completion. Generation logic exists in
`Reviewer.create_document` → `Sys.create_document`; the web layer never calls it.

**Implement via** feature task `2026-07-13_web-document-serving` (expanded AC).
This bug tracks the user-visible gap; the feature task is the work vehicle.

Suggested phased approach:

**Phase 1 — Render buttons** (low risk):
- Expose `documents:` (and optionally `summary_documents:`) from `WebReviewer`.
- Render one `<button>` per document spec in the review panel.
- Add `POST /generate-document` (or `/document-action/{n}`) that accepts a
  document-spec index for the current record.

**Phase 2 — Execute generation**:
- Reuse `Reviewer.create_document` / `Sys.create_document` server-side.
- For `docx` / `letter` / `markdown`: return a download URL fragment for HTMX.
- For `email`: prefer same-machine draft helpers; fall back to `mailto:` if needed.

### Key unknowns

- Whether document Liquid evaluation can reuse the reviewer's `template_to_value`
  path from a `WebReviewer` (or needs a thin adapter onto `Reviewer`).
- Whether LaTeX letter compile can stay synchronous in the HTMX request.
- Email portability (Outlook / appscript vs `mailto:`).

## Related

- CIP: 000B
- Feature (implementation vehicle): `2026-07-13_web-document-serving.md`
- Related limitation: `2026-07-14_web-local-app-launchers-unsupported.md`
- Config example: `people/letters/_referia.yml` (defines all three document types).

## Progress Updates

### 2026-07-14
Backlog item created. No implementation started. Buttons are entirely absent from
the web interface; the `documents:` section is silently ignored.

### 2026-10-09
Triaged: not a quick fix, not a new CIP. Linked to CIP-000B and folded into
`2026-07-13_web-document-serving` as remaining acceptance criteria. Status → Ready.
