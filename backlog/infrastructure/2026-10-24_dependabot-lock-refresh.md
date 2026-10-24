---
id: "2026-10-24_dependabot-lock-refresh"
title: "Refresh referia lock for Oct 22–23 Dependabot (Pillow, GitPython, Jupyter stack)"
status: "Completed"
priority: "High"
created: "2026-10-24"
last_updated: "2026-10-24"
category: "infrastructure"
related_cips: []
owner: "Neil D. Lawrence"
dependencies:
- "2026-10-07_dependabot-referia-transitive-refresh"
tags:
- backlog
- security
- dependabot
- pillow
- gitpython
- jupyter
- poetry
---

# Task: Refresh referia lock for Oct 22–23 Dependabot (Pillow, GitPython, Jupyter stack)

> **Scale note:** Backlog (not CIP). Mechanical consumer lock refresh. No architecture or API change.
> Worked in a separate worktree (`/Users/neil/lawrennd/referia-dependabot`) so CIP-0018 WIP stays parked.

## Description

Dependabot on [lawrennd/referia](https://github.com/lawrennd/referia/security/dependabot)
reopened **62 alerts** (6 critical, 32 high, 22 medium, 2 low) between 2026-09-01 and
2026-10-23. Most of the volume is Pillow 12.3.0; the rest is a short list of lock bumps.
The 2026-10-07 GitPython/oauthlib/urllib3 refresh already closed those three families.

| Package | Locked (main) | Patched | Alerts | Path |
|---------|---------------|---------|--------|------|
| Pillow | 12.3.0 | **13.0.0** | ~40 (5 critical) | direct (`pillow = "*"`) |
| GitPython | 3.2.0 | **3.2.1** | 1 high RCE | `referia → lynguine → gitpython` (`>=3.1.62` already allows 3.2.1) |
| certifi | 2026.6.17 | **2026.10.19** | 1 critical | transitive CA bundle |
| tornado | 6.5.7 | **6.5.9** | 6 | Jupyter stack |
| jupyterlab | 4.6.3 | **4.6.4** | with notebook | Jupyter stack |
| notebook | 7.6.0 | **7.6.3** | with jupyterlab | Jupyter stack |
| nbconvert | 7.17.1 | **7.17.2** | 1 high | Jupyter stack |
| pyarrow | 17.0.0 | **23.0.1** | 1 high | lynguine `parquet` extra (`>=14,<24`); version jump, smoke-test |
| soupsieve | 2.8.4 | **2.9.0** | 2 medium | Beautiful Soup |
| langgraph-sdk | 0.4.2 | **0.4.4** | 1 high | optional `llm` extra |
| setuptools | 83.0.0 | **84.1.0** | 1 low | Windows-only |

### Out of scope (tracked elsewhere)

- **diskcache** alert #73 (no upstream patch) → `2026-08-13_dependabot-diskcache`
- Raising lynguine's GitPython *floor* to `>=3.2.1` (optional hardening; 3.2.1 already satisfies `>=3.1.62`)

## Acceptance Criteria

- [x] `poetry.lock` resolves Pillow **≥ 13.0.0**, gitpython **≥ 3.2.1**, certifi **≥ 2026.10.19**
- [x] Jupyter stack: tornado **≥ 6.5.9**, jupyterlab **≥ 4.6.4**, notebook **≥ 7.6.3**, nbconvert **≥ 7.17.2**
- [x] Remaining patched packages (soupsieve, langgraph-sdk, setuptools, pyarrow if resolvable with NumPy 1.x) updated or documented as blocked
- [x] `poetry check` clean (`pyproject.toml` unchanged)
- [x] Test suite passes (893 passed, 1 skipped, 19 xfailed, 3 xpassed)
- [ ] Open Dependabot alerts for these packages fixed or documented as pending GitHub rescan

## Implementation Notes

```bash
cd /Users/neil/lawrennd/referia-dependabot
poetry update pillow gitpython certifi tornado jupyterlab notebook nbconvert pyarrow soupsieve langgraph-sdk setuptools
poetry check
poetry run pytest tests/ -q
```

No referia `pyproject.toml` change should be required: Pillow is already `*`, GitPython is
owned by lynguine at `>=3.1.62`. If pyarrow 23 cannot resolve against `numpy>=1,<2`, leave
pyarrow on the highest 17.x/compatible line and record the block.

Do not run this on `cip0018-implement-stacked-inherit`.

## Related

- Previous lock refresh: [`2026-10-07_dependabot-referia-transitive-refresh`](./2026-10-07_dependabot-referia-transitive-refresh.md)
- diskcache (leave open): [`2026-08-13_dependabot-diskcache`](./2026-08-13_dependabot-diskcache.md)
- Lynguine GitPython: `lynguine/backlog/infrastructure/2026-08-13_dependabot-gitpython.md`
- Dependabot: https://github.com/lawrennd/referia/security/dependabot

## Progress Updates

### 2026-10-24

Task created from Dependabot triage. CIP-0018 left parked; worktree from `origin/main`
at `/Users/neil/lawrennd/referia-dependabot` on branch `backlog-2026-10-24-dependabot-lock-refresh`.

### 2026-10-24 (completed)

`poetry update` against live `lynguine@main` fails: GitHub main now requires `numpy>=2`, referia still has `numpy>=1,<2`. Resolved against locked lynguine **8be6fcc** (temporary `rev` pin, then restored `branch = main`). `pyproject.toml` has no net change.

| Package | Before | After |
|---------|--------|-------|
| pillow | 12.3.0 | **13.0.0** |
| gitpython | 3.2.0 | **3.2.1** |
| certifi | 2026.6.17 | **2026.10.23** |
| tornado | 6.5.7 | **6.6** |
| jupyterlab | 4.6.3 | **4.6.4** |
| notebook | 7.6.0 | **7.6.3** |
| nbconvert | 7.17.1 | **7.17.2** |
| soupsieve | 2.8.4 | **2.10** (`<3.13`); 3.0.4 on Python ≥3.13 |
| langgraph-sdk | 0.4.2 | **0.4.9** |
| setuptools | 83.0.0 | **84.2.1** |

**Blocked (not this lock):** pyarrow stays **17.0.0**. Locked lynguine caps `pyarrow<18` and NumPy 1.x; Dependabot's patch is **23.0.1**, which needs a lynguine/NumPy 2 bump. diskcache **5.6.3** still has no patch (`2026-08-13_dependabot-diskcache`).

Tests: 893 passed. Alert closure pending push + GitHub rescan.
