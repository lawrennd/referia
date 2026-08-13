---
id: "2026-08-13_dependabot-diskcache"
title: "Assess diskcache pickle deserialization alert (no upstream patch)"
status: "Proposed"
priority: "Medium"
created: "2026-08-13"
last_updated: "2026-08-13"
category: "infrastructure"
related_cips: ["0006"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- security
- dependabot
- diskcache
- llm
- cip0006
---

# Task: Assess diskcache pickle deserialization alert (no upstream patch)

## Description

Dependabot alert **#73** (medium): **CVE-2025-69872** / GHSA-w8v5-vhqr-4h9v — unsafe pickle
deserialization in `diskcache`.

- Locked version: **5.6.3** (latest; vulnerable range `<= 5.6.3`)
- **No patched version** listed in the advisory (`first_patched_version: null`)

`diskcache` is in referia's optional **`llm` group**, added under **CIP-0006** for LLM response caching.

## Acceptance Criteria

- [ ] Document how referia uses diskcache (cache keys, cache directory, trust boundary)
- [ ] Confirm whether cache files can be influenced by untrusted users or shared environments
- [ ] Choose mitigation: alternative cache backend, signed/trusted cache only, config to disable cache, or monitor for upstream fix
- [ ] Dependabot alert #73 dismissed or fixed with documented rationale
- [ ] If code changes required, tests cover the chosen mitigation

## Implementation Notes

Pickle deserialization is unsafe when cache contents can be tampered with. For single-user review
notebooks the risk may be acceptable; for multi-user or web-deployed referia (CIP-000C web reviewer)
the risk profile differs — check both contexts.

Options to evaluate:

1. Disable disk cache by default in untrusted deployments
2. Switch to JSON/msgpack cache values where feasible
3. Replace `diskcache` with another backend when an patched release appears
4. Subscribe to GHSA-w8v5-vhqr-4h9v for upstream fix

## Related

- CIP: [CIP-0006](../../cip/cip0006.md) — introduced diskcache for LLM caching
- Dependabot alert #73: https://github.com/lawrennd/referia/security/dependabot/73
- No existing backlog item for this alert.

## Progress Updates

### 2026-08-13

Task created from Dependabot alert triage. No upstream patch available; assessment task rather than simple upgrade.
