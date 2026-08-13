---
id: "2026-08-13_dependabot-cryptography-jupyterlab"
title: "Upgrade cryptography and JupyterLab for Dependabot alerts"
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
- cryptography
- jupyterlab
---

# Task: Upgrade cryptography and JupyterLab for Dependabot alerts

## Description

Two packages in referia's dependency tree have open Dependabot alerts addressable by lock updates
without major API migration.

### cryptography (1 alert)

- Locked version: **49.0.0**
- Required: **≥ 50.0.0**
- Alert **#93** (high): CVE-2026-69247 / GHSA-g6cj-pr64-35w5 — PKCS#7 Bleichenbacher oracle
- Transitive via `google-auth` (lynguine → google-api-python-client chain)

### jupyterlab (5 alerts)

- Locked version: **4.6.1**
- Required: **≥ 4.6.2**
- Transitive via direct `jupyter = "*"` dependency
- Alerts **#80–#84**: XSS, extension blocklist bypass, PluginManager bypass (several CVE-2026-734xx)

## Acceptance Criteria

- [x] `poetry.lock` resolves `cryptography` to **≥ 50.0.0** (now **50.0.0**)
- [x] `poetry.lock` resolves `jupyterlab` to **≥ 4.6.2** (now **4.6.3**)
- [ ] Dependabot alerts #80–#84 and #93 closed
- [x] `poetry run pytest` passes (337 passed)
- [ ] Jupyter-based review workflows still launch (smoke test)

## Implementation Notes

```bash
poetry update cryptography jupyterlab
# or broader: poetry update jupyter
```

If `cryptography` 50.x is blocked by an upstream pin, document the blocker and consider a
`poetry` dependency override as interim measure.

JupyterLab alerts mainly affect interactive notebook/extension surfaces; referia's primary use is
review notebooks — still worth patching for shared environments.

## Related

- Dependabot: https://github.com/lawrennd/referia/security/dependabot
- cryptography alert via lynguine: `lynguine/backlog/infrastructure/2026-08-13_dependabot-cryptography-transitive.md`
- JupyterLab is a direct referia `jupyter` dependency (not lynguine)
- No existing CIP or backlog item covers these alerts.

## Progress Updates

### 2026-08-13

Task created from Dependabot alert triage. No matching CIP/backlog found.

### 2026-08-13 (evening)

`poetry update cryptography jupyterlab lynguine` → cryptography 49.0.0 → **50.0.0**,
jupyterlab 4.6.1 → **4.6.3**. Tests pass. Dependabot alert closure pending GitHub rescan.
