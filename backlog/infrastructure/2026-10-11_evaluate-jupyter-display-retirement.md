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

> **Note**: This is a **decision / discovery** task, not an implement-drop ticket.
> Named layouts (REQ-000E / CIP-0010) are **web-first**; Jupyter parity is explicitly out of scope there.

## Description

CIP-000B and REQ-0008 established a web review path while leaving the Jupyter (`Reviewer` / ipywidgets) path intact for expert users. As web becomes the primary surface for multi-config hosting, filters, and named layout compositions, maintaining two display stacks may cost more than it helps.

This task asks: should referia **retire Jupyter as a display/rendering surface** (keep notebooks only for authoring/debug/compute experiments), keep it as a long-term peer, or shrink it to a documented legacy path?

Do **not** remove Jupyter support as part of this task. Produce a written recommendation that can amend REQ-0008 / CIP-000B if accepted.

## Acceptance Criteria

- [ ] Inventory what still depends on Jupyter display (`Reviewer`, `util/widgets.py`, example notebooks, docs, CI)
- [ ] List capabilities web still lacks vs Jupyter for real review workflows (if any)
- [ ] Recommend one of: keep peer / legacy-only / retire-with-timeline — with rationale against REQ-0008
- [ ] If retire or legacy: draft the requirement/CIP amendment text (do not apply until product Accept)
- [ ] Explicitly state impact on named layouts (already web-first) and on authors who only use notebooks today

## Implementation Notes

- Related: CIP-000B (web display; Jupyter untouched by design), REQ-0008 (web without Jupyter **and** Jupyter continues), CIP-0010 / REQ-000E (web-first layouts)
- Prefer a short decision note in a CIP amendment or requirements update over a parallel architecture doc
- Poetry / `jupyter` dependency and security surface are inputs to the cost side, not the whole decision

## Related

- CIP: 000B, 0010
- Requirements: REQ-0008, REQ-000E
- Documentation: CIP-000B motivation (local desktop without Jupyter overhead)

## Progress Updates

### 2026-10-11

Task created (Proposed). Triggered while specifying named layout compositions: implement layouts web-first; park Jupyter display future as an explicit product decision rather than inventing notebook layout parity.