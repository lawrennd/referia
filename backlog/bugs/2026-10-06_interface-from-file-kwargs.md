---
id: "2026-10-06_interface-from-file-kwargs"
title: "Forward allowed_roots / unbounded_paths in referia Interface"
status: "Ready"
priority: "High"
created: "2026-10-06"
last_updated: "2026-10-06"
category: "bugs"
related_cips: ["000F"]
owner: ""
dependencies: []
tags:
- backlog
- bug
- interface
- lynguine
---

# Task: Fix Interface.from_file kwargs mismatch

## Description

lynguine `Interface.from_file` constructs the subclass with
`allowed_roots` and `unbounded_paths`. Referia’s
`referia.config.interface.Interface.__init__` only accepts
`data`, `directory`, `user_file`, so every `from_file` path fails
(`WebReviewer`, `referia.data.Data()`, etc.) with
`TypeError: unexpected keyword argument 'allowed_roots'`.

This blocks loading any config via the normal entry points, including REF
2021 files and current OneDrive workflows through the web server.

## Acceptance Criteria

- [ ] Referia `Interface.__init__` accepts and forwards path kwargs to
  `super().__init__` (or uses `**kwargs` safely)
- [ ] `Interface.from_file("_referia.yml", directory=...)` succeeds for a
  minimal fixture
- [ ] `WebReviewer` construction works again for a minimal config
- [ ] Regression test covers the kwargs path

## Implementation Notes

Related to CIP-000F REF replay investigation but not dialect migration.
Can land independently and should land early.

## Related

- CIP: 000F (related bug)
- lynguine `lynguine/config/interface.py` `from_file`

## Progress Updates

### 2026-10-06

Bug recorded while accepting CIP-000F.
