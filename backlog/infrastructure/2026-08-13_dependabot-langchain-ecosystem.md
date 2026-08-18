---
id: "2026-08-13_dependabot-langchain-ecosystem"
title: "Confirm LangChain Dependabot alerts closed and close CIP-000D"
status: "Ready"
priority: "Medium"
created: "2026-08-13"
last_updated: "2026-08-18"
category: "infrastructure"
related_cips: ["000D", "0006"]
owner: "lawrennd"
dependencies:
- "2026-08-18_cip000D-bump-constraints"
- "2026-08-18_cip000D-api-compat"
- "2026-08-18_cip000D-docs"
tags:
- backlog
- security
- dependabot
- langchain
- llm
- cip000D
---

# Task: Confirm LangChain Dependabot alerts closed and close CIP-000D

## Description

After CIP-000D implementation tasks land on `main`, confirm GitHub Dependabot shows alerts
**#72** and **#74–#78** as fixed, mark CIP-000D Implemented then Closed (`compressed: false`),
and pause for documentation compression.

Dependabot can lag one scan after merge. diskcache **#73** is out of scope (no upstream patch;
see `2026-08-13_dependabot-diskcache.md`).

This item began as the pre-CIP alert tracker. Assessment is done: 0.3.x has no backports;
migration to 1.x is the remediation (CIP-000D Accepted). Remaining work is verification after
the three implementation tasks.

## Acceptance Criteria

- [x] Assess whether 0.3.x receives backported fixes or migration to LangChain 1.x is required
- [x] Upgrade path chosen and documented (CIP-000D: LangChain 1.x)
- [ ] `poetry.lock` on `main` has llm-group packages at patched 1.x versions
- [ ] LLM tests passed as part of the api-compat task
- [ ] Dependabot alerts #72, #74–#78 closed (or documented if a scan is still pending)
- [ ] CIP-000D status: Implemented, then Closed after you verify
- [ ] Decision recorded: compress into formal docs now or defer

## Implementation Notes

Do not start this task until the three CIP-000D implementation items are Completed.

```bash
gh api repos/lawrennd/referia/dependabot/alerts?state=open --jq \
  '.[] | select(.number == 72 or (.number >= 74 and .number <= 78)) | {number, state, package: .dependency.package.name}'
```

## Related

- CIP: [CIP-000D](../../cip/cip000D.md)
- Dependabot: https://github.com/lawrennd/referia/security/dependabot
- Implementation: [`2026-08-18_cip000D-bump-constraints`](./2026-08-18_cip000D-bump-constraints.md),
  [`2026-08-18_cip000D-api-compat`](./2026-08-18_cip000D-api-compat.md),
  [`2026-08-18_cip000D-docs`](./2026-08-18_cip000D-docs.md)
- Out of scope: [`2026-08-13_dependabot-diskcache`](./2026-08-13_dependabot-diskcache.md)

## Progress Updates

### 2026-08-13

Task created from Dependabot alert triage. Related to CIP-0006 scope but no existing backlog for CVE remediation.

### 2026-08-18

Code audit confirms referia uses a narrow LangChain surface (`ChatOpenAI`, `ChatAnthropic`, message
types, `invoke`) and does not call vulnerable APIs (`load_prompt`, URL text splitters). Migration
to 1.x still required to close Dependabot alerts. **[CIP-000D](../../cip/cip000D.md)** created for
migration design.

### 2026-08-18 (Accepted)

CIP-000D Accepted. This task is now the post-merge Dependabot closure check, blocked on the three
implementation backlogs.
