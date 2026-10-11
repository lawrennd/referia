---
id: "2026-10-11_singleton-navigation-chrome"
title: "Auto-hide index/subindex nav chrome when ≤1 choice"
status: "Ready"
priority: "High"
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

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Implement referia REQ-000D / CIP-0010: when there is at most one index value (and similarly for subseries/subindex), hide the selector chrome by default. Optional config override (e.g. `navigation: { index: auto|show|hide }`). Applies to any review, not only root overview.

## Acceptance Criteria

- [ ] Index selector hidden by default when `len(index_list) <= 1`
- [ ] Subindex/subseries chrome hidden when absent or ≤1 choice
- [ ] Author can force show/hide via ordinary config
- [ ] Web and Jupyter behaviour aligned (or documented gap with follow-up)
- [ ] Multi-row reviews (≥2) unchanged

## Implementation Notes

- Web panel-nav / record selector; Jupyter display_when patterns
- Sketch in CIP-0010 Detailed Description (navigation section)

## Related

- CIP: 0010
- Requirement (via CIP): REQ-000D

## Progress Updates

### 2026-10-11

Task created (Ready) after REQ-000D marked Ready and CIP-0010 Accepted.
