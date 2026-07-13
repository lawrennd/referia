---
id: "2026-07-13_web-document-serving"
title: "Web display system: document serving and system integration"
status: "Proposed"
priority: "Medium"
created: "2026-07-13"
last_updated: "2026-07-13"
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
---

# Task: Web display system: document serving and system integration

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Adapt `Sys` document operations for the web context: serve PDFs in-browser,
expose download links for generated Word documents, and handle URL opening.
The goal is feature parity with the Jupyter `Sys.view_series()` workflow.

## Acceptance Criteria

- [ ] `GET /document/{path:path}` serves a file from the review directory with the correct MIME type
- [ ] PDFs are embedded in the review page via `<iframe src="/document/...">` or an `<object>` tag alongside the review form
- [ ] `urls:` entries from `_referia.yml` are rendered as `<a href="..." target="_blank">` links in the viewer panel
- [ ] `POST /generate-document` triggers Word document generation and returns a download link
- [ ] `POST /edit-pdf` triggers PDF page extraction and returns a download link for the extracted file
- [ ] File paths are validated to prevent directory traversal (serve only files within the configured review directory)
- [ ] The document panel updates when the index changes (HTMX swap)

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

Word and PDF generation remain server-side via the existing `Sys` methods;
the route returns a `FileResponse` or a download URL fragment that HTMX
inserts into the page.

## Related

- CIP: 000B
- PRs: 
- Documentation: 

## Progress Updates

### 2026-07-13

Task created following acceptance of CIP-000B.
