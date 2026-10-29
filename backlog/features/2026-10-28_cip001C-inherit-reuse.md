---
id: "2026-10-28_cip001C-inherit-reuse"
title: "inherit.reuse opt-in so catalog views share compute and review"
status: "Completed"
priority: "High"
created: "2026-10-28"
last_updated: "2026-10-28"
category: "features"
related_cips: ["001C"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- features
- inherit
- catalog
- overview
- cip001C
---

# Task: `inherit.reuse` opt-in so catalog views share compute and review

> Linked CIP: 001C. Do not remove the forced `compute`/`review` ignore — candidate reviews depend on it.

## Description

`Interface._process_parent` always appends `compute` and `review` to `inherit.ignore`. Sibling Today/Year need the parent's catalog input, output, compute, review, filters, and sort without duplicating the spec.

Add an explicit opt-in list. After applying today's defaults, remove each listed key from `ignore`. When `viewer` is ignored, skip the parent-assessor link injection so the child owns chrome.

```yaml
writable: true
inherit:
  directory: ../
  filename: _referia.yml
  writable: true
  reuse: [input, output, compute, review, filters, sort]
  ignore: [viewer]
```

Configs that omit `reuse` behave exactly as today.

## Acceptance Criteria

- [ ] `inherit.reuse` is a list of keys; each is removed from `inherit.ignore` after default ignore/append
- [ ] Candidate inherit without `reuse` still ignores parent `compute` and `review`
- [ ] Listing a default-ignored key in `reuse` makes that parent section available to the child
- [ ] When `viewer` is in `ignore`, the parent-assessor `<a href=…>` is not injected
- [ ] `inherit.writable: true` plus top-level `writable: true` still keeps parent output writable (existing lynguine contract)
- [ ] Tests cover: reuse of compute/review; default candidate inherit unchanged; viewer ignore skips parent link

## Implementation Notes

- Touch: `referia/config/interface.py` — `_process_parent` only
- Do not fork lynguine merge or `_bind_spec_directory` (lynguine CIP-0018)
- Do not treat `append: [compute]` as opt-in; that already fails because defaults are force-appended to ignore
- Soft depend for end-to-end Today Save: lynguine `2026-10-28_cip0018-bind-directory-sources`

## Related

- CIP: 001C
- lynguine CIP-0018 (directory bind; other repo)

## Progress Updates

### 2026-10-28

Task created (Ready) from CIP-001C acceptance.

### 2026-10-28 (later)

Completed: `inherit.reuse` strips listed keys after forced ignore; viewer ignore skips parent-assessor link.
