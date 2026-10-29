---
id: "2026-10-28_cip001C-today-year-configs"
title: "OneDrive today/ and year/ sibling catalog views plus seed"
status: "Completed"
priority: "High"
created: "2026-10-28"
last_updated: "2026-10-28"
category: "features"
related_cips: ["001C"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-10-28_cip001C-inherit-reuse"
- "2026-10-28_cip001C-group-month-none"
- "2026-10-28_cip001C-catalog-schedule-yaml"
tags:
- backlog
- features
- catalog
- today
- year
- yaml
- cip001C
---

# Task: OneDrive `today/` and `year/` sibling catalog views plus seed

> Linked CIP: 001C. Files live in the OneDrive referia tree (application), not the referia package repo. Soft-depends on lynguine CIP-0018 bind + exclude.

## Description

Add two ordinary configs that inherit the catalog with `inherit.reuse` and only change chrome:

- `today/_referia.yml` — title Today; `on_today: true`, `complete: false`; sort `when`; `_group: none`
- `year/_referia.yml` — title Year; academic-year window on `when` as concrete ISO dates (Cambridge 1 Oct–30 Sep, edited once a year); `_group: month`

Root (and both views) viewer links to `/`, `/today/`, `/year/`. No new product mode. Talks stay a separate serve root.

One-time seed of `info/catalog-scores.yml`:

1. Copy leftover leaf `due:` into empty score `due` (truncate `YYYY-MM-DD HH:MM` to a date)
2. Explicit pass: live interview/meeting configs seed `event` from leaf `date` where that date is happens-on (MPhil 2026-10-28 is the example)
3. Do not auto-copy leaf `date` into `due`
4. After a value exists, output wins; no write-back into leaf YAML

## Acceptance Criteria

- [ ] `GET /today/` lists only rows where `event` or `due` is today; each row's `config_url` opens the real review
- [ ] `GET /year/` lists the academic-year window grouped by month of `when`
- [ ] `GET /` seasonal list windows on `when`, not leaf `date`
- [ ] Today/Year do not appear as catalog rows (parent source `exclude` once lynguine CIP-0018 lands)
- [ ] Editing `due` on Today updates the shared `info/catalog-scores.yml` and shows on `/`
- [ ] Seed pass documented and run once; subsequent Saves do not clobber from leaf `due:` / `date`
- [ ] Talks are not checked out under OneDrive

## Implementation Notes

- Paths: `~/Library/CloudStorage/OneDrive-Personal/referia/today/_referia.yml` and `year/_referia.yml`
- Inherit block from CIP-001C (`writable`, `reuse`, `ignore: [viewer]`)
- Blocked in practice until lynguine `2026-10-28_cip0018-bind-directory-sources` and `…-directory-source-exclude` exist; do not hardcode absolute OneDrive paths as a workaround
- Academic year: e.g. `when: {after: 2026-10-01, before: 2027-09-30}` in the year config, not a rolling `today-90d`

## Related

- CIP: 001C
- lynguine CIP-0018
- Package mirror: `2026-10-28_cip001C-example-overview`

## Progress Updates

### 2026-10-28

Task created (Ready) from CIP-001C acceptance. Implementation waits on inherit.reuse, grouping, catalog YAML, and lynguine CIP-0018.

### 2026-10-28 (later)

Completed: OneDrive `today/` and `year/` configs, root links, score seeds. Live `/today/` verified.
