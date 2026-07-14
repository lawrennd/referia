---
id: "2026-07-14_web-documents-not-rendered"
title: "Web interface does not render or execute documents section (email, letter, docx)"
status: "Proposed"
priority: "Medium"
created: "2026-07-14"
last_updated: "2026-07-14"
related_cips: []
tags: ["web", "documents", "email", "docx", "letter", "generation"]
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
   - **letter** — run the LaTeX pipeline and open or save the resulting PDF.
   - **docx** — render the Markdown via Pandoc/python-docx and save the file.
3. Report success or failure in the status bar.

## Implementation Notes

### Scope of work

This is non-trivial. The Jupyter implementation uses a mix of `subprocess`, COM
automation (Outlook on Windows/Mac), and file-system operations that run locally on
the reviewer's machine. In the web context the server is local (same machine), so the
same approaches are feasible, but the trigger path is different.

Suggested phased approach:

**Phase 1 — Render buttons** (low risk):
- Extend `WebReviewer.get_widget_specs()` (or add `get_document_specs()`) to expose
  the `documents:` list.
- Add a new route `POST /document/{index}` that accepts a document spec index.
- Render one `<button>` per document spec in the review panel, using HTMX to POST to
  the route.

**Phase 2 — Execute generation**:
- For `type: docx` / `type: letter`: call existing `referia` generation helpers
  server-side (same process, same filesystem); return file path in status bar.
- For `type: email`: call existing `Message` / Outlook helpers on the server process;
  this works because server and browser run on the same Mac.

### Key unknowns

- Whether the Liquid evaluation for document specs can reuse `view_to_value()` /
  `viewer_to_value()` or needs a dedicated document-rendering path.
- Whether multi-step documents (LaTeX compile → open PDF) can be made async without
  blocking the HTMX response.
- Cross-platform portability (email via Outlook COM vs. `mailto:` vs. SMTP).

## Related

- Feature: `2026-07-14_web-subseries-selector.md`
- Config example: `people/letters/_referia.yml` (defines all three document types).

## Progress Updates

### 2026-07-14
Backlog item created. No implementation started. Buttons are entirely absent from
the web interface; the `documents:` section is silently ignored.
