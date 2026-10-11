---
id: "2026-10-11_singleton-navigation-chrome"
title: "Auto-hide index/subindex nav chrome when ≤1 choice"
status: "Ready"
priority: "Medium"
created: "2026-10-11"
last_updated: "2026-10-11"
category: "features"
related_cips: ["0010"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- features
- web
- jupyter
- navigation
- cip0010
---

# Task: Auto-hide singleton navigation chrome

> Linked CIP: 0010. REQ-000D.
> For **list** layouts, selector hiding is owned by `2026-10-11_inline-list-same-page` (filter/sort replace selector even when many keys). This task is the general ≤1 rule for `side_by_side` (and any non-list chrome).

## Description

When there is at most one index value (and similarly for subseries/subindex), hide the selector chrome by default. Optional config override (`navigation: { index: auto|show|hide }`). Applies to any review — not only root overview.

## Acceptance Criteria

- [ ] Index selector hidden by default when `len(index_list) <= 1`
- [ ] Subindex/subseries chrome hidden when absent or ≤1 choice
- [ ] Author can force show/hide via ordinary config (infer-only OK for v1 if documented)
- [ ] Web and Jupyter aligned (or documented gap)
- [ ] Multi-row `side_by_side` reviews (≥2) keep the selector as today
- [ ] Does not fight `inline_list` (list layout already omits selector)

## Implementation Notes

- Web panel-nav / record selector; Jupyter `display_when` patterns
- Priority Medium: useful polish; overview success path is `inline-list-same-page`

## Related

- CIP: 0010
- Sibling: `2026-10-11_inline-list-same-page`

## Progress Updates

### 2026-10-11

Task created (Ready) after REQ-000D marked Ready and CIP-0010 Accepted.

### 2026-10-11 (later)

Retargeted: list chrome lives in `inline-list-same-page`; this task is REQ-000D for non-list layouts. Priority High → Medium.
