---
id: "2026-10-07_web-record-document-index-in-url"
title: "Web PDF iframe URL must include the active record index"
status: "Completed"
priority: "High"
created: "2026-10-07"
last_updated: "2026-10-07"
category: "bugs"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-10-06_web-index-query-string-type"
tags:
- backlog
- web
- editpdf
- localpdf
- index
- htmx
---

# Task: Put the active index in `/record-document` iframe URLs

> Backlog tasks are DOING the work defined in CIPs (HOW).
> Linked CIP: 000B (web display). Depends on typed index coercion for numeric
> labels (`2026-10-06_web-index-query-string-type`, Completed).

## Description

The document panel embeds `localpdf` / `editpdf` files in an `<iframe>` whose
`src` is:

```text
{prefix}/record-document/{kind}/{n}
```

There is **no record index** in that URL. Serving resolves the file from
`WebReviewer.get_index()` at request time (`get_value` on the configured
`field`, e.g. `ProposalFilename`).

That is wrong for a shareable, per-record document URL:

1. Switching records via HTMX rebuilds the panel, but every record still
   requests the **same** document URL. Reviewers cannot tell which index the
   iframe is for, and the browser has no distinct resource identity per row.
2. Seen on
   `applications/2026-10-06_ai-cam_ai-for-teaching/preliminary`: after
   converting proposals to PDF and updating `ProposalFilename` to `01.pdf`
   etc., the viewer still behaved as if it were fetching the old `01.docx`
   for the control. Server-side `set_index` + `get_record_document` do follow
   the active index on a fresh load; the missing index in the iframe `src` is
   the proper product fix so each record has a distinct document URL.

Numeric allocation labels (e.g. `Project number` = `2`) must use the same
string→typed label coercion as `GET /record?index=` so
`/record-document/…?index=2` selects label `2`, not a positional offset.

## Acceptance Criteria

- [x] Document panel iframe (and “Open in a new tab”) URLs include the active
      record index (query param or path segment — pick one and document it).
- [x] `GET …/record-document/{kind}/{n}?index=<label>` (or equivalent) sets
      that index before resolving the file, using the same coercion as
      `WebReviewer.set_index` / `_apply_index`.
- [x] Changing the index selector yields a **different** document URL when
      the underlying file differs; the correct PDF for that row is served.
- [x] Missing / unknown index returns 404 (same policy as `/record`).
- [x] Root-server and single-config routes both behave correctly.
- [x] Unit tests cover string labels, numeric labels (`"2"` → int `2`), and
      missing index.

## Implementation Notes

Likely touch points:

1. `referia/web/render.py` — `render_document_panel`: add current index to
   `src` / open-link href (pass `current_index` into the helper from
   `_panel_response_context`).
2. `referia/web/routes.py` — `_serve_record_document` and both
   `record-document` handlers: accept `index`, call `_apply_index` before
   `get_record_document`.
3. Prefer `?index=` for consistency with `GET /record?index=` (CIP-000C
   shareable URLs). Do **not** invent a second positional meaning for bare
   integers.
4. Optional hardening (not required for acceptance): `Cache-Control:
   no-store` on document responses so stale bodies cannot linger if a URL
   is reused during development.

Do not change lynguine; keep HTTP string coercion in referia’s web layer.

## Related

- CIP: 000B
- CIP: 000C (shareable `?index=` URLs)
- Task: `2026-10-06_web-index-query-string-type` (coerce numeric query strings)
- Config: `applications/2026-10-06_ai-cam_ai-for-teaching/preliminary`
  (`editpdf` + `ProposalFilename`)

## Progress Updates

### 2026-10-07

Bug diagnosed while reviewing ai@cam teaching proposals in the web UI.
Backlog created; not yet implemented.

Implemented: `render_document_panel` adds `?index=`; `/record-document`
handlers call `_apply_index` before resolve. Tests in `test_web_render.py`
and `test_web_routes.py`.
