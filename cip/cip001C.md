---
author: "Neil D. Lawrence"
created: "2026-10-28"
id: "001C"
last_updated: "2026-10-28"
status: "Closed"
compressed: true
related_requirements: ["0014", "0009", "000E"]
related_cips: ["0010", "000C", "000B", "000F"]
tags:
- cip
- web
- catalog
- schedule
- root
- inherit
- filters
- overview
title: "Root-owned schedule with sibling Today and Year overviews"
---

# CIP-001C: Root-owned schedule with sibling Today and Year overviews

> **Note**: CIPs describe HOW to achieve requirements (WHAT).
> Use `related_requirements` to link to the requirements this CIP implements.

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [x] In Progress - Actively being implemented
- [x] Implemented - Work complete, awaiting verification
- [x] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

## Summary

Extend the CIP-0010 tall catalog so **schedule is a root assessment**, not a meaning of leaf `date`. Writable tall columns `due`, `event`, and `notes` join `complete` in `catalog-scores.yml`. A derived `when` (and `on_today`) drives windows. Sibling ordinary configs `today/_referia.yml` and `year/_referia.yml` inherit discovery and scores and only change chrome. `GET /` stays the seasonal list, now windowed on `when`.

This CIP implements [REQ-0014](../requirements/req0014_root-owned-schedule.md). It does not reopen CIP-0010's tall-first decision, does not introduce `mode: catalog`, and does not federate talks or other git roots into the OneDrive tree.

## Motivation

The OneDrive root is already a CIP-0010 catalog: `yaml_directory` discovers descendant `_referia.yml` files, tall scores live in `info/catalog-scores.yml`, `display.layout: inline_list` lists them. Default filters window on leaf `date` in `today±30d` and group by first path segment.

That `date` does not mean one thing. MPhil interviews use it as event day (`date: 2026-10-28`). Other configs use it as opened/cohort identity. About fifteen application configs already declare `due:`, but referia never projects or filters it. Today's interview is therefore in the applications pile, not singled out.

CIP-0010 already treated root **output** as the writable store (`complete`, “later `category`, notes”) and rejected a parallel `_events.yml` dialect. Deadlines belong in that store. Leaf `date` stays identity. Today and Year are the same catalogue instantiated as distinct reviews (template-driven composition), matching the product choice of sibling referias over named presets on `GET /`.

## Detailed Description

### Layering

| Layer | Responsibility |
|-------|----------------|
| Leaf `_referia.yml` | Identity: `title`, `description`, `date` (opened / cohort). Optional leftover `due:` is a seed, not the store. |
| lynguine tall join | Discovery ⋈ `info/catalog-scores.yml` on `configPath`. Per-field `_created` / `_modified` already record last writes. |
| Root output (this CIP) | Writable `complete`, `due`, `event`, `notes`. No write-back into leaf YAML. |
| Compute (view) | `when` = `event` if set else `due`. `on_today` true when `event` or `due` equals today. |
| referia display | Seasonal `/`, Today `/today/`, Year `/year/` — ordinary `_referia.yml`, `inline_list`. |

Aligns with progressive augmentation, explicit–implicit separation, and lynguine's authoritative-store-and-views tenet: the score file is the store; Today/Year are views.

### Package vs config vs lynguine

The first draft of this CIP read as if Today/Year were “just YAML.” That is not true of inherit, grouping, or directory discovery. Split:

**Already works — `_referia.yml` only (OneDrive root + `examples/`):**

- `output.columns: [complete, due, event, notes]` and tall Save of those columns
- `review:` widgets that already exist: `Checkbox`, `Text`, `DatePicker`, `SaveButton`
- `filters:` / `sort:` / `display.filter_defaults` on any tall column (`date_range` and boolean already generic)
- `compute` with `function: today` (ISO `%Y-%m-%d`) and `function: render_liquid` (for `when` / `on_today` if Liquid is enough)
- `GET /today/` and `GET /year/` routing (CIP-000C: a directory with `_referia.yml` loads that config)
- Viewer Liquid links to `/today/` and `/year/`
- Academic-year window as concrete ISO dates (`2026-10-01` … `2027-09-30`), edited once a year
- One-time seed of `info/catalog-scores.yml` (and/or projecting leftover leaf `due:` into input so a Liquid fill can copy empty scores)

**Referia package (not YAML, not lynguine):**

- **`_group: month` and `_group: none`.** Today `_INLINE_LIST_GROUP_BY` is only `{directory, version}`. You cannot group by an arbitrary computed column. Month grouping is display chrome.
- **Inherit of catalog views.** Referia forces `inherit.ignore` to include `compute` and `review` (`referia/config/interface.py` defaults). A child `today/_referia.yml` with `inherit: {directory: ../}` will **not** reuse the parent’s widgets, `when`/`on_today` compute, or review mapping. Sibling views use an explicit opt-in (`inherit.reuse`) so those keys are shared. Candidate-review inherit stays unchanged. Until that lands, Today/Year would have to duplicate the catalog spec — which this CIP rejects.
- DatePicker already stores **`YYYYMMDD`**, not ISO. `date_range` / `today` compute use ISO. Either document that mix and normalise in Liquid, or give DatePicker an ISO option. Do not pretend the widget writes `YYYY-MM-DD`.

**Lynguine (infrastructure; lynguine CIP-0018 in `/Users/neil/lawrennd/lynguine`; referia must not fork):**

- **`yaml_directory` `source[].directory: .` is not rebound on inherit.** `_bind_spec_directory` only rewrites specs that have a `filename`. Catalog input has `directory` + `glob`, no `filename`, so Today would discover from `today/` unless lynguine binds directory sources the same way as filename specs. Output `filename: catalog-scores.yml` *does* bind, so the score file is the easier half.
- **Discovery exclude** (`exclude: [today/**, year/**]`) does not exist. YAML alternative: list work directories as separate `source` entries (`applications`, `marking`, `theses`, …) so `today/` never matches. This CIP keeps auto-discovery of new top-level folders, so exclude lives in lynguine CIP-0018.

**Not a new product mode, not new routing, not a new store dialect.**

### Data model

**Leaf (input projection, read-only)** — keep CIP-0010 fields:

```yaml
fields: [title, description, date, referia_config_version]
```

`date` means when this review instance was opened / which cohort it is. Stop using it as the listing clock. Do not add `due` to the lasting projection except as a **seed source** (below).

**Root store (output, tall, keyed by `configPath`)** — extend columns:

| Column | Meaning | Widget |
|--------|---------|--------|
| `complete` | Done / still active (CIP-0010) | Checkbox |
| `due` | Complete-by (written exercise EOD, REF, supervision) | `DatePicker` (stored `YYYYMMDD`; seed from leaf `due:` truncates `YYYY-MM-DD HH:MM` to a date) |
| `event` | Happens-on (interview day, meeting day) | `DatePicker` |
| `notes` | Short progress line | Text |

Lynguine already emits `complete_created` / `complete_modified`. The same per-field timestamps on `due` and `event` satisfy “see that the deadline moved” without a second audit dialect. Full rewrite history is git of `catalog-scores.yml`.

**Derived view columns (compute, not stored):**

| Column | Rule |
|--------|------|
| `when` | `event` if set, else `due` |
| `on_today` | true iff `event == today` **or** `due == today` |

Seasonal and year **windows and sort** use `when`. Today **filters** on `on_today`. Using only `when == today` would hide a row whose `event` is next week but `due` is today.

Per-candidate times (this afternoon's interviewee) stay inside the interview review. The catalog answers which **reviews** demand attention, not who is at 15:00.

### Seeding (once, then output wins)

Same pattern CIP-0010 used for `complete` vs leaf `current`:

1. On first encounter, if the score row has no `due` and the leaf has `due:`, copy the date into the score row.
2. Do **not** auto-copy leaf `date` into `due`.
3. **Explicit one-time pass** (application tree, not a silent rule): for live interview/meeting configs, seed `event` from leaf `date` where that date is the happens-on day (MPhil interviews on 2026-10-28 are the example).
4. After a value exists in `catalog-scores.yml`, **output wins**. No write-back into leaf `_referia.yml`.

Leaf `due:` may remain as stale documentation; it is not authoritative.

### Sibling referias

`GET /` stays the seasonal overview (root `_referia.yml`). Add two ordinary configs that **share** discovery, scores, compute, and review widgets, and only change chrome (`title`, `display.filter_defaults`, `_group`, viewer links).

That share is **not** today’s default inherit. Referia always ignores parent `compute` and `review`. This CIP’s referia work is an explicit opt-in:

```yaml
writable: true
inherit:
  directory: ../
  filename: _referia.yml
  writable: true
  reuse: [input, output, compute, review, filters, sort]
  ignore: [viewer]
```

`reuse` removes listed keys from `inherit.ignore` **after** the forced `compute`/`review` defaults, so they are inherited. Keys not listed stay ignored. `ignore: [viewer]` keeps the child's chrome (and skips the parent-assessor link injection when `viewer` is ignored). Candidate reviews omit `reuse` and are unchanged.

Lynguine already requires both top-level `writable: true` and `inherit.writable: true` to keep the parent output writable. Today/Year need that so Save writes the shared `catalog-scores.yml`.

**`today/_referia.yml`**

- Inherit the catalog with `reuse` as above (not a bare `inherit: {directory: ../}`).
- Title: Today.
- `filter_defaults`: `on_today: true`, `complete: false` (tristate still available).
- Sort: `when` then `title`. `_group: none` (or equivalent: do not group by directory).
- Same `inline_list` widgets; each row's `config_url` still opens the real review.

**`year/_referia.yml`**

- Same inherit.
- Title: Year.
- Academic-year window on `when`: Cambridge 1 Oct–30 Sep, expressed as relative or computed bounds resolved at session start (e.g. after last 1 Oct, before next 1 Oct, or `today-90d`/`today+270d` only if that is documented as a stand-in — prefer real academic-year bounds).
- `_group: month` so December undergraduate and January PhD/MPhil bursts are visible.
- v1 is `inline_list` + month groups. A calendar-grid named layout is **out of scope** (would be a new REQ-000E composition).

Root (and Today/Year) viewer chrome links to `/today/` and `/year/`. No new product mode.

Talks remain a **separate serve root** (`referia serve --root ~/lawrennd/talks`). Viewer prose may link that calendar. Do not checkout talks under OneDrive in this CIP.

### Implementation traps

#### 0. Referia inherit ignores compute and review

`Interface._process_parent` appends `compute` and `review` to `inherit.ignore` even if the child listed them under `append`. Do **not** stop appending those defaults (candidate reviews rely on it). Accepted HOW: `inherit.reuse` (list of keys). After defaults, each reused key is removed from `ignore`. When `viewer` is ignored, do not inject the parent-assessor link. This is referia, not YAML, and not lynguine CIP-0018.

#### 1. Inherited `.` paths

If Today inherits `input.source.directory: .`, `.` must mean the **parent catalog directory** (the OneDrive root), not `today/`.

Lynguine already binds inherited **filename** specs with `directory: .` to `inherit.directory` (see `test_from_file_inherit_binds_parent_data_directory`). Directory sources (`glob`, no `filename`) are **lynguine CIP-0018**. Referia must not hardcode absolute `$HOME/OneDrive/referia` in the view configs and must not fork `_bind_spec_directory`.

Today and Year must also **share** the parent's `catalog-scores.yml` (same index, same columns). They are views over one store, not extra score files under `today/info/`. Filename output already binds; keep that as a regression once CIP-0018 lands.

#### 2. Do not list the views as work

Root glob `**/_referia.yml` with `include_start_directory: false` still discovers `today/_referia.yml` and `year/_referia.yml`.

**Decision:** exclude by path from discovery. That is **lynguine CIP-0018** `exclude: [today/**, year/**]` on the catalog source, so the view configs stay ordinary YAML. A leaf `discover: false` key is rejected as primary: it teaches lynguine about referia overviews.

`include_start_directory: false` remains necessary so the root file itself is omitted; exclude is the extra nested-view rule. Application YAML lists the patterns; lynguine does not know the names.

#### 3. Month grouping

`_INLINE_LIST_GROUP_BY` in `referia/web/routes.py` is currently `{directory, version}`. Add `month` (from `when`, fallback empty if unparseable) and `none` (flat list). Unknown `_group` still falls back to `directory` for existing configs.

#### 4. Filter bar

Add `when` as a `date_range` filter (seasonal + year defaults). Add `on_today` as a boolean (Today's default). Keep `date` available as identity if authors want it, but it is **not** the default clock. Seasonal `filter_defaults` move from `date: today±30d` to `when: today-30d … today+30d` (or a slightly forward-weighted window if we document it).

### Example root output / review (delta from today's CIP-0010 root)

```yaml
output:
  type: yaml
  index: configPath
  filename: catalog-scores.yml
  directory: ./info
  columns: [complete, due, event, notes]

compute:
  # existing configPath, config_url, depth, today …
  - field: when
    function: coalesce_dates   # or Liquid: event then due
    args: {fields: [event, due]}
  - field: on_today
    function: date_equals_today
    args: {fields: [event, due]}   # OR

review:
  - {type: Checkbox, field: complete, default: false}
  - {type: DatePicker, field: event, args: {description: Event (happens-on)}}
  - {type: DatePicker, field: due, args: {description: Due (complete-by)}}
  - {type: Text, field: notes, args: {description: Progress}}
  - {type: SaveButton}

filters:
  - {field: complete, type: boolean, label: Complete}
  - {field: on_today, type: boolean, label: Today}
  - {field: when, type: date_range, label: When}
  - {field: title, type: contains, label: Title}

sort:
  - {field: when, order: asc}

display:
  layout: inline_list
  filter_defaults:
    complete: false
    when: {after: today-30d, before: today+30d}
    _sort: when:asc
    _group: directory
```

Prefer existing `render_liquid` + `today` over new compute functions. New names (`coalesce_dates`, `date_equals_today`) only if Liquid cannot compare DatePicker `YYYYMMDD` to ISO `today` cleanly. The contract is coalesce + OR-today, not a stored `when` column.

`input.compute` runs while reading the yaml_directory partition, **before** `catalog-scores.yml` is joined, so `row_args: event` / `due` raise. Derive `when` and `on_today` in `WebReviewer.get_value` (and `get_row_data`) from the live output cells plus `today`. Filters, sort, and month grouping then see a view, not a stored column.

### What this CIP does not do

- Does not reopen CIP-0010 tall-first or invent `mode: catalog`.
- Does not write `due` / `event` / `complete` back into leaf YAML.
- Does not auto-copy leaf `date` into `due`.
- Does not add a calendar-grid named layout (REQ-000E follow-on).
- Does not federate talks, teaching, or other git roots into the review catalog (later hub CIP).
- Does not replace per-candidate interview times with catalog `event`.
- Does not add an append-only deadline changelog beyond lynguine field timestamps + git.
- Does not retire leaf `current:` (still CIP-0010 follow-up).

### Alternatives considered

| Approach | Decision |
|----------|----------|
| Keep windowing on leaf `date` | Rejected — overloaded meaning; today's interview is not distinct |
| Project leaf `due:` as the lasting deadline | Rejected — not editable at root; CIP-0010 output is the store |
| Parallel `_events.yml` / schedule dialect | Rejected again — CIP-0010 already rejected a second dialect |
| Named presets on `GET /` only | Rejected by product choice — sibling Today and Year referias |
| Duplicate the catalog spec in `today/` and `year/` | Rejected — define once; requires a referia inherit opt-in instead |
| Bare `inherit: {directory: ../}` | Rejected — referia always ignores parent `compute` and `review` |
| Stop force-appending `compute`/`review` to ignore | Rejected — would change candidate-review inherit; use `inherit.reuse` opt-in |
| Both sibling configs and root presets | Deferred — links from the seasonal viewer are enough |
| `when == today` for the Today view | Rejected — misses due-today / event-later rows |
| Seed `due` from leaf `date` | Rejected — `date` is identity; interviews seed `event` in an explicit pass |
| Checkout talks under OneDrive | Rejected — different store (git vs cloud tree); serve talks separately |
| Mix `markdown_directory` from `~/lawrennd/talks` into the catalog | Rejected — couples two roots; later hub CIP |
| Leaf `discover: false` | Rejected as primary — path exclude on the catalog source |
| Calendar-grid layout in v1 | Rejected — month grouping on `inline_list` shows bursts |
| Full deadline audit log | Rejected — `due_modified` + git of scores is enough |

## Implementation Plan

1. **Requirement + design (this CIP)**
   - REQ-0014 Proposed; this CIP Proposed. Pause for review. No backlog until Accepted.
   - **Done.** Accepted 2026-10-28. Lynguine bind/exclude moved to lynguine CIP-0018. Backlog created in both repos.

2. **Store columns + view compute (YAML, OneDrive + example)**
   - Extend root `output.columns` and `review:` widgets; join still tall on `configPath`.
   - `when` / `on_today` via existing `render_liquid` + `today`; seasonal defaults on `when`.
   - Tests: Save `due` / `event` / `notes`; event-only / due-only / both / neither; DatePicker `YYYYMMDD` vs ISO `today`; leaf YAML unchanged.

3. **Referia inherit opt-in (`inherit.reuse`)**
   - Child can reuse parent `input` / `output` / `compute` / `review` / `filters` / `sort` after the forced ignore.
   - Skip parent-assessor viewer injection when `viewer` is ignored.
   - Default candidate-review inherit unchanged.
   - Tests: Today writes the parent score file; candidate inherit still ignores parent review.

4. **Grouping (referia package)**
   - `_group: month` and `_group: none`.
   - Tests: month buckets from `when`; Today is ungrouped; unknown `_group` still `directory`.

5. **Lynguine CIP-0018 (other repo; do not implement here)**
   - Bind glob/directory sources on inherit.
   - Source `exclude` so `today/**` and `year/**` are not catalog rows.
   - Referia application YAML lists those patterns once CIP-0018 lands.

6. **Application configs (OneDrive tree)**
   - Root viewer links; `today/_referia.yml`; `year/_referia.yml`; seed leaf `due:` into scores; explicit `event` seed for live interviews.
   - Academic-year bounds as ISO dates in the year config.
   - Depends on steps 2–5 and lynguine CIP-0018.

7. **Docs / example**
   - Update `examples/overview_inline_list/` (or a sibling example) so the pattern is reproducible without OneDrive.

## Backward Compatibility

- Existing catalogs that only score `complete` keep working; new columns are optional until the root config declares them.
- Leaf `date` remains projected and can still be filtered; it is no longer the default window.
- Leaf `due:` unread by the package remains unread as authority; seeding copies it once.
- CIP-000C directory listing is unchanged (still reads leaf `date` / `current` as fallback).
- Talks `_referia.yml` is unchanged; its front-matter `date` is already an event.

## Testing Strategy

- Unit: `when` / `on_today`; month grouping; exclude globs; inherit path bind for directory sources.
- Web: root seasonal window uses `when`; `/today/` lists only OR-today rows; `/year/` groups by month; editing `due` on Today updates the shared score file and shows on `/`.
- Regression: CIP-0010 `complete` checkbox, filter clear, `include_start_directory: false`.
- Fixture: a tiny tree with identity `date`, leftover leaf `due:`, an interview `event`, plus `today/` and `year/` views.

## Related Requirements

- [REQ-0014](../requirements/req0014_root-owned-schedule.md) — root-owned timeline; Today and Year reviews
- [REQ-0009](../requirements/req0009_multi-config-web-hosting.md) — one server, path URLs for `/today/` and `/year/`
- [REQ-000E](../requirements/req000E_named-layout-compositions.md) — still `inline_list`; no new named layout in this CIP

## Implementation Status

- [x] REQ-0014 written
- [x] CIP-001C written (Proposed)
- [x] Accepted after review; lynguine work split to lynguine CIP-0018
- [x] Backlog tasks (referia + lynguine)
- [x] Store columns + `when` / `on_today` (YAML) → `2026-10-28_cip001C-catalog-schedule-yaml`
- [x] Referia `inherit.reuse` → `2026-10-28_cip001C-inherit-reuse`
- [x] Month / none grouping → `2026-10-28_cip001C-group-month-none`
- [x] Lynguine bind + exclude → lynguine CIP-0018 (not this repo)
- [x] OneDrive `today/` and `year/` configs + root links + seed → `2026-10-28_cip001C-today-year-configs`
- [x] Example + tests → `2026-10-28_cip001C-example-overview`

## References

- [CIP-0010](./cip0010.md) — tall catalog, `complete`, `inline_list`
- [CIP-000C](./cip000C.md) — root routing; listing fallback
- [CIP-000F](./cip000F.md) — config dialect (ordinary `_referia.yml`)
- lynguine CIP-000F — `yaml_directory`, `include_start_directory`
- lynguine CIP-0018 — inherit bind for glob sources; directory `exclude` (this CIP's lynguine work)
- lynguine inherit bind: `test_from_file_inherit_binds_parent_data_directory`
- Application root: `~/OneDrive/referia/_referia.yml` and `info/catalog-scores.yml`
- Talks calendar (out of scope): `~/lawrennd/talks/_referia.yml`

## Progress Updates

### 2026-10-28

Accepted. Split: referia keeps `inherit.reuse`, `_group: month|none`, and application YAML; lynguine CIP-0018 owns directory-source bind and `exclude`. Backlog created in both repos.

Implemented on worktree branch `cip001C-root-owned-schedule` (depends on sibling lynguine `cip0018-inherited-directory-sources`). OneDrive `today/` and `year/` plus score seeds applied.

Live `/today/` verified 2026-10-28. Folded into the referia checkout; `when` / `on_today` stay a `get_value` view. Compressed into formal docs.

### 2026-10-28 compression

Distilled into formal docs (`compressed: true`):

- `docs/usage/catalog_schedule.rst` — store vs view, `inherit.reuse`, Today/Year, grouping
- `docs/modules/config.rst` — `inherit.reuse` pointer
- `docs/index.rst` — toctree entry
- `README.md` — root-server Today/Year; `inherit` key
- `examples/overview_inline_list/` — miniature catalog with `today/` and `year/`
