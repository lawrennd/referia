---
id: "2026-10-18_web-reviewer-skips-precompute-soft-fill"
title: "WebReviewer never registers review precompute; soft-fill/PDF extract silent on web"
class: 1
owner: "Neil D. Lawrence"
status: "Closed"
created: "2026-10-18"
last_updated: "2026-10-18"
incident_date: "2026-10-18"
spawned_cips: []
spawned_backlog:
  - "2026-10-18_web-reviewer-register-and-run-precompute"
spawned_requirements: []
tags:
  - coe
  - web
  - soft-fill
  - precompute
  - extract_form_fields
  - path-resolution
---

# CoE: WebReviewer never registers review precompute; soft-fill/PDF extract silent on web

> **Correction of Error** (CIP-0016). CoEs are orthogonal to the WHY→WHAT→HOW→DO
> hierarchy. They examine where the hierarchy broke and produce items at the appropriate
> level to fix it. The CoE itself does not implement fixes — it produces outputs (CIPs,
> backlog tasks, requirements, tripwires) that are implemented separately.
>
> Blameless: focus on process, tooling, and design — not people.
>
> Analysis depth: Class 0 may abbreviate Timeline, Incident questions, and 5 Whys.
> Class 1+ should complete them in full.

## Summary

On 2026-10-18, Early Gates Panel configs
(`applications/panel/2026-27/{mphil,phd}/application/`) loaded successfully in
`referia serve` after moving `extract_form_fields` out of `input.compute`, but
review fields that should soft-fill from the Panel PDF (notably **Candidate Email**)
stayed empty. Jupyter registers `type: precompute` specs onto
`CustomDataFrame._precompute` while building widgets; **WebReviewer never does**,
so `compute_pre` on index change is a no-op. Separately, when precompute *does*
run, relative `root: ../files` for extract is resolved against the **serve
process cwd**, not the review directory (WebReviewer already chdirs only around
`from_flow`). Recurrence prevention: web parity tests that a `review:` precompute
soft-fill runs on first open, with cwd pinned to the config directory.

## Severity

**Class**: 1

- Class 0 — Internal only, easily reversible. No user-facing impact.
- Class 1 — Maintainer/contributor workflow impact (not yet externally impactful).
- Class 2+ — External impact: downstream users, deployed behaviour, customer/legal exposure.

**Blast radius**: Any review opened via `referia serve` / WebReviewer that relies
on `review: type: precompute` (or top-level `compute:` run-on-load) for soft-fill,
PDF form extract, or similar. Jupyter Reviewer path unaffected. Panel soft-fill
configs appear to work in YAML but do nothing on the web.

## Impact

Operator reviewing MPhil/PhD Early Gates applications on the web saw a loaded
UI with name/viewer from CSV, but **Candidate Email** (and any other soft-fill
targets driven by precompute) remained blank despite a working
`cam_panel_application.v1` extract against the same PDF. Time lost diagnosing
install extras / pandas `input.compute` dict assignment before finding web
parity gaps. No data corruption; fields simply never suggested.

## Timeline

- 2026-10-18 — Panel `_referia.yml` wired with `extract_form_fields` → `applicant`
  and soft-fill for `given` / `family` / `Candidate Email`
- 2026-10-18 — First load failures: missing PyMuPDF, then
  `ValueError: Incompatible indexer with Series` storing a dict via `input.compute`
- 2026-10-18 — Extract moved to `review` precompute / top-level `compute:`; page
  returns 200
- 2026-10-18 — Operator reports fields not populated in the reviewer UI
- 2026-10-18 — Reproduce: `WebReviewer` has `_precompute == []`; Candidate Email
  `None`; extract with `root: ../files` from serve cwd → `FileNotFoundError`
- 2026-10-18 — Partial code fix started then reverted; CoE + backlog opened first
- 2026-10-18 — After registration+chdir+ensure-columns: extract still logged a
  dict set, but `get_value(applicant)` returned `None` — lynguine
  `_AtAccessor.__setitem__` wrote into empty `output` when the row was
  missing there, while `coltype` still pointed at `cache`

## Evidence / metrics

- `GET /applications/panel/2026-27/mphil/application/` → 200; HTML
  `name="Candidate Email" value=""`
- Direct extract (config-relative root) returns
  `email: salonee.verma.05@gmail.com` for `10947271.pdf`
- `WebReviewer('_referia.yml', cfg_dir)` after load:
  `precompute len 0`; `applicant` column absent; `Candidate Email` is `None`
- Serve cwd resolve: `../files` →
  `/Users/neil/Library/CloudStorage/OneDrive-Personal/files/...` (wrong);
  config-relative → `.../mphil/files/10947271.pdf` (exists)
- Contrast: Jupyter `extract_review` for `type: precompute` extends
  `reviewer._data._precompute` (`referia/assess/review.py`)
- Related prior bug (same cwd class): `2026-10-06_web-localpdf-relative-directory`

## What happened

Soft-fill YAML was correct for the Jupyter compute hook model, but the web path
never registers those hooks and does not chdir when they would run, so PDF
extract/soft-fill silently never populate review widgets.

## Incident questions

### Detection

1. **When did you learn there was impact?**
   - 2026-10-18, when the Panel application page loaded but Candidate Email stayed empty.
2. **How did you learn there was impact?**
   - Operator report after config load was fixed; confirmed by inspecting HTML values
     and constructing `WebReviewer` in a REPL.
3. **How can we reduce the time-to-detect in half?**
   - Add a WebReviewer regression: config with `precompute` soft-fill from a fixture
     path must yield a non-empty field after `__init__` / first `set_index`.

### Diagnosis

4. **What was the underlying cause of the impact?**
   - WebReviewer was built as a no-widget port of Reviewer but precompute/postcompute
     registration (and cwd discipline for compute_pre) were not ported; top-level
     `compute:` is also not auto-run on web load.
5. **Was an internal activity underway during the incident?**
   - Yes — wiring CIP-0013 / cam_panel soft-fill into live Panel 2026-27 configs
     and exercising them under `referia serve`.
6. **How can we reduce the time-to-diagnose in half?**
   - Document in web README / compute soft-fill docs: “precompute runs on web only
     if WebReviewer registers hooks”; log at INFO when `_precompute` is empty but
     `review:` contains `type: precompute`.

### Mitigation

7. **When did impact return to pre-incident levels (or when will it)?**
   - When the spawned backlog task is implemented and Candidate Email soft-fills
     on first open under serve.
8. **How does the owner know the system/process is properly restored?**
   - Unit/integration test green; Panel MPhil URL shows Candidate Email from PDF;
     `_precompute` non-empty after WebReviewer init; relative extract root works
     when serve cwd ≠ config dir.
9. **How did you determine where and how to mitigate?**
   - Diffed Jupyter `extract_review` precompute handling vs WebReviewer init;
     confirmed cwd chdir only wraps `from_flow`, matching the earlier localpdf cwd bug.
10. **How can we reduce the time-to-mitigate in half?**
    - Treat “Jupyter compute hooks” as an explicit WebReviewer parity checklist
      (precompute, postcompute, top-level compute, cwd) whenever adding review
      features that depend on them.

## 5 Whys

1. **Why** was Candidate Email empty on the web?
   - Because soft-fill compute never wrote the field.
2. **Why** did soft-fill never write?
   - Because `_data._precompute` was empty, so `compute_pre` on `set_index` ran nothing.
3. **Why** was `_precompute` empty?
   - Because WebReviewer never walks `review:` for `type: precompute` the way Jupyter does.
4. **Why** was that easy to miss when adding soft-fill to Panel configs?
   - Because the YAML shape matches docs/Jupyter, and the page “loads” (200) with no error.
5. **Why** is there no failing test when precompute is ignored?
   - Because web tests assert precompute clusters are *skipped as widgets*, not that
     their specs are *registered and executed*.
6. *(optional)* **Why** would fixing registration alone still fail extract?
   - Because `compute_pre` would run with serve cwd, so `root: ../files` would not
     find the PDF unless set_index/compute also chdirs to the review directory.
7. *(optional)* **Why** did extract still leave Candidate Email empty after
   registration, chdir, and ensuring the `applicant` cache column?
   - Because lynguine `.at` wrote the dict into an empty `output` frame (missing-row
     branch) while reads used `cache` via colspecs — a second silent failure mode.

**Root cause(s)**: Incomplete Jupyter→web parity for review compute hooks, compounded
by cwd-relative path resolution during compute (same class of bug as web localpdf),
and a lynguine `.at` routing bug when `output` has no rows. Silent success (empty
soft-fill) hid the gaps until an operator noticed missing fields.

## Traceability artifacts missing or incorrect

- [ ] Missing tenet (WHY)
- [ ] Missing requirement (WHAT)
- [ ] Missing CIP (HOW) — web/Jupyter parity for compute hooks not called out as HOW;
      fix is backlog-sized unless recurrence warrants a small CIP
- [x] Missing backlog task (DO) — no task for WebReviewer precompute registration + cwd
- [ ] Incorrect/forbidden link direction
- [x] Template/runtime drift — `_referia.yml` / docs assume precompute runs; web runtime does not
- [x] Other: positive web test covers “skip precompute as widget” but not “execute as hook”

## Follow-up outputs

### Backlog tasks

- [x] Register and run `review` precompute/postcompute (and top-level `compute:`) under
      WebReviewer with review-directory cwd — owner: Neil D. Lawrence —
      `backlog/bugs/2026-10-18_web-reviewer-register-and-run-precompute.md`
- [x] Lynguine: route `CustomDataFrame.at` writes by colspecs (empty output must not
      steal cache) — owner: Neil D. Lawrence —
      `/Users/neil/lawrennd/lynguine/backlog/bugs/2026-10-18_at-setitem-empty-output-steals-cache.md`

### CIPs

- None for now (parity bug; escalate to CIP if multiple hook types need a design pass)

### Requirements

- None

### Validation tripwires

- [x] WebReviewer tests: `test_register_review_computes_copies_precompute_specs`,
      `test_set_index_chdirs_to_review_directory` (serve cwd ≠ config dir) —
      owner: Neil D. Lawrence — shipped in referia PR #27
- [x] Lynguine regression: `test_at_setitem_routes_dict_to_cache_when_output_index_empty`
      — shipped in lynguine PR #42
- [x] Operator validation: Panel MPhil/PhD applications reviewed with soft-fill
      working after merge

## Checklist

- [x] Severity class assigned
- [x] Single-threaded owner named
- [x] Summary written (stand-alone)
- [x] Impact documented
- [x] Timeline documented (required Class 1+; optional Class 0)
- [x] Incident questions answered (Detect / Diagnose / Mitigate)
- [x] 5 Whys completed (abbreviated OK for Class 0; full for Class 1+)
- [x] Missing/incorrect traceability artifacts identified
- [x] Follow-up outputs listed with owners (and created)
- [x] CoE status updated to Analysed once outputs are created
- [x] CoE status updated to Closed once outputs are implemented
