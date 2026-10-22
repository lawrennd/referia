---
id: "2026-10-22_web-editpdf-serves-source-until-prepare"
title: "Web editpdf iframe serves the full source PDF instead of pdftk page ranges"
status: "Proposed"
priority: "High"
created: "2026-10-22"
last_updated: "2026-10-22"
category: "bugs"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: ["2026-07-13_web-document-serving"]
tags:
- backlog
- web
- documents
- pdf
- editpdf
- pdftk
---

# Bug: Web `editpdf` view does not extract first–last pages with pdftk

> Backlog tasks are DOING the work defined in CIPs (HOW).
> Linked CIP: 000B (web display). Related: `2026-07-13_web-document-serving`.

## Description

Jupyter `edit_files` / `Sys.copy_file` already extract page ranges with
`pypdftk.get_pages` (`pdftk`) when an `editpdf` entry has

```yaml
pages:
  first: ApplicationFirstPage
  last: ApplicationLastPage
```

The web path does not. `WebReviewer.get_record_document` →
`_resolve_editpdf_file` returns the **annotated copy if it already exists**,
otherwise the **full source PDF**. Extraction only happens in
`ensure_edit_pdf`, which is wired to the "Prepare / download PDF" button
(`POST /edit-pdf/{n}`).

Observed on
`applications/2026-10-19_ai-cam_programme-manager/interview-selection/`:
`pdfpages.xlsx` has first/last pages for application, CV, and cover letter;
`pdftk` is installed; `../pdfs/` is empty; the iframe shows the whole
application PDF until Prepare is clicked (once per document, per candidate).

This is not a missing `pdftk` in the config. The page-range copy is never
created on view.

## Acceptance Criteria

- [ ] Opening an `editpdf` document in the web UI extracts `pages.first`–
      `pages.last` into `storedirectory` via `Sys.copy_file` / `pdftk`
      (same as Jupyter), then serves that copy.
- [ ] If first/last are empty, behaviour stays "no extracted copy" (do not
      silently serve a zero-page file).
- [ ] Prepare still works and does not re-extract when a valid copy already
      exists.
- [ ] Unit tests cover: dest missing + pages set → extract; dest present →
      serve dest; pages empty → source PDF; relative `storedirectory`
      against the config directory.

## Implementation Notes

Call `ensure_edit_pdf(n)` from `get_record_document` when `kind == "editpdf"`
and the view has `pages`, instead of falling back to the source in
`_resolve_editpdf_file`. Keep the fallback for missing source files.

`ensure_edit_pdf` currently skips extraction when `dest.is_file()`. That is
correct once a page-range copy exists; it is wrong if an earlier run copied
the *full* PDF to dest. Consider comparing dest page count to first–last, or
always extracting when `pages` is set and dest is missing.

## Related

- CIP: 000B
- `referia/assess/web_review.py` `_resolve_editpdf_file`, `ensure_edit_pdf`
- `referia/system.py` `Sys.copy_file` (`tk.get_pages`)
- `referia/web/render.py` `render_document_panel`

## Progress Updates

### 2026-10-22

Task created after interview-selection showed full application PDFs despite
filled page ranges. Application-layer workaround: pre-extract into `pdfs/`
with `pdftk` for this review only.
