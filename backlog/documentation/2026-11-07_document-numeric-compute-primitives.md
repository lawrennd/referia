---
id: "2026-11-07_document-numeric-compute-primitives"
title: "Document YAML numeric compute primitives in compute.rst"
status: "Proposed"
priority: "Medium"
created: "2026-11-07"
last_updated: "2026-11-07"
category: "documentation"
related_cips: []
owner: "lawrennd"
dependencies:
- "2026-11-07_yaml-numeric-compute-primitives"
tags:
- backlog
- documentation
- compute
- numeric
- vongole-interim
---

# Task: Document numeric compute primitives

> Documents the feature task `2026-11-07_yaml-numeric-compute-primitives`.
> Do not claim the ops exist in Sphinx until they are registered and tested.

## Description

Once the numeric YAML primitives are implemented, update
[docs/usage/compute.rst](../../docs/usage/compute.rst) so reviewers can find
them without reading the registry.

Document:

- Op names (`add`, `subtract`, `multiply`, threshold/`gte`/`lte`, optional `matmul`/`dot`)
- Short YAML examples under `compute` / `PopulateButton`
- Explicit note that these are **interim assessment compute** in referia pending
  vongole (lynguine CIP-0007), alongside existing `sum` / `max` / `len`

## Acceptance Criteria

- [ ] `docs/usage/compute.rst` lists the new primitives with brief descriptions
- [ ] At least one YAML example for multiply and one for threshold compare
- [ ] Callout states interim referia placement; long-term vongole / CIP-0007
- [ ] Docs match the live registry names (no fictional aliases)

## Implementation Notes

- Prefer a short subsection under existing compute usage rather than a new page.
- Cross-check against lynguine docs fix task so examples stay honest across repos.

## Related

- Feature: `2026-11-07_yaml-numeric-compute-primitives`
- Lynguine CIP: 0007
- Lynguine docs: `2026-11-07_fix-fictional-add-compute-examples`
- Existing referia vongole docs alignment: `2026-10-18_align-compute-docs-vongole-intent`

## Progress Updates

### 2026-11-07

Task created. Blocked on feature task implementation.
