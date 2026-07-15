---
id: "2026-07-15_cip000C-reviewer-cache"
title: "Reviewer cache with mtime invalidation"
status: "Completed"
priority: "High"
created: "2026-07-15"
last_updated: "2026-07-15"
related_cips: ["000C"]
---

# Task: Reviewer cache with mtime invalidation

## Description

In root-server mode, loading a `WebReviewer` from a `_referia.yml` is
expensive (reads Excel files, resolves inheritance, etc.).  Cache reviewers
in a module-level dict keyed by resolved config path and invalidate the
cache entry when the config file's modification time changes.

## Acceptance Criteria

- `app.state.reviewer_cache: dict[str, tuple[float, WebReviewer]]` stores
  `(mtime, reviewer)` pairs.
- On each request, `os.path.getmtime(config_path)` is compared to the cached
  mtime; if it has changed, the reviewer is reloaded.
- Cache misses (first request for a path) load the reviewer synchronously.
- Thread safety: loading is synchronous (uvicorn default worker model);
  no explicit locking needed for single-worker deployments.

## Implementation Notes

- Only the `_referia.yml` mtime is checked; changes to inherited configs or
  referenced data files are not detected automatically (acceptable limitation
  for v1).
- Provide a `GET /?action=reload` or similar endpoint to force a cache clear
  for a specific config during development.

## Related

- CIP: 000C
- Task: 2026-07-15_cip000C-path-router
