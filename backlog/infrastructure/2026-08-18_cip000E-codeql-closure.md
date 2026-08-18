---
id: "2026-08-18_cip000E-codeql-closure"
title: "Confirm CodeQL alerts closed and close CIP-000E"
status: "Ready"
priority: "Medium"
created: "2026-08-18"
last_updated: "2026-08-18"
category: "infrastructure"
related_cips: ["000E"]
owner: "lawrennd"
dependencies:
- "2026-08-18_cip000E-workflow-permissions"
- "2026-08-18_cip000E-exception-exposure"
- "2026-08-18_cip000E-path-safety"
- "2026-08-18_cip000E-xss-verification"
tags:
- backlog
- security
- codeql
- cip000E
---

# Task: Confirm CodeQL alerts closed and close CIP-000E

## Description

After the four CIP-000E implementation tasks land on `main`, confirm GitHub code scanning shows
**0 open** alerts from this inventory (20 alerts as of 2026-08-18), update CIP-000E to Implemented
then Closed (`compressed: false`), and pause for documentation compression.

GitHub scans can lag one run after merge.

## Acceptance Criteria

- [ ] `gh api repos/lawrennd/referia/code-scanning/alerts?state=open` shows none of #1–#20 still open
      (fixed, or #12 dismissed with documented rationale)
- [ ] CIP-000E implementation status checkboxes complete
- [ ] CIP-000E status: Implemented, then Closed after you verify
- [ ] Decision recorded: compress into formal docs now or defer

## Implementation Notes

Do not start this task until the other four CIP-000E backlog items are Completed. Auth, TLS, CSRF,
and `/errors` access control remain out of scope (future CIP).

## Related

- CIP: [CIP-000E](../../cip/cip000E.md)
- Code scanning: https://github.com/lawrennd/referia/security/code-scanning

## Progress Updates

### 2026-08-18

Task created when CIP-000E was Accepted. Blocked on the four implementation tasks.
