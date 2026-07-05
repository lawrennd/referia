---
author: "Neil D. Lawrence"
created: "2026-07-05"
id: "000A"
last_updated: "2026-07-05"
status: "Implemented"
compressed: false
related_requirements: []
related_cips: []
tags:
- cip
- data-format
- yaml
- excel
- migration
title: "Migration from Excel to YAML for referia data files"
---

# CIP-000A: Migration from Excel to YAML for referia data files

## Status

- [ ] Proposed - Initial idea documented
- [ ] Accepted - Approved, ready to start work
- [ ] In Progress - Actively being implemented
- [x] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected
- [ ] Deferred

## Summary

Replace Excel (`.xlsx`) files used as input/output data stores in referia review
workflows with YAML (`.yml`) files. A pilot conversion was completed for the
`theses/examined` workflow, converting `candidates.xlsx` and `pdfpages.xlsx`.

## Motivation

Excel files are opaque binaries: they cannot be diffed, meaningfully tracked in
version control, or inspected without specialist tools. YAML is human-readable,
diffable, and already natively supported by lynguine as both input and output
format. Switching the data layer to YAML would make review data easier to
inspect, audit, and back up — particularly valuable for thesis examination
records that have long-term archival significance.

## Detailed Description

### What lynguine supports

`lynguine.access.io` already implements `read_yaml` / `write_yaml` alongside
`read_excel` / `write_excel`. The `read_data` / `write_data` dispatch functions
handle both. Switching format is therefore a configuration-only change in the
`_referia.yml` files: change `type: excel` → `type: yaml`, rename the file, and
drop Excel-specific keys (`sheet`, `header`).

### Pilot scope (`theses/examined`)

Two Excel files were converted in the pilot:

| File | Role | Config files updated |
|---|---|---|
| `theses/examined/info/candidates.xlsx` | Input (student roster) | `pdfpages/_referia.yml`, `examined/_referia.yml` |
| `theses/examined/info/pdfpages.xlsx` | Output (page selections) | `pdfpages/_referia.yml` |

The `chapter_comments.xlsx`, `chapter_corrections.xlsx`, `introduction.xlsx`,
and related files were left as Excel for this pilot.

### Lessons learned from the pilot

1. **Serialisation of date columns**: pandas reads Excel date cells as
   `pd.Timestamp` objects. PyYAML serialises these with Python-specific tags
   (`!!python/object/apply:pandas._libs.tslibs.timestamps._unpickle_timestamp`)
   that `yaml.safe_load` cannot read. The fix is to call `.date().isoformat()`
   before writing. Dates become plain strings (`'2022-01-31'`), which is
   acceptable — lynguine currently stores dates as strings in YAML workflows
   (see `introduction.yml`).

2. **Float-valued integers**: Page numbers and checkbox flags stored in Excel
   come out as `float64` (e.g. `1.0`, `95.0`). Converting whole-number floats
   to `int` before YAML serialisation produces cleaner output (`1`, `95`) and
   avoids confusing downstream readers.

3. **Computed index fields**: `candidates.xlsx` has no `Name` column — it is
   computed by a `render_liquid` compute block in the `input:` section of
   `_referia.yml`. Removing `sheet` and `header` from the config and switching
   to `type: yaml` leaves the compute block intact, so `Name` continues to be
   derived at load time. No changes to the compute logic were needed.

4. **Shared input files**: `candidates.xlsx` is referenced by two configs
   (`pdfpages/_referia.yml` and `examined/_referia.yml`). Both must be updated
   together when the file is renamed. A search for `filename: candidates.xlsx`
   across `_referia.yml` files is the reliable way to find all consumers.

5. **`candidates.xlsx` has no `preferred` column**: The `row_args` mapping in
   the compute block references `preferredName: preferred`, but that column is
   absent from the Excel. The YAML conversion faithfully reproduces what is
   present; the missing field is handled gracefully by the Liquid template.

6. **Keep originals as backup**: The `.xlsx` files should be retained alongside
   the new `.yml` files until the YAML workflow is validated end-to-end in a
   live notebook session. The conversion script skips conversion if a `.yml`
   already exists, preventing accidental overwrite.

7. **Scope of migration**: Only the `theses/examined` workflow was converted in
   this pilot. Historical review archives (under `applications/`,
   `project-checking/`, `uk-ai/`) use Excel extensively but are mostly
   read-only completed reviews. Converting them yields little practical benefit
   and carries migration risk with no clear gain.

### The conversion script

`scripts/excel_to_yaml_pilot.py` (in the OneDrive referia folder) performs the
one-time conversion and can serve as a template for future migrations. Key
design choices:

- Uses the referia `.venv` Python environment (which has `pandas` and `openpyxl`)
- `remove_nan()` drops `NaN`/`None`/empty-string values — matching lynguine's
  `write_yaml` behaviour
- `coerce_value()` handles `pd.Timestamp` → ISO date string and `float` whole
  numbers → `int`
- `--dry-run` flag for safe inspection before writing

## Implementation Plan

1. **Pilot** (`theses/examined`): ✅ complete
   - Convert `candidates.xlsx` → `candidates.yml`
   - Convert `pdfpages.xlsx` → `pdfpages.yml`
   - Update `pdfpages/_referia.yml` (input + output)
   - Update `examined/_referia.yml` (input)

2. **Validation**: Open the assessment notebook in `pdfpages/` and verify that:
   - All 15 students load correctly
   - Saving a page-range entry writes to `pdfpages.yml`
   - The `examined/_referia.yml` allocation view still works

3. **Wider rollout** (future, if pilot validates):
   - Apply the same pattern to `theses/examined/introduction.xlsx`,
     `chapter_comments.xlsx`, `chapter_corrections.xlsx`
   - Consider `theses/drafts/` equivalents
   - Active `applications/` and `project-checking/` reviews

## Backward Compatibility

Existing `.xlsx` files are left in place. Switching back requires reverting
the two config edits (`type: yaml → excel`, filename change) — the original
Excel files are untouched. There is no data loss risk in the pilot.

## Testing Strategy

Manual validation in the Jupyter assessment notebook:

- Load the notebook in `theses/examined/pdfpages/`
- Confirm all candidates appear with correct names
- Edit one page-range entry and save; confirm `pdfpages.yml` is updated
- Load `theses/examined/` notebook and confirm allocation view still works

## Implementation Status

- [x] Inspect Excel file structure and lynguine YAML support
- [x] Write `scripts/excel_to_yaml_pilot.py` conversion script
- [x] Handle date serialisation (`pd.Timestamp` → ISO string)
- [x] Handle float-integer page numbers (`1.0` → `1`)
- [x] Convert `candidates.xlsx` → `candidates.yml`
- [x] Convert `pdfpages.xlsx` → `pdfpages.yml`
- [x] Update `theses/examined/pdfpages/_referia.yml`
- [x] Update `theses/examined/_referia.yml`
- [ ] Validate in live notebook session
- [ ] Archive or remove `.xlsx` files once validated

## References

- `lynguine.access.io.read_yaml` / `write_yaml` — existing YAML I/O support
- `theses/examined/info/introduction.yml` — prior example of YAML data in this workflow
- `scripts/yaml_output.py` — existing script for YAML output generation
