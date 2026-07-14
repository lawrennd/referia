---
id: "2026-07-14_web-local-app-launchers-unsupported"
title: "Web interface cannot support local app launchers (editpdf, urls, editdocx)"
status: "Proposed"
priority: "Low"
created: "2026-07-14"
last_updated: "2026-07-14"
related_cips: []
tags: ["web", "editpdf", "urls", "local-apps", "architecture", "limitation"]
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

## Current State

None of these launchers are rendered as buttons or executed in the web interface.
The corresponding configuration sections are silently ignored.

## Strategy Options (for future discussion)

No implementation decision has been made. Options to evaluate:

1. **Render buttons, execute server-side (local-only).**  
   Add `POST /launch/{action}` routes. Since server and browser are on the same Mac,
   `subprocess.Popen(["open", path])` works and opens the app on the reviewer's
   desktop. Simple, works for single-user local deployment.  
   *Risk*: would break if the server is ever run on a remote machine.

2. **Render viewer pane links for URLs.**  
   For `urls:` specifically, the web interface could render the URLs as `<a
   href="..." target="_blank">` links in the viewer panel, which the browser opens
   natively without server involvement. Low risk, high value for the common case.

3. **Render info-only placeholders.**  
   Display a read-only block listing the PDF path / URL so the reviewer can open it
   manually. No automation, but surfaces the information.

4. **Mark as out-of-scope for web interface.**  
   Accept that the web interface is a review/annotation tool and that local app
   launching remains a Jupyter-only capability. Document the limitation explicitly.

## Recommended First Step

Implement option 2 (URL links) as an easy win, and option 1 (server-side `open`) for
`editpdf` since it is the most commonly used launcher in thesis review workflows.
Defer `editdocx` / `editmd` until there is demand.

## Related

- Bug: `2026-07-14_web-documents-not-rendered.md` — `documents:` section also
  unimplemented; shares some of the same "server-side action" infrastructure needs.
- Tenet: document-centric-management — referia is designed around side-by-side
  document viewing and annotation; this limitation is architecturally significant.

## Progress Updates

### 2026-07-14
Backlog item created to record the limitation and capture strategy options.
No implementation started. The gap was noticed while testing
`people/letters/_referia.yml` which uses `editpdf` extensively.
