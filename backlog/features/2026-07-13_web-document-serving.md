---
id: "2026-07-13_web-document-serving"
title: "Web display system: document serving and system integration"
status: "In Progress"
priority: "Medium"
created: "2026-07-13"
last_updated: "2026-10-09"
category: "features"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: ["2026-07-13_web-routes-and-templates"]
tags:
- backlog
- web
- documents
- pdf
- system
- generation
---

# Task: Web display system: document serving and system integration

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Adapt `Sys` document operations for the web context: serve PDFs in-browser,
handle URL opening, and trigger generation of `_referia.yml` `documents:`
artefacts (docx, letter, email, and related types) with download or status
feedback. The goal is feature parity with the Jupyter document workflow for
local `referia serve`.

Serving and viewing are largely done. Remaining work is **generation actions**.

## Acceptance Criteria

### Done — serving and viewing

- [x] `GET /document/{path:path}` serves a file from the review directory with the correct MIME type
- [x] PDFs are embedded in the review page via `<iframe src="/document/...">` or an `<object>` tag alongside the review form
- [x] `urls:` entries from `_referia.yml` are rendered as `<a href="..." target="_blank">` links in the viewer panel
- [x] File paths are validated to prevent directory traversal (serve only files within the configured review directory)
- [x] The document panel updates when the index changes (HTMX swap)

### Open — generation (covers bug `2026-07-14_web-documents-not-rendered`)

- [ ] `WebReviewer` (or equivalent) exposes `documents:` / `summary_documents:` specs to the renderer
- [ ] Review panel renders one action button per document spec
- [ ] `POST /generate-document` (or equivalent) runs generation for the chosen spec against the current index
- [ ] `type: docx` / `type: letter` / `type: markdown` reuse `Reviewer.create_document` → `Sys.create_document` and return a download link or status fragment
- [ ] `type: email` creates a draft via existing helpers (same-machine) or a usable `mailto:` fallback, with status feedback
- [ ] `POST /edit-pdf` triggers PDF page extraction and returns a download link for the extracted file
- [ ] Failures surface clearly in the status bar without crashing the review page

## Implementation Notes

`Sys.view_urls()` builds URL strings from `view_to_value`; the web backend
renders these as anchor tags rather than calling `webbrowser.open()`.

PDF serving: use `fastapi.responses.FileResponse` with `media_type="application/pdf"`.

Security: resolve the requested path against the configured review directory root
and reject any path that escapes it:

```python
resolved = (root / path).resolve()
if not resolved.is_relative_to(root.resolve()):
    raise HTTPException(403)
```

Generation remains server-side via existing `Sys` / `Reviewer.create_document`
methods. Prefer returning a download URL fragment that HTMX inserts into the
page over silently calling `open_localfile` (browser download is the web-native
analogue of Jupyter opening the file).

Do **not** create a separate CIP for this slice; it is remaining CIP-000B scope.

## Related

- CIP: 000B
- Bug (user-visible gap): `2026-07-14_web-documents-not-rendered.md`
- Related: `2026-07-14_web-local-app-launchers-unsupported.md`
- Config example: `people/letters/_referia.yml`

## Progress Updates

### 2026-07-13

Task created following acceptance of CIP-000B.

### 2026-10-06

Started implementation: `GET /document/{path}` and `GET /record-document/{kind}/{n}`
serve files; the review panel embeds declared `localpdf`/`editpdf` PDFs in lazy
iframes and renders `urls:` as links. Generate-document and edit-pdf download
routes remain open.

### 2026-10-09

Expanded remaining AC to cover full `documents:` parity (docx, letter, email),
not only Word. Linked bug `2026-07-14_web-documents-not-rendered` as the
user-visible tracker for this open work. Confirmed: implement under CIP-000B,
not as a new CIP or a one-line quick fix.
