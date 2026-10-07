---
id: "2026-10-07_dependabot-referia-transitive-refresh"
title: "Refresh referia lock for Oct Dependabot (GitPython, oauthlib, urllib3)"
status: "Completed"
priority: "High"
created: "2026-10-07"
last_updated: "2026-10-07"
category: "infrastructure"
related_cips: []
owner: "lawrennd"
dependencies:
- "2026-08-13_dependabot-gitpython"
tags:
- backlog
- security
- dependabot
- gitpython
- oauthlib
- urllib3
- lynguine
---

# Task: Refresh referia lock for Oct Dependabot (GitPython, oauthlib, urllib3)

> **Scale note:** Backlog (not CIP). Mechanical consumer lock refresh against lynguine
> [PR #28](https://github.com/lawrennd/lynguine/pull/28); no architecture or API change.

## Description

Lynguine closed its October Dependabot alerts by raising floors and refreshing its lock
(GitPython **3.1.62**, oauthlib **4.0.0**, urllib3 **2.8.0**). Referia still resolves the
pre-fix transitive set, so Dependabot can keep reporting the same CVEs on this repo.

| Package | Before | After (2026-10-07) | Required | Path |
|---------|--------|---------------------|----------|------|
| gitpython | 3.1.59 | **3.2.0** | ≥ 3.1.62 | `referia → lynguine → gitpython` |
| oauthlib | 3.3.1 | **4.0.0** | ≥ 4.0.0 | transitive (requests-oauthlib / Google stack) |
| urllib3 | 2.7.0 | **2.8.0** | ≥ 2.8.0 | transitive via `requests` |

### Why this is open

- Lynguine work landed 2026-10-04 ([PR #28](https://github.com/lawrennd/lynguine/pull/28); supersedes Dependabot #27).
- Referia pulls lynguine from `main` but did **not** re-run `poetry update` afterward.
- Companion August task (`2026-08-13_dependabot-gitpython`) completed the ≥3.1.58 refresh; this task is the **second** bump for the October GHSAs, plus the oauthlib/urllib3 companions from the same lynguine group PR.

### Out of scope (tracked elsewhere)

- **diskcache** alert #73 (no upstream patch) → `2026-08-13_dependabot-diskcache`
- **LangChain** alert closure / CIP-000D close → `2026-08-13_dependabot-langchain-ecosystem`, CIP-000D
- **Clone URL trust review** in lynguine `download.py` → lynguine `2026-08-13_dependabot-gitpython`

## Acceptance Criteria

- [x] `poetry.lock` resolves `gitpython` to **≥ 3.1.62** (now **3.2.0**)
- [x] `poetry.lock` resolves `oauthlib` to **≥ 4.0.0** and `urllib3` to **≥ 2.8.0**
- [x] Test suite passes (634 passed, 21 skipped, 19 xfailed, 3 xpassed)
- [x] Companion task `2026-08-13_dependabot-gitpython` October refresh checkbox marked done
- [ ] Open Dependabot alerts for these three packages fixed or documented as pending GitHub rescan

## Implementation Notes

```bash
cd /Users/neil/lawrennd/referia
poetry update lynguine gitpython oauthlib urllib3
# Confirm versions in poetry.lock
poetry run pytest tests/ -q
```

Lynguine already declares `gitpython = ">=3.1.62"`. No referia `pyproject.toml` change should be
required unless Poetry cannot resolve against the git dependency on `main`.

After merge, check https://github.com/lawrennd/referia/security/dependabot — alerts often lag one scan.

## Related

- Lynguine PR: https://github.com/lawrennd/lynguine/pull/28
- Companion (August + October GitPython story): [`2026-08-13_dependabot-gitpython`](./2026-08-13_dependabot-gitpython.md)
- Lynguine backlog: `lynguine/backlog/infrastructure/2026-08-13_dependabot-gitpython.md`
- Related open (not this task): [`2026-08-13_dependabot-diskcache`](./2026-08-13_dependabot-diskcache.md),
  [`2026-08-13_dependabot-langchain-ecosystem`](./2026-08-13_dependabot-langchain-ecosystem.md)

## Progress Updates

### 2026-10-07

Task created from Dependabot triage after lynguine PR #28. Scale assessed as backlog (lock refresh only).

### 2026-10-07 (completed)

Refreshed `poetry.lock` against lynguine `main` (`resolved_reference` **4f68587**):
gitpython **3.2.0**, oauthlib **4.0.0**, urllib3 **2.8.0**. Lynguine package constraint in
lock shows `gitpython = ">=3.1.62"`. `poetry check` clean. Tests: 634 passed.
Dependabot alert closure pending GitHub rescan after push.
