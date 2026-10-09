---
id: "2026-10-09_web-explicit-collapsible-sections"
title: "Web UI: explicit collapsible sections only (no heading heuristic)"
status: "Proposed"
priority: "High"
created: "2026-10-09"
last_updated: "2026-10-09"
category: "features"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-10-09_web-collapsible-review-sections"
tags:
- backlog
- web
- ui
- htmx
- templates
- sections
---

# Task: Explicit collapsible review sections (replace heuristic)

> Backlog tasks are DOING the work defined in CIPs (HOW).
> Linked CIP: 000B (web display).
> Follows: `2026-10-09_web-collapsible-review-sections` (shipped heuristic).

## Description

The first cut of collapsible review sections (`render_form` grouping on
heading-only `##` / `###` Markdown) guesses section boundaries. In practice
that collapses widgets that do **not** belong in a chapter block — any lone
heading becomes a `<details>` wrapper, including front-matter / misc
Markdown that should stay open in the flow.

**Change of approach:** only create collapsible groups when the config
**expressly declares** a section. Do not infer sections from Markdown
heading text.

The declaration should also **replace** today’s pattern of a separate
Markdown heading widget (e.g. `liquid: "### Chapter 1"` / `### %section_name%`
at the start of `thesis_section`). The section title belongs in the
`<summary>` (and optionally as accessible heading semantics), not as a
duplicate visible `###` above the folded body.

## Acceptance Criteria

- [ ] Heading-only Markdown / Criterion heuristics are **removed** (or
      permanently disabled). No auto-wrapping from `##` / `###` alone.
- [ ] An explicit config mechanism declares a collapsible section with a
      title (see Implementation Notes). Undeclared widgets render flat as
      before CIP-000B collapsible work.
- [ ] Declared section title appears as the `<summary>` label and **replaces**
      the need for a leading Markdown “Chapter N” header widget in the
      pattern.
- [ ] Sections remain closed by default; open/closed still persists across
      HTMX swaps (`data-section-key` / sessionStorage), matching PDF entries.
- [ ] Thesis (and similar) configs can opt in via template / instance fields
      without rewriting every field by hand — e.g. `thesis_section` starts
      with an explicit section marker using `%section_name%` / `title`.
- [ ] Tests: explicit declaration wraps following widgets; bare `### Heading`
      Markdown does **not** open a details group; summary text equals the
      declared title.

## Implementation Notes

### Suggested declaration shapes (pick one; keep it declarative)

**A. Dedicated widget (clearest)**

```yaml
- type: Section
  title: "%section_name%"   # or liquid / display
  # optional: open: false
```

`Section` is a boundary marker: starts a new `<details class="review-section">`
with `<summary>` = resolved title. Body is subsequent widgets until the next
`Section` (or end of form). No inner Markdown heading required.

**B. Flag on the first real widget of the group**

```yaml
- type: Textarea
  field: "%prefix%Summary"
  section: "%section_name%"   # non-empty string ⇒ start group; title from value
```

Already partially supported as `section: "Title"` but today coexists with the
heading heuristic — remove the heuristic and document `section:` as the
supported API (or prefer A so the title isn’t tied to a field widget).

**C. Template-instance key**

```yaml
- template: thesis_section
  instances:
    - title: "Chapter 1"
      section: true          # or collapsible: true
      section_name: "Chapter 1"
```

Expansion injects a `Section` (or `section:`) boundary from `title` /
`section_name`. Nice for “define once, instantiate many”; can compose with A.

**Recommendation:** implement **A** as the web render contract, and wire
`thesis_section` (C) so instances emit that marker instead of

```yaml
- type: Markdown
  liquid: "### %section_name%"
```

### Migration

1. Strip heuristic from `_section_boundary` / `render_form`.
2. Update `theses/*/introduction` (and drafts) `thesis_section` pattern to
   use explicit `Section` (or equivalent).
3. Leave unrelated Markdown headings as ordinary widgets.
4. Mark prior task’s heuristic as superseded in its progress notes.

### Out of scope

- Auto-collapsing `viewer:` Markdown by rewriting `h2`/`h3` in HTML.
- Jupyter widget parity (web-first unless a shared pattern appears).

## Related

- CIP: 000B
- Prior: `backlog/features/2026-10-09_web-collapsible-review-sections.md`
- Code: `referia/web/render.py` (`_section_boundary`, `render_form`),
  `base.html` (review-section open-state), `.review-section` in `style.css`
- Example configs: `theses/examined/introduction/_referia.yml` (`thesis_section`)

## Progress Updates

### 2026-10-09

Proposed after live review: heading heuristic collapses non-chapter blocks;
user wants express declaration only, with the declared title replacing the
current Chapter header Markdown.
