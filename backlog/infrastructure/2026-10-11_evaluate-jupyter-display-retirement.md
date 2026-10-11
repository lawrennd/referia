---
id: "2026-10-11_evaluate-jupyter-display-retirement"
title: "Evaluate retiring Jupyter as a review display surface"
status: "Proposed"
priority: "Low"
created: "2026-10-11"
last_updated: "2026-10-11"
category: "infrastructure"
related_cips: ["000B", "0010"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- jupyter
- web
- display
- product-decision
---

# Task: Evaluate retiring Jupyter as a review display surface

> **Decision / discovery** task — not an implement-drop ticket.
> CIP-0010 now requires **list + filter/sort on Jupyter** while notebook display exists (`inline-list-same-page`). This evaluation is about the long-term stack, not blocking that work.

## Description

CIP-000B / REQ-0008 left Jupyter display intact. Web is primary for multi-config hosting; `inline_list` will also land on Jupyter. Decide whether to keep Jupyter as a peer display surface, legacy-only, or retire it on a timeline.

Do **not** remove Jupyter as part of this task. Produce a written recommendation that can amend REQ-0008 / CIP-000B if accepted.

## Acceptance Criteria

- [ ] Inventory Jupyter display dependencies (`Reviewer`, widgets, notebooks, CI)
- [ ] Compare cost of dual stacks after `inline_list` exists on both surfaces
- [ ] Recommend: keep peer / legacy-only / retire-with-timeline — vs REQ-0008
- [ ] If retire or legacy: draft requirement/CIP amendment text (do not apply until Accept)
- [ ] Note impact on authors who only use notebooks today

## Implementation Notes

- Do not block `2026-10-11_inline-list-same-page`
- Related: CIP-000B, REQ-0008, CIP-0010 / REQ-000E

## Related

- CIP: 000B, 0010
- Sibling: `2026-10-11_inline-list-same-page`

## Progress Updates

### 2026-10-11

Task created (Proposed). Originally framed as alternative to inventing Jupyter layout parity.

### 2026-10-11 (later)

Updated: list layout now includes Jupyter behavioural contract; this task stays Low product-decision, not a substitute for implementing notebook list chrome.
