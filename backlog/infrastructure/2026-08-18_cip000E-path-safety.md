---
id: "2026-08-18_cip000E-path-safety"
title: "Centralise URL-to-filesystem path safety (CodeQL #4–#11)"
status: "Ready"
priority: "High"
created: "2026-08-18"
last_updated: "2026-08-18"
category: "infrastructure"
related_cips: ["000E"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- security
- codeql
- web
- path-injection
- cip000E
---

# Task: Centralise URL-to-filesystem path safety

## Description

CodeQL `py/path-injection` alerts **#4–#11** track URL `config_path` into `Path` operations and
`os.chdir`. `_resolve_config_path` already uses `resolve()` + `relative_to(root)`, but
`_list_sub_configs` does not apply the same check before `rglob`, and CodeQL does not treat the
existing check as a sanitizer.

CIP-000E: add `safe_path_under_root(root, *parts)` (new `referia/web/path_safety.py` or helpers in
`routes.py`) and use it everywhere a URL segment becomes a filesystem path. Routes own validation;
`WebReviewer` receives only already-validated directories.

This is an invariant for a later authenticated deployment — auth does not make `../` safe.

## Acceptance Criteria

- [ ] `safe_path_under_root` (or equivalent) rejects paths that escape the root
- [ ] `_resolve_config_path` and `_list_sub_configs` use it (including before `rglob`)
- [ ] Tests cover `../`, absolute escape, and a valid nested config path
- [ ] Document the contract: `WebReviewer.__init__` directory is caller-validated
- [ ] Web route tests still pass
- [ ] CodeQL alerts #4–#11 close, or remaining findings have documented suppressions

## Implementation Notes

`resolve()` + `relative_to` is the defence, including symlink escape. Prefer a dedicated module if
`WebReviewer` also needs the helper; otherwise keep it in `routes.py` to avoid extra files.

## Related

- CIP: [CIP-000E](../../cip/cip000E.md)
- Code: `referia/web/routes.py`, `referia/assess/web_review.py`
- Tests: `tests/test_web_routes.py`

## Progress Updates

### 2026-08-18

Task created when CIP-000E was Accepted.
