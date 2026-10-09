---
id: "2026-10-09_web-explicit-collapsible-sections"
title: "Web UI: explicit collapsible sections only (no heading heuristic)"
status: "Completed"
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

# Task: Explicit collapsible review sections (nested widget groups)

> Backlog tasks are DOING the work defined in CIPs (HOW).
> Linked CIP: 000B (web display).
> Follows: `2026-10-09_web-collapsible-review-sections` (shipped heuristic).

## Description

The first cut of collapsible review sections guessed boundaries from
heading-only `##` / `###` Markdown. That over-collapsed non-chapter blocks.

**Approach:** declare a section as a **nested widget group** (same idea as
Jupyter `type: group` / `GroupWidgetCluster`). Children are indented under
`entries:` so the YAML structure itself marks where the section ends — no
“everything until the next Section” scanning.

```yaml
- type: Section
  title: "%section_name%"
  entries:
    - type: Textarea
      field: "%prefix%Summary"
    - type: Checkbox
      field: "%prefix%SummaryIncludeHistory"
    # ... more widgets in this chapter
```

Web: each Section → `<details class="review-section">` with
`<summary>` = title. Jupyter: GroupWidgetCluster + Markdown heading from
title.

## Acceptance Criteria

- [x] Heading-only Markdown heuristics removed. Bare `### Heading` does not
      open a details group.
- [x] Explicit nested `type: Section` + `title` + `entries:` declares a
      collapsible group; siblings outside the indent stay in the open flow.
- [x] Declared title is the `<summary>` only (no duplicate heading widget).
- [x] Open/closed persists across HTMX swaps (`data-section-key` /
      sessionStorage).
- [x] `thesis_section` / `simple_section` templates nest chapter widgets
      under Section; drafts introduction regrouped the same way.
- [x] Tests cover nested entries, flat Markdown non-section, and
      `get_review_specs` preserving Section while `get_widget_specs` flattens.

## Implementation Notes

- `referia/web/render.py` — recursive `render_form` over Section.entries
- `referia/assess/web_review.py` — `_PRESERVE_CLUSTER_TYPES`; review specs
  keep Section nodes; widget specs flatten for field updates
- `referia/assess/review.py` — `extract_review` treats Section like group
- `referia/config/interface.py` — expand Section (`entries` or `children`)
- Accepts `children:` as a group-style alias → normalised to `entries`

## Related

- CIP: 000B
- Prior: `backlog/features/2026-10-09_web-collapsible-review-sections.md`
- Jupyter: `type: group` / `GroupWidgetCluster` in `review.py`
- Configs: `theses/examined/introduction/_referia.yml`,
  `theses/drafts/introduction/_referia.yml`

## Progress Updates

### 2026-10-09

Proposed after live review: heading heuristic collapses non-chapter blocks.

### 2026-10-09 (implemented)

First cut used a flat Section boundary marker. Revised to **nested
`entries:`** so section membership is structural (YAML indent / group
cluster), matching existing widget-grouping ideas.
