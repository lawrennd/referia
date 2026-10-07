---
id: "2026-08-13_dependabot-gitpython"
title: "Resolve Dependabot alerts for GitPython (via lynguine)"
status: "In Progress"
priority: "High"
created: "2026-08-13"
last_updated: "2026-10-07"
category: "infrastructure"
related_cips: []
owner: "lawrennd"
dependencies: []
tags:
- backlog
- security
- dependabot
- gitpython
- lynguine
---

# Task: Resolve Dependabot alerts for GitPython (via lynguine)

## Description

GitPython is a **transitive** dependency of referia (`referia → lynguine → gitpython`). Referia does
not declare GitPython directly, so patched versions come from lynguine’s constraint plus a referia
lock refresh.

### August 2026 (done)

- Referia lock was stale at **3.1.51** against August advisories (alerts #79, #85–#99; patched **≥ 3.1.58**).
- After lynguine 0.1.2 (`gitpython >= 3.1.58`), referia ran `poetry update lynguine gitpython` →
  GitPython **3.1.59**, lynguine **0.1.2**. Tests passed (337).

### October 2026 (open)

- Lynguine raised the floor again to `gitpython >= 3.1.62` and locked **3.1.62**
  ([lynguine PR #28](https://github.com/lawrennd/lynguine/pull/28)).
- Referia `poetry.lock` still has GitPython **3.1.59** as of 2026-10-04.
- Referia pulls lynguine from `main` (`pyproject.toml`), so a lock refresh should pick up the new floor.

Most alerts concern unguarded git option forwarding, config injection, and arbitrary file
read/overwrite — relevant if untrusted input reaches GitPython APIs (lower risk for typical referia
review workflows, but still worth patching).

## Dependabot alerts (August 2026 set)

| # | Severity | GHSA | Summary (abbrev.) |
|---|----------|------|-------------------|
| 79 | high | GHSA-rwj8-pgh3-r573 | Env-var exfiltration via `Repo.clone_from()` URL |
| 85 | high | GHSA-3rp5-jjmw-4wv2 | git-config section-name injection (RCE) |
| 86 | high | GHSA-6p8h-3wgx-97gf | `--template` clone hook RCE |
| 87 | high | GHSA-fjr4-x663-mwxc | Arbitrary file overwrite via `diff --output` |
| 88 | high | GHSA-r9mr-m37c-5fr3 | Option guard bypass (token smuggling) |
| 89 | high | GHSA-94p4-4cq8-9g67 | Env-var exfiltration via remote URL |
| 90 | high | GHSA-3f7w-8rr8-f37f | Unguarded options in checkout / tag create |
| 91 | medium | GHSA-539m-9xh6-q6rr | `--add-file` archive arbitrary read |
| 92 | medium | GHSA-p538-c434-8v24 | `--output` rev-list truncation |
| 94 | high | GHSA-4gmw-gg2m-w46p | read-tree option forwarding |
| 95 | high | GHSA-9rj7-rf2p-w77r | `Repo.init` `--template` RCE |
| 96 | medium | GHSA-hh9p-6wh2-4mfc | `--pathspec-from-file` arbitrary read |
| 97 | high | GHSA-wvpp-8hx9-p66j | Option guard bypass (`split_single_char_options`) |
| 98 | high | GHSA-jm78-9fvv-mhgr | git-config OPTION-name injection |
| 99 | high | GHSA-hmq2-w58f-27jc | `.gitmodules` submodule path traversal |

October lynguine advisories (need **≥ 3.1.62**): tracked on lynguine Dependabot / companion backlog
(e.g. GHSA-239g-whfq-7xj9, GHSA-g5vv-9gxw-82hx, GHSA-whh4-5q6c-9v3x, GHSA-59cr-6r3x-644w).

## Acceptance Criteria

- [x] August refresh: `poetry.lock` resolves `gitpython` to **≥ 3.1.58** (reached **3.1.59**)
- [x] Referia test suite passed after August lock update (337 passed)
- [x] Lynguine change linked (lynguine 0.1.2 / companion backlog; later [PR #28](https://github.com/lawrennd/lynguine/pull/28) for 3.1.62)
- [ ] October refresh: `poetry.lock` resolves `gitpython` to **≥ 3.1.62** (still **3.1.59** as of 2026-10-07) — tracked by [`2026-10-07_dependabot-referia-transitive-refresh`](./2026-10-07_dependabot-referia-transitive-refresh.md) (also bumps oauthlib / urllib3)
- [ ] August Dependabot alerts (#79, #85–#99) fixed or dismissed with documented rationale (pending GitHub rescan after August; re-check after October refresh)
- [ ] Any new GitPython alerts after the October refresh fixed or dismissed with rationale

## Implementation Notes

1. Lynguine declares the floor (`gitpython >= 3.1.62` as of 2026-10-04).
2. In referia: `poetry update lynguine gitpython` (lynguine is git dependency on `main`).
3. Confirm no referia code calls vulnerable GitPython APIs with untrusted input (GitPython use is via lynguine).
4. Clone URL trust review remains on the **lynguine** companion task (`download.py` / `clone_or_pull.py`).

## Related

- Dependabot: https://github.com/lawrennd/referia/security/dependabot
- Dependency path: `referia → lynguine → gitpython`
- Lynguine backlog: `lynguine/backlog/infrastructure/2026-08-13_dependabot-gitpython.md`
- Lynguine PR (October floor): https://github.com/lawrennd/lynguine/pull/28
- Lynguine lock: GitPython **3.1.62**; referia lock: **3.1.59** (needs refresh)

## Progress Updates

### 2026-08-13

Task created from Dependabot alert triage. No matching CIP/backlog found.

### 2026-08-13 (evening)

Lynguine 0.1.2 released with `gitpython >= 3.1.58`. Referia lock updated:
`poetry update lynguine gitpython` → gitpython 3.1.51 → **3.1.59**, lynguine 0.1.1 → **0.1.2**.
Tests pass. Dependabot alert closure pending GitHub rescan. Status briefly treated as complete for
the August floor.

### 2026-10-04

Reopened for documentation sync with lynguine:

- Lynguine landed [PR #28](https://github.com/lawrennd/lynguine/pull/28): floor `>=3.1.62`, lock **3.1.62**
- Referia lock still **3.1.59** — needs a second `poetry update lynguine gitpython`
- Status set back to **In Progress** until the October refresh and alert check are done

### 2026-10-07

October consumer refresh (GitPython + oauthlib + urllib3) split into Ready backlog
[`2026-10-07_dependabot-referia-transitive-refresh`](./2026-10-07_dependabot-referia-transitive-refresh.md)
so the work package is explicit and not buried only in this August-dated task.
