---
id: "2026-08-19_web-mathjax-typesetting"
title: "Web display: typeset LaTeX in Markdown and HTMLMath widgets"
status: "In Progress"
priority: "High"
created: "2026-08-19"
last_updated: "2026-08-19"
category: "features"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: ["2026-07-13_web-routes-and-templates"]
tags:
- backlog
- web
- mathjax
- markdown
- htmlmath
---

# Task: Web display: typeset LaTeX in Markdown and HTMLMath widgets

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Jupyter Markdown widgets are `ipywidgets.HTMLMath`, so `$...$` and `$$...$$` in `_referia.yml` content typeset in the notebook. The web backend converts Markdown to HTML with `markdown.markdown()` and serves it with no typesetter. Reviewers see raw TeX, for example Queens 2021 question 3:

```
vertices $(0, 0)$, $(0, 1)$, $(1, 1)$, $(1, 0)$ and the line $y=x+c$ … area $A(c)$
```

Questions 1 and 2 in the same config use the same delimiters (`$\frac{2}{3}$`, `$9$`, `$\angle RPQ$`). A commented `HTMLMath` widget in that file also assumes MathJax. `referia/web/render.py` already maps widget type `HTMLMath` to `_render_html`, but `base.html` never loads MathJax or KaTeX.

This is Jupyter-parity for CIP-000B, not a new widget type. Configs should keep using `$...$`; the page should typeset them.

## Acceptance Criteria

- [ ] Review Markdown widgets typeset inline `$...$` and display `$$...$$` (same delimiters as Jupyter HTMLMath)
- [ ] `HTMLMath` widgets typeset as well as Markdown
- [ ] Typesetting runs on first page load and after HTMX swaps (index change, Reload) so swapped fragments are not left as raw TeX
- [ ] Queens 2021 undergrad admissions question text is readable as maths without editing `_referia.yml`
- [ ] Offline/CDN choice is documented (same issue as the existing HTMX unpkg TODO)
- [ ] A test asserts the review page shell includes a typesetter (script tag or equivalent), so the page cannot silently drop maths again

## Implementation Notes

Preferred approach: MathJax 3 in `referia/web/templates/base.html`, configured like Jupyter:

- inline: `$...$` and `\(...\)`
- display: `$$...$$` and `\[...\]`

After HTMX settles, call `MathJax.typesetPromise()` on the swapped root (or the document) so Reload and record navigation re-typeset. Existing `htmx:afterSettle` listeners in `base.html` are the right hook.

KaTeX is smaller and faster, but MathJax matches Jupyter `HTMLMath` more closely. Prefer MathJax unless there is a strong reason to diverge.

Do not special-case question 3. Load the typesetter once for the review page.

Python-markdown can turn `_` into `<em>` inside TeX. If that shows up, handle it in rendering (math-aware markdown or a post-pass), not by rewriting application configs.

CDN vs vendoring: HTMX is still loaded from unpkg with a TODO to vendor for offline use. Follow the same pattern; do not block this task on vendoring both libraries.

## Related

- CIP: 000B
- Config that surfaced this: `applications/2021-12-06_queens_undergrad-admissions/_referia.yml` (`q3Question`, also q1/q2)
- Jupyter path: `referia/util/widgets.py` — Markdown uses `ipyw.HTMLMath`
- Web path: `referia/web/templates/base.html`, `referia/web/render.py` (`_render_markdown_widget`, `_render_html` / `HTMLMath`)

## Progress Updates

### 2026-08-19

Task created after web review of Queens 2021 undergrad admissions: question 3 (and other questions) assumed MathJax that the browser page does not load.

### 2026-08-19 (accepted)

Status moved to In Progress. Implementing MathJax on the review page shell.
