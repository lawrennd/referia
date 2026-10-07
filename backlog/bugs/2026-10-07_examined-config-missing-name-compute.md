---
id: "2026-10-07_examined-config-missing-name-compute"
title: "theses/examined/_referia.yml missing compute block for Name index"
status: "Proposed"
priority: "Low"
created: "2026-10-07"
last_updated: "2026-10-07"
category: "bugs"
related_cips: ["000A"]
owner: "lawrennd"
tags:
- backlog
- config
- theses
- examined
---

# Bug: theses/examined/_referia.yml missing compute block for Name index

## Description

`theses/examined/_referia.yml` uses `allocation: {index: Name}` but has no
`compute:` block to derive `Name` from `given`/`family`/`prefix`/`suffix`. 
Since `candidates.yml` (and the original `candidates.xlsx`) does not contain a 
`Name` column, the allocation falls back to positional integer indices (0–15), 
which then breaks `set_index` when the workflow tries to match against 
`series: chapter_comments.xlsx` using the `Chapter` selector.

Discovered during cip000A validation (2026-10-07). This bug predates the 
Excel→YAML conversion — the same failure occurs with `candidates.xlsx`.

## Acceptance Criteria

- [ ] `examined/_referia.yml` has a `compute:` block in `allocation:` that
      derives `Name` using the same `render_liquid` template as `pdfpages/_referia.yml`
- [ ] `WebReviewer("_referia.yml", examined_dir).set_index(name)` succeeds for
      at least one valid candidate name
- [ ] The examined master-list view loads correctly in the web server

## Implementation Notes

Copy the `compute:` block from `theses/examined/pdfpages/_referia.yml`:

```yaml
allocation:
  index: Name
  type: yaml
  filename: candidates.yml
  directory: ./info
  compute:
  - field: Name
    function: render_liquid
    args:
      template: "{% capture index %}{% if prefix %}{{ prefix }} {%endif%}{%if familyName %}{{ familyName }} {%endif%}{% if suffix %}{{ suffix }} {%endif%}{%if givenName %}{{ givenName }}{%endif%}{% endcapture %}{{ index | replace: ' ', '_' | replace: '.', '' }}"
    row_args:
      givenName: given
      familyName: family
      prefix: prefix
      suffix: suffix
```

Note: this is a config change in the OneDrive referia folder, not in the
referia package itself.

## Progress Updates

### 2026-10-07

Identified during cip000A validation. Pre-existing issue; not a regression
from the YAML migration.
