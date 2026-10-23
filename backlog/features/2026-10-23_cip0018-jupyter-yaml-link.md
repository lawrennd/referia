---
id: "2026-10-23_cip0018-jupyter-yaml-link"
title: "Jupyter stacked inherit follows YAML inherit.compose or link only"
status: "Completed"
priority: "Medium"
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
- jupyter
- inherit
- cip0018
---

# Task: Jupyter uses YAML compose or today's link view

> Linked CIP: 0018. Stacked-from-the-browser is a web feature (REQ-0008).

## Description

Jupyter has no query string. Widget creation follows YAML `inherit.compose` if present, otherwise `link`. Do not invent a parallel `viewer_inherit` flag.

If YAML says `stacked`, Jupyter concatenates `interface_layers()` the same way the web spec assembly does. Otherwise today's parent-link child view.

## Acceptance Criteria

- [ ] No YAML `inherit.compose`: Jupyter matches today's child view
- [ ] `inherit.compose: stacked` in YAML: Jupyter shows ancestor sections above child
- [ ] No undocumented Jupyter-only flag for stacking
- [ ] Query-param behaviour is not required (and not faked) in Jupyter

## Implementation Notes

- Share spec assembly with `WebReviewer` where practical so web and Jupyter do not drift on YAML stacked.

## Related

- CIP: 0018
- REQ-0008 (web is the surface that honours allowlisted params)

## Progress Updates

### 2026-10-23

Task created (Ready) when CIP-0018 was Accepted.

### 2026-10-23 (implementation)

Implemented on branch `cip0018-implement-stacked-inherit`. Tests in `tests/test_inherit_view.py` pass (32). Status Completed.
