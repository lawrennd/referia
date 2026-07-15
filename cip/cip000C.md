---
author: Neil D. Lawrence
created: "2026-07-15"
last_updated: "2026-07-15"  # refined URL scheme and index query parameter spec
status: Accepted
related_requirements: []
related_cips: ["000B"]
tags: ["web", "multi-config", "routing", "ecosystem", "architecture"]
compressed: false
---

# CIP-000C: Multi-Config Web Server (Root-Based Path Routing)

## Status

- [x] Proposed
- [x] Accepted
- [ ] In Progress
- [ ] Implemented
- [ ] Closed
- [ ] Rejected
- [ ] Deferred

## Summary

Replace the current single-config web server model (one `uvicorn` process per
`_referia.yml`) with a root-based server that can serve any `_referia.yml`
found under a configurable root directory.  Each config is addressable by its
filesystem path, exposed as a URL path on the same server:

```
http://127.0.0.1:8765/theses/examined/introduction/
http://127.0.0.1:8765/people/letters/
http://127.0.0.1:8765/people/achievements/
```

This enables cross-linking between related referia instances — parent configs,
inherited relationship data, sibling reviews — using plain HTML links rather than
requiring users to manage multiple server processes on different ports.

## Motivation

The referia ecosystem consists of many `_referia.yml` configurations that
reference each other through `inherit:` chains, viewer Liquid templates, and
document links.  For example:

- `people/letters` inherits from `people/achievements`
- `people/achievements` inherits from `people/relationship`
- Viewer panels in one config show links to Google Docs or other referia
  instances for the same person

In the Jupyter interface, navigating between these is handled by opening different
notebooks.  In the current web interface there is no equivalent: each `referia serve`
command hardcodes a single config, and cross-linking is impossible without
managing a separate server process (and knowing its port) for each config.

The single-process-per-config model also means no "landing page" exists to
discover what configs are available under a root.

## Detailed Description

### URL scheme

The server is started with a `--root` directory (defaulting to the current working
directory when `--root` is omitted):

```bash
referia serve --root ~/OneDrive/referia/ --port 8765
```

URL paths map to config file locations relative to the root:

```
GET /theses/examined/introduction/   →  {root}/theses/examined/introduction/_referia.yml
GET /people/letters/                 →  {root}/people/letters/_referia.yml
GET /                                →  landing page listing available configs
```

The trailing slash is canonical; the config filename defaults to `_referia.yml`
and is normally omitted from the URL.  When a non-default config filename is
used, it can be specified explicitly:

```
GET /theses/examined/introduction/_referia_draft.yml
```

This allows projects that maintain multiple named config files in the same
directory to address each one directly.

### Index as a query parameter

The current record is specified via an `index` query parameter:

```
GET /people/letters/?index=Kazlauskaite_Ieva          # label value
GET /people/letters/?index=3                           # positional (0-based integer)
GET /people/letters/?index=0                           # first record
GET /people/letters/?index=-1                          # last record
```

Resolution rules:
1. If `index` is an integer (including negative), treat as a positional offset
   into the DataFrame's index: `0` → first, `-1` → last, `n` → `df.index[n]`.
2. Otherwise treat as a label and look it up directly.
3. If absent, default to the first record (`index=0`).

The `subindex` query parameter follows the same convention for subseries navigation:

```
GET /people/letters/?index=Kazlauskaite_Ieva&subindex=2026-06-01
```

### State per config

Each config is an independent reviewer session.  State (current primary index,
current subindex) is encoded in the URL query string so that links are
shareable and the browser back button works:

```
GET /people/letters/?index=Kazlauskaite_Ieva
```

This replaces the current server-side `reviewer.set_index()` mutation with a
stateless request model.

Alternatively (simpler first pass): keep server-side state per config using a
dict keyed by config path, accepting the limitation that concurrent sessions
on the same server share state.

### Cross-linking

Viewer Liquid templates can produce links using the relative URL path:

```yaml
viewer:
- liquid: |
    [Achievements](/people/achievements/?index={{Name}})
    [Relationship](/people/relationship/?index={{Name}})
```

Since all configs are served from the same origin, these are plain relative
links with no CORS or port concerns.

### Landing page

`GET /` renders a directory listing of all `_referia.yml` files found under
the root, grouped by subdirectory, with the config `title:` shown as the
link label.

### Backward compatibility

- When started without `--root`, the server behaves identically to today:
  it looks for `_referia.yml` in the current working directory and serves
  only that config at `/`.
- The existing CLI interface (`referia serve`) is preserved; `--root` is an
  additive option.
- Existing `_referia.yml` files require no changes.

## Implementation Plan

1. **Refactor `create_app()`** — accept an optional `root` directory in addition to
   `user_file`/`directory`.  When `root` is provided, do not pre-load a reviewer at
   startup; instead load (and cache) reviewers on first request for each path.

2. **Add path router** — a catch-all route `GET /{config_path:path}` resolves the
   path to a `_referia.yml`, loads (or retrieves from cache) the `WebReviewer`, and
   renders the review panel.  All existing routes (`/field/{col}`, `/save`, `/record`,
   etc.) become sub-routes scoped under the config path prefix.

3. **Reviewer cache** — a module-level dict `{resolved_path: WebReviewer}` so configs
   are only loaded once per server lifetime.  Invalidation: reload on request if the
   `_referia.yml` mtime has changed.

4. **Landing page** — `GET /` scans the root for `_referia.yml` files and renders an
   index page.

5. **State in URL** — pass `index` and optionally `subindex` as query parameters.
   Accepted forms:
   - Integer (including `-1` for last, `0` for first) → positional lookup via
     `df.index[n]`, with Python-style wrapping for negatives.
   - Non-integer string → label lookup.
   - Absent → default to `index=0`.
   The config filename in the URL path defaults to `_referia.yml`; a non-default
   name (e.g. `_referia_draft.yml`) can be appended to the path explicitly.

6. **CLI update** — add `--root` option to `referia serve`; update `app.py` factory.

7. **Tests** — extend `test_web_routes.py` to cover path-based config resolution and
   the landing page.

## Backward Compatibility

- Single-config mode (no `--root`) is unchanged.
- No changes to `_referia.yml` format.
- The HTML structure rendered per-config is identical to today.

## Testing Strategy

- Unit test: path-to-filesystem resolution (relative paths, traversal rejection).
- Integration test: loading two different configs in the same test client and
  verifying that their state is independent.
- Integration test: landing page lists configs with correct titles.
- Existing `test_web_routes.py` tests should continue to pass against the
  single-config mode.

## Related Requirements

None formalised yet.

## Implementation Status

- [ ] Refactor `create_app()` to support optional root
- [ ] Add catch-all path router
- [ ] Reviewer cache with mtime invalidation
- [ ] Landing page
- [ ] State in URL: `index` and `subindex` query parameters (label or integer, `-1`/`0` for last/first)
- [ ] Non-default config filename support in path (e.g. `_referia_draft.yml`)
- [ ] CLI `--root` option
- [ ] Tests

## References

- CIP-000B: Web Display System — Non-Jupyter Rendering Backend (the existing
  single-config web server this CIP extends)
- Backlog: `2026-07-14_web-inherit-not-applied.md` — the inheritance issue that
  motivates cross-linking between configs
- Backlog: `2026-07-14_web-subseries-selector.md`
