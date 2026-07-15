---
id: "2026-07-15_web-directory-listing-improvements"
title: "Improve root-server directory listing: grouping, metadata, navigation, and filters"
status: "Completed"
priority: "Medium"
created: "2026-07-15"
last_updated: "2026-07-15"
related_cips: ["000C"]
---

# Task: Improve root-server directory listing

## Description

Enhanced the directory listing page (served when a URL path has no
`_referia.yml` but has sub-configs) with four features:

1. **Group by subdirectory** — configs are organised under their immediate
   parent as collapsible section headings (each heading is itself a clickable
   link to that subdirectory's listing), e.g.:

   ```
   theses/examined/
     • introduction
     • pdfpages
   people/
     • letters
   ```

2. **Metadata from `_referia.yml`** — each entry shows `title`, optional
   `description`, `date` (ISO string), and a green `current` badge when
   `current: true`.  Extracted via `yaml.safe_load` without loading
   `WebReviewer`.

3. **`..` parent navigation** — every listing page below the root includes an
   up-arrow link to the parent directory so users can navigate back up the
   tree without touching the browser's back button.

4. **Filter bar** — a compact form at the top of every listing page allows
   filtering by:
   - **After / Before** date range (`<input type="date">` fields)
   - **Current only** checkbox (hides configs where `current:` is absent or
     false)

   Filters are submitted as `GET` query params (`?after=…&before=…&current=1`)
   so the filtered URL is bookmarkable.  Configs with no `date` field pass
   through date filters unchanged.  If a filter empties the list the form
   remains visible so the user can clear it; a genuine absence of sub-configs
   still produces a 404.

## Implementation notes

- `_read_config_meta()` extended to read `date` and `current` fields.
- New `_filter_configs()` helper applies after/before/current_only criteria.
- `_render_directory_listing()` signature extended with `after`, `before`,
  `current_only` keyword args; renders parent link, filter form, grouped
  sections.
- `GET /` (root listing) and `GET /{config_path}` (intermediate listing) both
  accept and thread through `after`, `before`, `current` query params.

## Acceptance criteria

- [x] Flat list replaced by grouped sections with clickable subdirectory headings.
- [x] Each entry shows title (from YAML) or falls back to directory name.
- [x] Description displayed as a subtitle where present.
- [x] Date shown inline; `current` badge shown for current entries.
- [x] `..` link present on all listing pages except the root.
- [x] Filter form present on all listing pages with date range and current-only controls.
- [x] Date filters exclude entries outside the range; undated entries pass through.
- [x] Current-only filter hides entries where `current` is false or absent.
- [x] YAML parse errors for individual configs are silently skipped.
- [x] Tests cover parent link, date display, current badge, filter exclusion, and form presence.
