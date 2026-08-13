---
id: "2026-08-13_dependabot-gitpython"
title: "Resolve Dependabot alerts for GitPython (via lynguine)"
status: "Completed"
priority: "High"
created: "2026-08-13"
last_updated: "2026-08-13"
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

GitHub Dependabot reports **15 open high/medium alerts** for `GitPython` / `gitpython` in `poetry.lock`
(current locked version: **3.1.51**). Patched version required: **≥ 3.1.58** (covers alerts #85–#99).

GitPython is a **transitive dependency** of `lynguine` (`lynguine → gitpython *`). Referia does not
declare GitPython directly, so resolution likely requires coordinating a minimum version constraint
in lynguine and refreshing referia's lock file.

Most alerts concern unguarded git option forwarding, config injection, and arbitrary file
read/overwrite — relevant if untrusted input reaches GitPython APIs (lower risk for typical referia
review workflows, but still worth patching).

## Dependabot alerts

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

## Acceptance Criteria

- [x] `poetry.lock` resolves `gitpython` to **≥ 3.1.58** (now **3.1.59**)
- [ ] All 15 Dependabot alerts (#79, #85–#99) show as fixed or dismissed with documented rationale
- [x] Referia test suite passes after lock update (337 passed)
- [x] If lynguine change is required, corresponding lynguine backlog task or PR is linked (lynguine 0.1.2)

## Implementation Notes

1. Add `gitpython = ">=3.1.58"` (or equivalent) to lynguine `pyproject.toml` if not already constrained.
2. In referia: `poetry update gitpython` (or full lock refresh after lynguine release).
3. Confirm no referia code calls vulnerable GitPython APIs with untrusted input.

## Related

- Dependabot: https://github.com/lawrennd/referia/security/dependabot
- Dependency path: `referia → lynguine → gitpython`
- Lynguine backlog: `lynguine/backlog/infrastructure/2026-08-13_dependabot-gitpython.md`
- Lynguine lock already has gitpython 3.1.58; referia lock is stale at 3.1.51
- No existing CIP or backlog item covers this alert set.

## Progress Updates

### 2026-08-13

Task created from Dependabot alert triage. No matching CIP/backlog found.

### 2026-08-13 (evening)

Lynguine 0.1.2 released with `gitpython >= 3.1.58`. Referia lock updated:
`poetry update lynguine gitpython` → gitpython 3.1.51 → **3.1.59**, lynguine 0.1.1 → **0.1.2**.
Tests pass. Dependabot alert closure pending GitHub rescan.
