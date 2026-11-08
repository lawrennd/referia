---
id: "2026-11-08_cip0026-serve-readme-sweep"
title: "CIP-0026 Phase A: serve-command README sweep"
status: "Completed"
priority: "Medium"
created: "2026-11-08"
last_updated: "2026-11-08"
category: "documentation"
related_cips: ["0026"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- documentation
- referia-serve
- examples
---

# Task: Serve-command README sweep

> Backlog task for [CIP-0026](../../cip/cip0026.md) Phase A.

## Description

Align package example READMEs (and any package docs that still advertise
`referia-web` / `python -m referia.web.app`) to the canonical launch:

```bash
poetry run referia serve --directory examples/<name>
```

Update root `README.md` example bullets if present so they point at the
refreshed `examples/` tree.

## Acceptance Criteria

- [x] `examples/overview_inline_list/README.md` uses `referia serve`
- [x] `examples/topic_scatter_click/README.md` drops `referia-web` as primary/alternate
- [x] Grep of package docs finds no primary `referia-web` / module launch ads
- [x] Root README example pointers (if any) mention `referia serve`

## Implementation Notes

Canonical block from CIP-0026. Optional `--root` note for multi-config hosts.
Do not remove console-script entry points in this task — demote docs only.

## Related

- CIP: 0026

## Progress Updates

### 2026-11-08

Task created; CIP accepted and worktree started.

READMEs for overview / topic_scatter / subject_grain updated to canonical
`poetry run referia serve`. Root README gained a Package examples section.
Remaining `referia-web` mentions are only in CIP/backlog text.
