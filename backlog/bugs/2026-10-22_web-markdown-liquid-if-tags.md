---
id: "2026-10-22_web-markdown-liquid-if-tags"
title: "Web review Markdown only substitutes {{var}}; {% if %} tags appear raw"
status: "Completed"
priority: "High"
created: "2026-10-22"
last_updated: "2026-10-28"
category: "bugs"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- web
- liquid
- markdown
- widgets
---

# Bug: Review Markdown widgets do not run real Liquid tags

> Backlog tasks are DOING the work defined in CIPs (HOW).
> Linked CIP: 000B (web display). Viewer Liquid already uses lynguine
> `view_to_value` / python-liquid; review widgets do not.

## Description

`referia/web/render.py` `_evaluate_liquid` is a regex that only substitutes
`{{identifier}}` from the row dict. The docstring says more complex Liquid
is left as-is.

Review widgets such as

```yaml
- type: Markdown
  liquid: |
    {% if Priority == "Yes" %}**Priority candidate.**{% endif %}
    {{Email}}
```

therefore render the `{% if %}` / `{% endif %}` tags as visible text, while
`{{Email}}` is replaced. The same `{% if Priority == "Yes" %}` in `viewer:`
works, because `WebReviewer.render_viewer_html` calls
`self._data.view_to_value()`.

Observed on
`applications/2026-10-19_ai-cam_programme-manager/interview-selection/`
with `Priority` already in `input.mapping` (`Priority: Priority`).

Application workaround: `visible_if: {field: Priority, equals: "Yes"}` on a
static Markdown widget, which `_visibility_style` already understands.

## Acceptance Criteria

- [x] Review `type: Markdown` (and Criterion) `liquid:` templates are
      evaluated with python-liquid (LAX), same family as viewer.
- [x] `{% if column %}` / `{% if column == "Yes" %}` hides or shows the inner Markdown.
- [x] `{{column}}` substitution still works, including mapped names from
      `_name_column_map`.
- [x] Invalid Liquid raises a logged error and does not dump the raw template
      into the form.
- [x] Unit tests cover `{% if %}`, `{{var}}`, and a mapped alias.

## Implementation Notes

Replace `_evaluate_liquid` with a call through the reviewer data object, or
pass already-evaluated content from `WebReviewer` the way viewer HTML is
passed. Do not grow the regex. CIP-0016 demand-driven `mapping(names=…)`
already feeds python-liquid in lynguine; reuse that path.

## Related

- CIP: 000B
- `referia/web/render.py` `_evaluate_liquid`, `_markdown_widget_content`,
  `_render_criterion`
- `lynguine/assess/data.py` `liquid_to_value`

## Progress Updates

### 2026-10-22

Task created. Config workaround: `visible_if` on the priority banner in the
XN51107 review widgets; viewer `{% if %}` left as real Liquid.

### 2026-10-28

`_evaluate_liquid` now uses python-liquid. Observed on live MPhil ACS
interviews (Application Markdown dumping `{% if candidateEmail %}`).
Web `default:` string / `default.source` now copies the source column
(Interview Time) instead of writing the field name into Start.
