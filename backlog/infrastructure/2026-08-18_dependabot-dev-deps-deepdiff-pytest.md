---
id: "2026-08-18_dependabot-dev-deps-deepdiff-pytest"
title: "Upgrade dev dependencies deepdiff and pytest for Dependabot alerts"
status: "Completed"
priority: "High"
created: "2026-08-18"
last_updated: "2026-08-18"
category: "infrastructure"
related_cips: []
owner: "lawrennd"
dependencies: []
tags:
- backlog
- security
- dependabot
- deepdiff
- pytest
- dev-dependencies
---

# Task: Upgrade dev dependencies deepdiff and pytest for Dependabot alerts

## Description

GitHub Dependabot reports **three open alerts** in dev/test dependencies declared in
`pyproject.toml` `[tool.poetry.dev-dependencies]`. These are not runtime referia dependencies;
fixes should be straightforward lock updates with test-suite validation.

### deepdiff (2 alerts — critical + high)

- Locked version: **6.7.1** (`deepdiff = "^6.6.0"`)
- Required: **≥ 8.6.2** (alert #22); **≥ 8.6.1** (alert #7)
- Alert **#7** (critical): Class pollution in Delta class → DoS, RCE
- Alert **#22** (high): Memory exhaustion DoS via `SAFE_TO_IMPORT`
- Used in tests for structural diff assertions

### pytest (1 alert — medium)

- Locked version: **7.4.4** (`pytest = "^7.0"`)
- Required: **≥ 9.0.3**
- Alert **#28** (medium): Vulnerable tmpdir handling
- May require checking compatibility of `pytest-cov` and `pytest-mock` with pytest 9.x

## Acceptance Criteria

- [x] `pyproject.toml` constraints updated if needed (`deepdiff >= 8.6.2`, `pytest >= 9.0.3`)
- [x] `poetry.lock` resolves deepdiff to **≥ 8.6.2** and pytest to **≥ 9.0.3**
- [ ] Dependabot alerts #7, #22, and #28 closed (verify on GitHub after push)
- [x] `poetry run pytest tests/` passes
- [x] Any deepdiff API breaking changes in tests addressed (6.x → 8.x major jump)

## Implementation Notes

```bash
# Review constraint bumps in pyproject.toml first if poetry refuses to resolve
poetry update deepdiff pytest pytest-cov pytest-mock
poetry run pytest tests/ -q
```

deepdiff 6 → 8 is a major version change; grep tests for `DeepDiff` usage and check release notes
for breaking changes before closing the task.

pytest 7 → 9 is also a major jump; confirm CI workflow Python version supports pytest 9.

## Related

- Dependabot: https://github.com/lawrennd/referia/security/dependabot
- Alerts: #7, #22 (deepdiff), #28 (pytest)
- Prior security backlog: `2026-08-13_dependabot-cryptography-jupyterlab.md` (completed)

## Progress Updates

### 2026-08-18

Task created from GitHub security review. Dev-only quick wins after production dependency updates.

### 2026-08-18 (completed)

Upgraded dev constraints in `pyproject.toml` (`deepdiff ^8.6.2`, `pytest ^9.0.3`). Lock resolves
deepdiff **8.6.2**, pytest **9.1.1**. No test code changes required for deepdiff 8.x API.
`poetry run pytest tests/` — 337 passed, 1 skipped.
