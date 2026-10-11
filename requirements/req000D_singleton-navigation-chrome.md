---
id: "000D"
title: "Index navigation chrome hides when there is only one choice"
status: "In Progress"
priority: "Medium"
created: "2026-10-11"
last_updated: "2026-10-11"
related_tenets:
- user-oriented-convenience
- explicit-implicit-separation
stakeholders:
- Reviewers
- Review authors
- Maintainers
tags:
- requirement
- navigation
- ui
- index
- web
- jupyter
---

# REQ-000D: Index navigation chrome hides when there is only one choice

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

When a review interface has at most one selectable index value (and, where applicable, at most one subseries / subindex choice), the UI must not present useless index or subindex selectors by default. Reviewers see content and assessment controls; navigation chrome for a singleton is omitted unless the author opts back in.

This is ordinary navigation behaviour for any `_referia.yml`, including root/overview configs that load a single wide or composed row. It is not a special product “mode.” Singleton identity itself remains an infrastructure concern (lynguine explicit wrapping `index`); referia only decides when to show chrome around that identity.

**Why this matters**: *User-oriented convenience* removes mechanical clutter. *Explicit–implicit separation* keeps auto-hide in the application layer rather than asking lynguine to invent UI modes.

**Who benefits**: Reviewers on web and Jupyter surfaces; authors of one-row overviews and constants-heavy setups.

## Acceptance Criteria

- [ ] With ≤1 index choice, index selector chrome is hidden by default
- [ ] With ≤1 subseries/subindex choice (when that chrome exists), it is hidden by default
- [ ] Authors can override to show navigation even for a singleton
- [ ] Behaviour applies generally (not only to catalog/root configs)
- [ ] Multi-row reviews (≥2 index values) keep visible navigation as today

## Notes

Pairs with lynguine REQ-000C (explicit singleton index label). Referia CIP-0010 (config-driven root) should consume both: named one-row overview + hidden nav chrome.

## References

- **Related Tenets**: `user-oriented-convenience`, `explicit-implicit-separation`
- **Related lynguine requirement**: REQ-000C (explicit wrapping `index` for singletons)
- **Implementing CIPs**: link from CIP `related_requirements` (expected: referia CIP-0010)

## Progress Updates

### 2026-10-11
Requirement drafted from root-overview / filter-bar discussion. Status Proposed.

### 2026-10-11 (later)
Marked **Ready**. Implementing HOW: referia CIP-0010 (nav chrome + root overview); depends on lynguine REQ-000C / CIP-0010 Phase 3 for named singleton `index`.

### 2026-10-11 (backlog)
Marked **In Progress**. Backlog: `2026-10-11_singleton-navigation-chrome` (plus root/overview tasks under CIP-0010).
