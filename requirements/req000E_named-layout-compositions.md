---
id: "000E"
title: "Authors choose among named layout compositions, not fine-grained placement"
status: "Proposed"
priority: "High"
created: "2026-10-11"
last_updated: "2026-10-11"
related_tenets:
- template-driven-composition
- user-oriented-convenience
- explicit-implicit-separation
stakeholders:
- Review authors
- Reviewers
- Maintainers
tags:
- requirement
- layout
- display
- ui
- web
- composition
---

# REQ-000E: Authors choose among named layout compositions, not fine-grained placement

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Review authors must be able to choose **which composition** the review uses — where the major UI regions (navigation, filters, viewer content, assessment controls, documents) sit relative to each other — by selecting a **named layout composition** from a small, curated set with clear defaults. They place content in the sense Markdown and LaTeX authors do: pick a document class / named kind, write the substance, and let the system handle mechanical layout. They must **not** need Word-like fine control: no pixel positions, column-width fiddling, drag-and-drop regions, or per-widget absolute placement.

New compositions may be added over time as named options; each remains a deliberate, documented arrangement rather than an open geometry API.

**Why this matters**: *Template-driven composition* favours reusable patterns over bespoke layout. *User-oriented convenience* keeps authors in the domain of review structure, not CSS. *Explicit–implicit separation* puts layout choice in the application config layer as an explicit named option, with sensible defaults when omitted.

**Who benefits**: Authors of discovery overviews (inline list + mark-in-place) and of document-centric reviews (viewer beside form); reviewers who get an appropriate chrome without empty panes.

## Acceptance Criteria

- [ ] Authors can select a layout from a **small named set** in ordinary `_referia.yml` (no special product mode)
- [ ] Omitting the choice yields today’s default composition (document-centric side-by-side viewer + review)
- [ ] At least one named composition supports **list with assessments beside each entry** (mark in place), suitable for discovery overviews — not a vacant second pane
- [ ] Which fields appear as assessments is declared with the ordinary `review:` dialect (`field` + `type`); layout only changes composition, not a parallel mapping language
- [ ] Authors are **not** required (or invited) to set fine geometry: no freeform region coordinates, splitter recipes, or per-widget absolute placement as the authoring model
- [ ] The same named-composition mechanism applies generally (any review), not only root/catalog configs
- [ ] Adding a new composition is a deliberate product/design step (new named option), not unbounded author inventiveness
- [ ] Under the list composition, filter/sort chrome replaces the index selector (same idea on web and Jupyter)
- [ ] List composition works on web; Jupyter gets the same behavioural contract (list + filter/sort, not one-row browsing as the primary chrome)

## Notes

Complements REQ-000D (when to hide nav chrome for singletons). CIP-0010: `display.layout: inline_list` is the option that lists the tall working set; lynguine keeps discovery/store results; referia owns page composition.

Analogy for authors and docs: **document class, not desktop publishing**.

Long-term Jupyter-as-display retirement remains a separate product question; it does not block list-layout behaviour on notebooks while Jupyter display exists.
## References

- Tenet: [template-driven-composition](../tenets/referia/template-driven-composition.md)
- Tenet: [user-oriented-convenience](../tenets/referia/user-oriented-convenience.md)
- CIP-0010 (config-driven root / overview presentation)
- CIP-000B (web display system)
