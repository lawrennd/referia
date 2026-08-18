---
id: "2026-08-18_cip000E-xss-verification"
title: "Resolve or document CodeQL reflected XSS alert #12"
status: "Completed"
priority: "Medium"
created: "2026-08-18"
last_updated: "2026-08-18"
category: "infrastructure"
related_cips: ["000E"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- security
- codeql
- web
- xss
- cip000E
---

# Task: Resolve or document CodeQL reflected XSS alert #12

## Description

CodeQL `py/reflective-xss` alert **#12** flags `_render_directory_listing` (~line 925) in
`referia/web/routes.py`. The `label` in the heading is built as `f"/{_esc(breadcrumb)}"`, so the
value is already HTML-escaped. CodeQL likely does not model `_esc()` as a sanitizer.

Also review `href="{inh_url}"` (~831): those URLs are filesystem-derived, not raw query input.

## Acceptance Criteria

- [x] Audit confirms no unescaped user/query input reaches the listing HTML
- [x] Either refactor so `html.escape` is visible at the sink, or add a documented CodeQL
      suppression citing escape at source
- [x] Inherit-link `href` values reviewed (escape or constrain as needed)
- [ ] Alert #12 closed or dismissed with rationale recorded here and in CIP-000E

## Implementation Notes

Prefer making the sanitizer obvious to CodeQL (`html.escape` at the f-string sink) over a
suppression. Can land with the exception-exposure or path-safety change if they already touch this
function; keep this task so the alert is not forgotten.

## Related

- CIP: [CIP-000E](../../cip/cip000E.md)
- Code: `referia/web/routes.py` (`_render_directory_listing`)

## Progress Updates

### 2026-08-18

Task created when CIP-000E was Accepted.

Listing sinks now call `html.escape(..., quote=True)` on `href` values (entry URLs, group
headings, parent link, inherit links) and `html.escape(breadcrumb)` for the heading label.
Do not name the page body `html` in `_render_directory_listing` — that shadows the stdlib
module. Alert #12 should close on the next CodeQL scan.
