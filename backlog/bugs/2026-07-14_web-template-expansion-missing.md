---
id: "2026-07-14_web-template-expansion-missing"
title: "Web interface does not expand templates: section entries"
status: "Proposed"
priority: "High"
created: "2026-07-14"
last_updated: "2026-07-14"
related_cips: []
tags: ["web", "templates", "rendering"]
---

# Task: Web interface does not expand `templates:` section entries

## Description

When a `_referia.yml` uses a `templates:` section to define reusable widget
patterns, the web interface silently ignores those patterns and renders nothing
for the corresponding `review:` entries.

There are two syntactic forms for instantiating a template, and both are broken:

### Form A — `type:` matching a template name

```yaml
templates:
  CriterionComment:
    - type: Markdown
      ...
    - type: Textarea
      ...

review:
- type: CriterionComment   # should expand the template above
  field: criterion_1
  args:
    label: "Criterion 1"
```

`_flatten_entries` in `WebReviewer` receives `{"type": "CriterionComment", ...}`.
Because `"CriterionComment"` is not in `_CLUSTER_TYPES` and is not a known
built-in widget type, it is passed directly to `render_form`, which doesn't know
how to render it and produces nothing.

### Form B — `template:` key reference

```yaml
review:
- template: simple_section   # should expand templates.simple_section
  args:
    field: references
    label: "References"
```

`_flatten_entries` receives `{"template": "simple_section", ...}`.  It has no
`"type"` key, so `entry_type` is `""`, which is not in `_CLUSTER_TYPES`, so the
entry is appended as-is — again producing nothing visible in the web UI.

## Observed behaviour

Running the thesis assessment config (`examined/introduction/_referia.yml`) in
the web interface shows only the top-level `viewer:` block (e.g. title/date
header).  None of the `review:` widgets appear — all of them are either
`type: CriterionComment` (Form A) or `template: simple_section` (Form B)
instantiations.

## Root cause

`WebReviewer._flatten_entries` does not read the `templates:` section of the
interface config.  It has no logic to:

1. Detect that a `type:` value refers to a user-defined template (rather than a
   built-in widget type).
2. Look up the template definition in `self._interface.get("templates", {})`.
3. Substitute the template's widget list, merging in the call-site `args`.
4. Detect and handle the `template:` key (Form B) as an alternative invocation
   syntax.

The Jupyter path handles template expansion at a different layer (inside
`lynguine`/`referia`'s config/interface machinery), so it works correctly there.
The web interface bypasses that machinery and needs to implement equivalent
expansion itself.

## Acceptance Criteria

- [ ] `type: CriterionComment` entries in `review:` expand to the widgets
      defined in `templates.CriterionComment`, with `args` substituted where
      referenced.
- [ ] `template: simple_section` entries expand to the widgets defined in
      `templates.simple_section`, with `args` substituted.
- [ ] Expanded widgets appear correctly in the web review form.
- [ ] Unknown `type:` values (not built-in, not in `templates:`) produce a
      visible warning widget rather than silent omission.
- [ ] Tests cover both Form A and Form B expansion in `WebReviewer`.

## Implementation Notes

- `WebReviewer._flatten_entries` is the right place to add expansion; it already
  handles recursive cluster flattening.
- The `templates:` dict is available via `self._interface.get("templates", {})`.
- Template `args` substitution may need to resolve Liquid-style placeholders
  (e.g. `{label}`) in field names and widget properties — scope to be confirmed
  by inspecting how the Jupyter path handles it.
- Consider: what happens when a template references another template (circular
  reference guard needed).

## Related

- Tenet: template-driven-composition
- Tenet: progressive-augmentation
