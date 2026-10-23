---
id: "2026-10-23_cip0018-interface-layers"
title: "interface_layers() — root-first viewer/review from each inherit node"
status: "Ready"
priority: "High"
created: "2026-10-23"
last_updated: "2026-10-23"
category: "features"
related_cips: ["0018"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-07-14_web-inherit-not-applied"
tags:
- backlog
- features
- inherit
- interface
- cip0018
---

# Task: `interface_layers()` on referia Interface

> Linked CIP: 0018. Do not implement until CIP-0018 is Accepted (it is).

## Description

Add a referia helper on `referia.config.interface.Interface` (name: `interface_layers()`) that walks `_parent` and returns **root-first**:

```
[(title, directory, viewer_entries, review_entries), ...]  # last item is self
```

Each tuple reads that node's `_data`, not `interface["viewer"]` / `interface["review"]` (those are already merged/appended and drop provenance). Circular inherit stays lynguine's existing error.

## Acceptance Criteria

- [ ] `interface_layers()` returns one tuple per node, oldest ancestor first, self last
- [ ] `viewer_entries` / `review_entries` are that node's own `_data` lists (empty list if absent)
- [ ] `title` is that config's `title`, falling back to the directory name
- [ ] A three-config chain yields three tuples; a config with no parent yields one
- [ ] Does not call lynguine `__getitem__` for `viewer`/`review` on parent nodes

## Implementation Notes

- Keep this in referia; do not fork lynguine merge.
- Prerequisite: `WebReviewer` must already construct this `Interface` so `_parent` exists (`2026-07-14_web-inherit-not-applied`).

## Related

- CIP: 0018
- Prerequisite: `2026-07-14_web-inherit-not-applied`

## Progress Updates

### 2026-10-23

Task created (Ready) when CIP-0018 was Accepted.
