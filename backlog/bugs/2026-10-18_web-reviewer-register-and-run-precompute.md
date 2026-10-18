---
id: "2026-10-18_web-reviewer-register-and-run-precompute"
title: "WebReviewer must register review precompute/postcompute and run them with config-dir cwd"
status: "In Progress"
priority: "High"
created: "2026-10-18"
last_updated: "2026-10-18"
category: "bugs"
related_cips: []
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- bug
- web
- soft-fill
- precompute
- extract_form_fields
- path-resolution
- CoE
---

# Bug: Register and run review precompute under WebReviewer

> Backlog tasks are DOING the work defined in CIPs / CoE follow-ups (HOW→DO).
> Spawned by CoE `coe/2026-10-18_web-reviewer-skips-precompute-soft-fill.md`.

## Description

Jupyter `Reviewer` registers `review: type: precompute` (and `postcompute`)
specs onto `CustomDataFrame._precompute` / `_postcompute` in `extract_review`.
`set_index` then calls `compute_pre`, which runs those specs for the active row.

**WebReviewer never registers those hooks.** `_flatten_entries` only expands
precompute clusters so they are not rendered as widgets
(`test_precompute_cluster_skipped`); it does not copy specs onto `_precompute`.
Result: soft-fill and `extract_form_fields` in Panel configs are a silent no-op
on `referia serve`.

Additionally, `WebReviewer` chdirs to the review directory only around
`from_flow`. `set_index` → `compute_pre` runs with the **serve process cwd**, so
relative extract roots such as `root: ../files` resolve incorrectly (same class
of bug as `2026-10-06_web-localpdf-relative-directory`).

Top-level interface `compute:` is also not auto-run on web load (Jupyter often
triggers it via other paths). Soft-fill listed only under `compute:` will not
run on first open unless we either run it after init or rely on registered
precompute.

Observed on Early Gates 2026-27 MPhil/PhD application reviews: page 200, name
from CSV, **Candidate Email** empty despite successful PDF extract when cwd/root
are correct.

## Acceptance Criteria

- [x] On `WebReviewer` init (and reload), walk `review:` (including nested
      cluster/`load` children as needed) and register `type: precompute` /
      `postcompute` specifications onto `_data._precompute` / `_postcompute`
      (parity with Jupyter `extract_review`).
- [x] `set_index` (and thus `compute_pre` / `compute_post`) runs with cwd = review
      directory so relative paths in compute args (`root: ../files`, etc.) resolve
      like Jupyter / like `run_populate`.
- [x] Top-level `_referia.yml` `compute:` runs once for the active index after
      first `set_index` (and after reload), also under review-directory cwd — or
      document and test an equivalent guaranteed path for soft-fill on load.
- [x] Soft-fill + `extract_form_fields` into an intermediate object field (e.g.
      `applicant` dict) then liquid into `Candidate Email` works when the column
      is new (ensure via `__setitem__` / cache; depends on lynguine
      `2026-10-18_at-setitem-empty-output-steals-cache`).
- [x] Unit tests: `test_register_review_computes_copies_precompute_specs`,
      `test_set_index_chdirs_to_review_directory`; existing
      `test_precompute_cluster_skipped` still passes.
- [x] Manual/REPL check: WebReviewer on Panel MPhil yields
      `Candidate Email` from PDF (`salonee.verma.05@gmail.com`).
- [x] Open PRs for referia `web_review.py` + lynguine AtAccessor fix; re-check
      live `referia serve` URL after merge.

## Implementation Notes

Suggested shape (do not treat as the only design):

1. `_register_review_computes()` after `from_flow`, before first `set_index`.
2. Wrap `set_index` body in `os.chdir(self._directory)` (mirror `run_populate`).
3. `_run_interface_compute()` for top-level `compute:` after first index is set.
4. Re-register on `reload_data`.

**Column creation:** storing `extract_form_fields` dict into a new `applicant`
column may hit
`KeyError: Attempting to add column "applicant" as a set request has been given
to non existent column.` if autocache / mutable write path does not create the
column. Fix within this task (ensure column exists / use write path that allows
new object columns) or spawn a follow-on bug if the root cause is lynguine-wide.

**Out of scope:** changing `input.compute` to accept dict returns (separate
pandas/`finalize_data` issue); promoting `documents` extras (already handled in
`pyproject.toml`).

## Related

- CoE: `coe/2026-10-18_web-reviewer-skips-precompute-soft-fill.md`
- Similar cwd bug: `2026-10-06_web-localpdf-relative-directory`
- Code: `referia/assess/web_review.py`, `referia/assess/review.py` (`extract_review`)
- Configs: `applications/panel/2026-27/{mphil,phd}/application/_referia.yml`
- Lynguine soft-fill docs: `docs/compute_framework.md`

## Progress Updates

### 2026-10-18

Task created from CoE after Panel soft-fill diagnosis. Partial `web_review.py`
patch reverted so implementation proceeds from a clean baseline once Ready work
starts.

### 2026-10-18 (implementation)

- `WebReviewer`: register precompute/postcompute, chdir on `set_index`, ensure
  compute target columns via `__setitem__`, run top-level `compute:` after first
  index.
- Lynguine fix required: `_AtAccessor` was writing dicts into empty `output`
  (`backlog/bugs/2026-10-18_at-setitem-empty-output-steals-cache` in lynguine).
- REPL smoke: Candidate Email soft-fills from `10947271.pdf`. Live serve URL
  check + git commits still pending.
