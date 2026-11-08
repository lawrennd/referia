---
id: "2026-11-08_cip0026-examples-sphinx-index"
title: "CIP-0026 Phase A: restore docs/examples/index.rst"
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
- sphinx
- examples
---

# Task: Restore Sphinx examples index

> Backlog task for [CIP-0026](../../cip/cip0026.md) Phase A.

## Description

`docs/index.rst` includes `examples/index`, but `docs/examples/index.rst` is
missing. Create a curated Sphinx page listing package examples with one-line
purpose + `referia serve` command, linking into usage guides. De-emphasise
raw notebooks unless kept as secondary.

## Acceptance Criteria

- [x] `docs/examples/index.rst` exists and builds as a toctree target
- [x] Lists current serveable demos with purpose + serve command
- [x] Links to relevant usage guides (e.g. catalog schedule)
- [x] Notes notebooks as secondary / legacy if still present

## Implementation Notes

Prefer not to duplicate full README content — keep the index short and point
at `examples/*/README.md`.

## Related

- CIP: 0026

## Progress Updates

### 2026-11-08

Task created; CIP accepted and worktree started.

Restored `docs/examples/index.rst` with serveable demo table, numeric
placeholder, LLM/thesis note, and legacy notebook pointer.
