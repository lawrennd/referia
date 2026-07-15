---
id: "2026-07-15_cip000C-landing-page"
title: "Landing page listing all configs under root"
status: "Ready"
priority: "Medium"
created: "2026-07-15"
last_updated: "2026-07-15"
related_cips: ["000C"]
---

# Task: Landing page listing all configs under root

## Description

When the server is started with `--root`, `GET /` renders a discovery page
listing all `_referia.yml` files found recursively under the root directory.
Each entry is a link to the corresponding config URL, labelled with the
config's `title:` field if present, otherwise the directory path.

## Acceptance Criteria

- `GET /` in root-server mode returns HTML with one link per discovered config.
- Links use the canonical URL form (directory path, no `_referia.yml` suffix).
- Each link label shows the `title:` from the YAML frontmatter if available,
  otherwise the relative path.
- Configs are sorted alphabetically by path.
- Hidden directories (names starting with `.`) are excluded from the scan.
- In single-config mode `GET /` continues to serve the review interface as today.

## Implementation Notes

- The YAML `title:` can be read by parsing only the frontmatter (first few
  lines up to the second `---`) without loading the full config, keeping the
  landing page fast.
- Consider caching the list of configs with a short TTL or rebuilding on
  each `GET /` (acceptable for infrequent access).

## Related

- CIP: 000C
- Task: 2026-07-15_cip000C-create-app-root-refactor
