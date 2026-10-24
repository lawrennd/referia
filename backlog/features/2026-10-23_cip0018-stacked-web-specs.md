---
id: "2026-10-23_cip0018-stacked-web-specs"
title: "WebReviewer stacked spec assembly from interface_layers()"
status: "Completed"
priority: "High"
created: "2026-10-23"
last_updated: "2026-10-23"
category: "features"
related_cips: ["0018"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-10-23_cip0018-interface-layers"
- "2026-10-23_cip0018-view-query-allowlist"
tags:
- backlog
- features
- web
- inherit
- cip0018
---

# Task: Assemble stacked viewer/review specs

> Linked CIP: 0018. Presentation stays in referia; lynguine merge is unchanged.

## Description

When `compose=stacked`, `WebReviewer.get_viewer_specs` / `get_review_specs` concatenate from `interface_layers()`:

1. For each ancestor layer: wrap that layer's entries in `type: Section` with `title` = that config's title (fallback: directory). Mark `inherited: true` and `writable` from that hop's `inherit.writable`.
2. Then the child's unwrapped (or optionally section-titled) local entries.

Honour `inherit_viewer` / `inherit_review`. When stacked, **do not** inject the static *Parent assesser available here* viewer HTML.

`compose=link` (default) keeps today's child specs and the existing parent-link blob.

Do **not** put `review` on lynguine `append` to achieve stacking.

## Acceptance Criteria

- [ ] `compose=link` / omitted: child review specs only; parent-link present; no inherited Section titles
- [ ] `compose=stacked`: ancestor sections above child in both viewer and review; order grandparent → parent → child
- [ ] Titles match ancestor `title` fields
- [ ] `compose=stacked&inherit_review=0`: ancestor viewers only; child review unchanged
- [ ] `inherit_viewer=0` omits ancestor viewers
- [ ] Stacked mode skips the injected parent-assessor viewer element
- [ ] lynguine default ignore/append is unchanged

## Implementation Notes

- Read each node's `_data`, not merged `__getitem__`.
- CIP-0010 `inline_list` still lists rows; this must not flatten the working set.

## Related

- CIP: 0018
- Depends on: `2026-10-23_cip0018-interface-layers`, `2026-10-23_cip0018-view-query-allowlist`

## Progress Updates

### 2026-10-23

Task created (Ready) when CIP-0018 was Accepted.

### 2026-10-23 (implementation)

Implemented on branch `cip0018-implement-stacked-inherit`. Tests in `tests/test_inherit_view.py` pass (32). Status Completed.
