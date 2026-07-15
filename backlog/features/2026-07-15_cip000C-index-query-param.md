---
id: "2026-07-15_cip000C-index-query-param"
title: "Index and subindex as URL query parameters"
status: "Ready"
priority: "High"
created: "2026-07-15"
last_updated: "2026-07-15"
related_cips: ["000C"]
---

# Task: Index and subindex as URL query parameters

## Description

Move the current primary-index and subindex state from server-side mutation
(`reviewer.set_index()`) into URL query parameters so that record positions
are stateless, shareable, and browser-back-button friendly.

## Acceptance Criteria

- `GET /{config_path}/?index=Kazlauskaite_Ieva` renders that record.
- `GET /{config_path}/?index=3` renders the fourth record (0-based positional).
- `GET /{config_path}/?index=0` renders the first record.
- `GET /{config_path}/?index=-1` renders the last record.
- `GET /{config_path}/` (no `index`) defaults to `index=0`.
- `subindex` follows the same resolution rules and is optional.
- Integer detection: try `int(value)`; if it succeeds treat as positional
  with Python-style negative wrapping (`df.index[n % len(df)]` or
  `df.index[n]` with appropriate bounds check).
- Non-integer strings are treated as label lookups; a missing label returns
  HTTP 404.
- Navigation buttons (Prev / Next / First / Last) update the `index` query
  parameter in the URL rather than posting to a server-side route.

## Implementation Notes

- HTMX `hx-push-url` can be used on navigation buttons to update the browser
  URL bar without a full page reload.
- The existing `reviewer.set_index()` / `reviewer.get_index()` calls inside
  routes should be replaced by resolving the index from the query parameter
  on each request.
- For the single-config mode (no `--root`), this same query-parameter
  convention applies so the single-config server also gains shareable URLs.

## Related

- CIP: 000C
- Task: 2026-07-15_cip000C-path-router
