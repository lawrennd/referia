---
author: "Neil D. Lawrence"
created: "2026-10-06"
id: "000F"
last_updated: "2026-10-06"
status: "Closed"
compressed: true
related_requirements: []
related_cips: ["000A", "000B", "000C"]
tags:
- cip
- yaml
- migration
- config
- versioning
- compatibility
title: "Detect, version, and migrate referia config dialects"
---

# CIP-000F: Detect, version, and migrate referia config dialects

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [x] In Progress - Actively being implemented
- [x] Implemented - Work complete, awaiting verification
- [x] Closed - Verified and complete
- [ ] Rejected
- [ ] Deferred

## Summary

Make the referia `_referia.yml` dialect explicit. Today `Interface.__init__`
silently rewrites convenience keys (`allocation`, `scores`, `scorer`, …) into
lynguine form. That conversion becomes a named detector and normaliser, with
CLI support to stamp versions and optionally rewrite keys, and a
`referia_config_version` field so files state which dialect they use.

Rollout is phased: **detect → stamp living configs → warn → error on missing
version**. This CIP does **not** silently rewrite user YAML on load.

## Motivation

Referia began as REF 2021 review tooling (UOA 11, June–December 2021). The
surviving configs under `~/Documents/ref` still use the original convenience
keys. `Interface` already converts those keys in memory, so the dialect is
understood — but the conversion is implicit, unversioned, and not reversible
to a file the user can inspect.

Three problems follow:

1. **Detection is mixed into construction.** There is no function that can
   answer “is this file old-format?” without mutating a dict. `referia check`
   only validates YAML parse, not dialect.
2. **Files on disk stay in the old dialect** while the running system thinks
   in lynguine keys. Reviewers and agents cannot tell which form they are
   editing. Deprecation warnings fire only for `scorer`, not for `allocation`
   or `scores`.
3. **Silent write-back would be harmful.** These files contain hand-written
   Liquid, HTML criteria, and comments. Rewriting on load would strip
   formatting and surprise users. Conversion of *keys* is also not the same
   as making a 2021 layout load: parent-directory `$HOME/...` paths still hit
   lynguine path confinement.

The REF configs showed that a detector is feasible: 11/11 files parse, and
hand-constructed `Interface(data=...)` converts them. What is missing is an
explicit, testable, versioned migration path.

This aligns with *Handle implicit behavior explicitly in the application
layer* and *Just work, make it easy for humans*: keep load-time conversion so
old files still run, but name it, report it, and only rewrite when asked.

## Detailed Description

### What “old format” means

There are several layers. This CIP versions **config dialect**, not widget
types, not data-file format (Excel vs YAML is CIP-000A), and not path policy.

| Layer | Markers | Auto-convert? |
|---|---|---|
| **Dialect v0 (proto)** | `_config.yml` with `datadirectory` / `allocation:` as a filename string (June 2021) | No. Report only. Too incomplete. |
| **Dialect v1 (referia convenience)** | Top-level `allocation`, `additional`, `scores`, `scorer`, `global_consts`, `globals`; optional `converters` instead of `dtypes` | Yes, in memory. Optional write via migrate. |
| **Dialect v2 (canonical)** | `input` / `output` / `review` (plus referia extras: `viewer`, `combinator`, `localpdf`, `editpdf`, `urls`) | Already canonical. Stamp version if missing. |
| **Layout, not dialect** | `directory: $HOME/...` pointing *outside* the config folder | Out of scope. Path jail is lynguine; see Related. |
| **Viewer templates** | `display: "{field}"` vs `liquid: "{{field}}"` | Do not auto-rewrite. Both remain valid. |
| **Notebook API** | `rf.assess.Data()` vs `rf.data.Data()` / `Reviewer` | Out of scope (code, not YAML). |

A file is **v1** if any v1 marker key is present at the top level (or
`converters` appears on a data spec). A file is **v2** if it has `input` or
`review` (or `output`) and none of the v1 marker keys. Unlabelled v2 files are
current canonical YAML without a version stamp.

Mixing v1 and v2 keys that name the same slot (`allocation` with `input`,
`scores` with `output`, `scorer` with `review`) remains an error, as today.

### Version field

Add a top-level integer:

```yaml
referia_config_version: 2
```

Rules:

- **Integer, not semver.** This labels dialect generations, not referia
  package releases. Package `0.x` can still load v1 files.
- **Stamp before enforce.** Living configs get a machine-wide stamp-only
  pass (insert version, leave all other keys alone). After that pass,
  missing version becomes a warning, then an error (see rollout below).
- **Stamp on migrate / stamp-only, not on load.** Loading a v1 file
  converts in memory and does not write `referia_config_version` back.
- **Unknown future version** (`referia_config_version` > current supported):
  warn and refuse to guess, unless a `--force` migrate flag is added later.
- **Do not put the field in lynguine.** It is a referia convenience label.
  Strip or ignore it before calling `super().__init__` if lynguine would
  treat unknown keys strictly.

Current supported version after this CIP: **2**.

### Rollout: stamp then enforce

| Phase | Action | Missing version |
|---|---|---|
| 1. Detect + normalise | Library + `check` report dialect | Allowed (inferred) |
| 2. Stamp-only | `referia migrate --stamp-only --write` over living roots | Insert `1` or `2` surgically |
| 3. Warn | After stamp corpus is done | `check` / load warn |
| 4. Error | Package bump after grace period | `Interface` raises unless `--allow-unversioned` |

Stamp-only must prefer a **surgical insert** (ruamel.yaml or line insert at
top / after frontmatter) so comments and key order survive. A full PyYAML
dump of ~270 OneDrive configs is unacceptable for this phase.

A stamped v1 file is still v1 on disk; load still normalises in memory.
Full key rewrite (`allocation` → `input`, etc.) remains a separate opt-in
migrate mode.

### Detector (read-only)

New module, e.g. `referia/config/dialect.py`, with a pure function:

```python
detect_config_dialect(data: dict) -> DialectReport
```

`DialectReport` includes:

- `version_declared` — int or `None`
- `version_inferred` — 0, 1, or 2
- `markers` — which old keys were found
- `conflicts` — mixed v1/v2 slots
- `needs_normalise` — True if in-memory conversion would change keys
- `notes` — converters vs dtypes, proto `_config.yml`, etc.

No I/O. Safe to call from `referia check`, tests, and `Interface`.

### Normaliser (in-memory, existing behaviour extracted)

Extract the key rewrites already in `Interface.__init__` into:

```python
normalise_referia_config(data: dict) -> dict
```

This is the same mapping as today:

- `allocation` (+ `additional`) → `input` (hstack of vstack)
- `scores` → `output`
- `scorer` → `review` (keep the deprecation warning until files migrate)
- `global_consts` → `constants`
- `globals` → `parameters`
- `converters` → `dtypes` on data specs (if still accepted by lynguine under
  the old name, rewrite to the current name)

Then `Interface.__init__` calls detect + normalise **before** template
expansion and `super().__init__`. Construction stays the convenience layer;
the steps become explicit and unit-testable without Excel files.

Do **not** expand `CriterionComment*` in the migrate writer unless we decide
expanded widgets are the on-disk form. Recommendation: **leave composites
unexpanded on disk**. Expansion is a runtime convenience. Writing the
expanded form would make configs huge (the REF environment original file is
the cautionary example).

### On-disk migrate (opt-in)

Extend the CLI:

```bash
referia check --root PATH
referia migrate --root PATH --stamp-only          # dry-run stamp
referia migrate --root PATH --stamp-only --write  # surgical insert
referia migrate --root PATH                       # dry-run full rewrite
referia migrate --root PATH --write               # rewrite keys → v2
```

**`--stamp-only --write`:** insert `referia_config_version: N` where N is
inferred; do not change any other keys. Skip files that already declare a
version. Skip / report v0 proto files.

**Full rewrite `--write`:**

1. Parse YAML.
2. If inferred version is 0, skip with an error for that file.
3. If already v2 keys, set stamp only (same as stamp-only).
4. If v1 keys, apply `normalise_referia_config`, set
   `referia_config_version: 2`.
5. Default sibling `_referia.migrated.yml`; `--in-place` with `.bak`.

Full rewrite may use a dump that loses comments — document that; stamp-only
must not.

Dry-run is the default so `referia migrate --root ~/Documents/ref` can show
what would happen without touching files.

### What `referia check` should report

After this CIP, `check` reports three classes:

1. YAML parse errors (existing)
2. Dialect: v0 / v1 unlabelled / v1 stamped / v2 unlabelled / v2 stamped / mixed
3. Conflicts that would raise in `Interface`
4. After phase 3: missing version as warning; after phase 4: as error

It should not require Excel or path access. Path-jail failures stay a load
error, not a dialect error.

### Runtime vs disk (decision)

| Action | When | Writes files? |
|---|---|---|
| Detect | `check`, `migrate`, tests | No |
| Normalise in memory | Every `Interface` load of v1 | No |
| Stamp-only | `migrate --stamp-only --write` | Yes, opt-in surgical |
| Full key rewrite | `migrate --write` (without stamp-only) | Yes, opt-in |

Automatic conversion **on load** continues so 2021 files keep working once
construction and path issues are fixed. Automatic conversion **on disk** does
not.

### Related bugs (out of scope for dialect migrate, but blocking REF replay)

These are not dialect problems. Track as separate backlog:

1. **`Interface.from_file` kwargs.** lynguine now passes `allowed_roots` and
   `unbounded_paths` into `cls(...)`. Referia’s `Interface.__init__` does not
   accept them, so `WebReviewer` and `referia.data.Data()` fail for *all*
   configs. Fix by forwarding `**kwargs` to `super().__init__`.
2. **Path confinement.** v1 files often set `directory: $HOME/Documents/ref`
   from a subdirectory. lynguine jails reads to the config directory.
   Migrating keys does not fix that.

### Alternatives considered

- **Keep silent conversion only.** Cheap, already works for `Interface(data=)`.
  Rejected as the long-term story: agents and `check` cannot see dialect, and
  `scorer` deprecation never finishes.
- **Require version field immediately.** Would break every existing
  `_referia.yml` in OneDrive. Rejected in favour of stamp-then-enforce.
- **Allow missing version forever.** Rejected; after stamp, missing version
  should become an error so new files follow practice.
- **Rewrite on load.** Violates user control of YAML; loses comments.
  Rejected.
- **One version number tied to package version.** Config dialect changes
  slower than the package. Rejected.

## Implementation Plan

1. Detector + `DialectReport` (unit tests with synthetic v1/v2 fixtures)
2. Extract `normalise_referia_config`; wire into `Interface`
3. `referia check` dialect reporting (incl. JSON)
4. `referia migrate --stamp-only` with surgical write
5. Machine-wide stamp pass over living roots (OneDrive referia, Documents/ref)
6. Phased enforce: warn, then error on missing version
7. Optional full key-rewrite migrate mode
8. Compress docs after CIP close

## Backward Compatibility

- v1 files continue to load via in-memory normalise (same as today).
- No file is rewritten unless the user runs `migrate --write` / `--stamp-only --write`.
- Until phase 4, missing version still loads (with inference / warn).
- After phase 4, missing version errors; escape hatch `--allow-unversioned`.
- Widget expansion behaviour unchanged.

## Testing Strategy

- Unit tests for detect/normalise without personal REF data (synthetic key
  shapes only).
- Round-trip: normalise(v1) detects as v2.
- Stamp-only tests: comments preserved; version inserted; keys unchanged.
- CLI: `check` JSON includes dialect; migrate dry-run does not write.
- Do not add UOA 11 workbooks to the repo.

## Related Requirements

No numbered requirements file yet for config dialect. If we add one later,
it should state: “A `_referia.yml` declares or can be inferred as a known
referia config dialect; after the stamp corpus, new files must declare a
version.”

Tenets: `explicit-implicit-separation`, `user-oriented-convenience`.

## Implementation Status

Backlog tasks created on acceptance (2026-10-06):

- [x] Detector and report dataclass — `backlog/features/2026-10-06_cip000F-detect-dialect.md`
- [x] Extract in-memory normaliser from `Interface` — `backlog/features/2026-10-06_cip000F-extract-normaliser.md`
- [x] `referia check` dialect reporting — `backlog/features/2026-10-06_cip000F-check-dialect-report.md`
- [x] `referia migrate --stamp-only` (surgical) — `backlog/features/2026-10-06_cip000F-migrate-stamp-only.md`
- [x] Machine-wide stamp of living `_referia.yml` trees — `backlog/infrastructure/2026-10-06_cip000F-stamp-machine-configs.md`
- [x] Warn then error on missing version — `backlog/features/2026-10-06_cip000F-enforce-version.md`
- [x] Full key-rewrite migrate mode — `backlog/features/2026-10-06_cip000F-migrate-rewrite.md`
- [x] Related bug: `Interface.from_file` kwargs — `backlog/bugs/2026-10-06_interface-from-file-kwargs.md`
- [x] Tests and fixtures (synthetic v1/v2 YAML) — `referia/tests/test_config_dialect.py`
- [x] Related: dialect-aware `strict_columns` defaults — `backlog/bugs/2026-10-06_strict-columns-duplicate-excel-headers.md`

### 2026-10-06 validation (close)

- Dialect unit tests and `TestStrictColumnsDefault`: **26 passed**.
- Stamped v1 REF configs load without an explicit `strict_columns: false`.
- Referia `_resolve_strict_columns` / `_finalize_df(None)` honour v1→permissive,
  v2→strict. End-to-end `from_flow` input loads still force permissive mode in
  lynguine (`strict_columns=False`); tracked separately as
  `lynguine/backlog/bugs/2026-10-06_from-flow-hardcodes-strict-columns-false.md`
  and is **out of scope** for this CIP’s dialect detect / stamp / migrate work.

### 2026-10-06 compression

Distilled into formal docs (`compressed: true`):

- `docs/usage/config_dialect.rst` — user guide (versions, mapping, CLI, `strict_columns`)
- `docs/modules/config.rst` — dialect automodule + link
- `docs/index.rst` — toctree entry
- `README.md` — check / migrate / version summary

## References

- `referia/config/interface.py` — current silent conversion
- `referia/check.py` / `referia/cli.py` — YAML lint only today
- `cip/cip000A.md` — Excel→YAML *data* files (different layer)
- `lynguine/access/paths.py` — path confinement that still blocks REF layout
- REF 2021 working configs: `~/Documents/ref/{impact,output,environment}/**/_referia.yml`
