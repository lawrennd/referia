---
id: 2026-07-14_web-local-app-launchers-unsupported
title: Web interface cannot support local app launchers (editpdf, urls, editdocx)
status: Ready
priority: Low
created: '2026-07-14'
last_updated: '2026-10-09'
related_cips:
- '000B'
tags:
- web
- editpdf
- urls
- local-apps
- architecture
- limitation
owner: lawrennd
category: bugs
---

# Feature/Limitation: Local App Launchers Not Supported in Web Interface

## Description

Several `_referia.yml` keys trigger local application launches during a Jupyter review
session:

| Key | Jupyter behaviour |
|---|---|
| `editpdf` | Copies a PDF (optionally clipping a page range) and opens it in Preview / Acrobat. |
| `urls` | Opens one or more URLs in the default browser. |
| `editdocx` | Opens a Word document in the system Word installation. |
| `editmd` | Opens a Markdown file in the configured editor. |

These all work in Jupyter because the Python kernel runs on the reviewer's local
machine and can call `subprocess`, `os.open`, or `webbrowser.open` directly.

In the web interface the server is also local, so the *process* model is the same —
but the *trigger* model is different. There is no equivalent of a Jupyter widget
button that fires Python code. Additionally, for remote deployments (if ever
considered) these actions would not be possible at all.

## Current State (2026-10-09)

Partially superseded by CIP-000B web document serving:

| Key | Web status |
|---|---|
| `urls` | **Done** — rendered as `<a target="_blank">` links |
| `localpdf` / viewing `editpdf` paths | **Done** — embedded in document-panel iframes |
| `editpdf` page extraction → download | **Open** — tracked under `2026-07-13_web-document-serving` (`POST /edit-pdf`) |
| `editdocx` / `editmd` open-in-app | **Deferred** — no demand yet; Jupyter-only is acceptable |

Narrow remaining scope of *this* item to anything not covered by document-serving
generation routes (mainly optional server-side `open` for extracted PDFs). Prefer
download links over `subprocess open` for web-native behaviour.

## Strategy (resolved for common cases)

1. ~~Render viewer pane links for URLs~~ — **done**.
2. ~~Embed PDFs in the document panel~~ — **done**.
3. Generation / extraction downloads — **in progress** via
   `2026-07-13_web-document-serving`.
4. Server-side `open` for local apps — optional, local-only; defer unless a
   workflow needs it after downloads exist.
5. `editdocx` / `editmd` — out of scope for web until demanded.

## Related

- CIP: 000B
- Feature: `2026-07-13_web-document-serving.md` — owns `POST /edit-pdf` and
  generation downloads.
- Bug: `2026-07-14_web-documents-not-rendered.md` — `documents:` section
  generation (docx / letter / email).
- Tenet: document-centric-management

## Progress Updates

### 2026-07-14
Backlog item created to record the limitation and capture strategy options.
No implementation started. The gap was noticed while testing
`people/letters/_referia.yml` which uses `editpdf` extensively.

### 2026-10-09
Triaged against CIP-000B progress. URLs and PDF viewing are done. Remaining
extraction/generation work lives on `web-document-serving`; this item kept as
Low/Ready for any leftover local-`open` decisions. Linked to CIP-000B.
