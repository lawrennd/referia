---
id: "2026-08-18_cip000E-workflow-permissions"
title: "Add least-privilege GitHub Actions permissions (CodeQL #1–#3)"
status: "Completed"
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
- github-actions
- cip000E
---

# Task: Add least-privilege GitHub Actions permissions

## Description

CodeQL alerts **#1–#3** (`actions/missing-workflow-permissions`) flag workflows with no explicit
`permissions:` block, so `GITHUB_TOKEN` gets default broad scope.

Add least-privilege permissions per CIP-000E:

| Job | File | Permissions |
|-----|------|-------------|
| `build` | `.github/workflows/python-tests.yml` | `contents: read` |
| `test-coverage` | `.github/workflows/docs.yml` | `contents: read` |
| `build-and-deploy` | `.github/workflows/docs.yml` | `contents: read` plus whatever `peaceiris/actions-gh-pages` needs (`pages: write` / `id-token: write` if required) |

## Acceptance Criteria

- [x] Both workflow files declare `permissions:` at workflow or job level
- [x] `python-tests.yml` and `docs.yml` `test-coverage` are read-only for contents
- [x] Docs deploy job still has enough token scope to publish GitHub Pages
- [ ] CodeQL alerts #1–#3 close after the change reaches `main` (or are expected to close on next scan)

## Implementation Notes

`peaceiris/actions-gh-pages@v3` pushes to the `gh-pages` branch using `GITHUB_TOKEN`, so the
deploy job needs `contents: write`. `pages: write` / `id-token: write` are not required for this
action. Do not grant broader scopes.

## Related

- CIP: [CIP-000E](../../cip/cip000E.md)
- Alerts: https://github.com/lawrennd/referia/security/code-scanning

## Progress Updates

### 2026-08-18

Task created when CIP-000E was Accepted.

Implemented: workflow-level `contents: read` on `python-tests.yml`; job-level `contents: write`
on `docs.yml` `build-and-deploy` and `contents: read` on `test-coverage`. Alert closure waits
for the next CodeQL scan after merge.
