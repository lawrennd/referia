---
id: "0013"
title: "A review session's Python runtime can restart without stopping the web server"
status: "Proposed"
priority: "High"
created: "2026-10-24"
last_updated: "2026-10-24"
related_tenets:
- user-oriented-convenience
- explicit-implicit-separation
- progressive-augmentation
stakeholders:
- Reviewers
- Review authors
- Developers
tags:
- requirement
- web
- kernel
- process-isolation
- restart
---

# REQ-0013: A review session's Python runtime can restart without stopping the web server

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Reviewers and authors must be able to discard a review session's Python runtime and start a fresh one while the web server stays up. The HTTP layer that serves the page, static assets, and other configs must remain responsive. A hung compute, a stale imported function, or a corrupted in-memory session on one config must not take down the browser UI or other loaded configs.

This is independent of reloading data from disk. Today's Reload action refreshes flows; it does not give a new interpreter. Reviewers need the stronger outcome: a new Python process for that session, with compute functions reimported from source.

**Why this matters**: *User-oriented convenience* — Jupyter users already restart a kernel without killing the notebook server; the web path should not be weaker. *Explicit–implicit separation* — display stays in the application HTTP layer; session Python is an explicit runtime, not hidden inside request handlers. *Progressive augmentation* — this is a referia web concern, not a lynguine change and not a Jupyter dependency.

**Who benefits**: Reviewers iterating on compute functions and `_referia.yml`; authors debugging hung LLM or PDF work; anyone using the CIP-000C root server with more than one config, who currently share one process.

## Acceptance Criteria

- [ ] A reviewer can restart one config's Python session without stopping the web server process
- [ ] After restart, that session's compute functions are the current source on disk, not the previously imported module objects
- [ ] A compute that hangs in one session does not prevent the server from serving other configs or accepting a restart for the hung session
- [ ] Restarting one config does not discard another config's in-memory session
- [ ] Reloading data from disk remains available and remains distinct from restarting the Python runtime
- [ ] The outcome does not require Jupyter, a notebook kernel, or any Jupyter protocol

## Notes

The YAML widget that *triggers* restart (a Restart button in `_referia.yml`) is a later, smaller outcome. This requirement is the runtime property that such a button would use. Complementary HTTP-layer reload (`referia serve --reload`) is also distinct: that restarts the server process, not a single session.

## References

- Tenet: [user-oriented-convenience](../tenets/referia/user-oriented-convenience.md)
- Tenet: [explicit-implicit-separation](../tenets/referia/explicit-implicit-separation.md)
- Tenet: [progressive-augmentation](../tenets/referia/progressive-augmentation.md)
- Related: [REQ-0008](./req0008_web-review-without-jupyter.md), [REQ-0009](./req0009_multi-config-web-hosting.md), [REQ-000B](./req000B_web-security-untrusted-paths.md)

## Progress Updates

### 2026-10-24

Requirement created (Proposed). Paired with CIP-001B (Jupyter-like kernel/server process split).
