---
id: "2026-07-15_web-directory-listing-improvements"
title: "Improve root-server directory listing: grouping and metadata"
status: "Proposed"
priority: "Medium"
created: "2026-07-15"
last_updated: "2026-07-15"
related_cips: ["000C"]
---

# Task: Improve root-server directory listing

## Description

The current directory listing (served when a URL path has no `_referia.yml`
but has sub-configs) shows a flat list of paths.  Two improvements are
needed:

1. **Group by subdirectory** — configs should be organised under their
   immediate parent directory as section headings, so a tree like:

   ```
   theses/examined/introduction
   theses/examined/pdfpages
   people/letters
   ```

   renders as:

   ```
   theses/examined/
     • introduction
     • pdfpages
   people/
     • letters
   ```

2. **Show metadata from `_referia.yml`** — each entry should display a
   human-readable title and optionally a short description, extracted
   directly from the YAML file (without loading a full `WebReviewer`).

   Candidate fields to extract (in priority order):
   - `title:` — display name
   - `description:` — one-line summary
   - `allocation.filename` — data file name, as a hint of what's being
     reviewed

## Implementation notes

- Parse each `_referia.yml` with `yaml.safe_load()` for display purposes
  only — do not instantiate `WebReviewer` (expensive).
- Grouping key: the directory path relative to the search base, minus the
  final component (i.e. `theses/examined` groups `introduction` and
  `pdfpages`).
- At the root level (`GET /`) group by top-level directory.
- Render as `<section>` elements with `<h2>` headings and `<ul>` items.
- Keep the existing simple CSS; extend it for sections.

## Acceptance criteria

- Flat list replaced by grouped sections with subdirectory headings.
- Each listing entry shows title (from YAML) or falls back to directory name.
- Optional description displayed as a subtitle where present.
- YAML parse errors for individual configs are silently skipped (show name
  only).
- Unit test: `_list_sub_configs()` returns correct grouping structure.
