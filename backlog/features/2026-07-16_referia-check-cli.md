---
id: "2026-07-16_referia-check-cli"
title: "Add `referia check` CLI subcommand for LLM-ready config linting"
status: "Proposed"
priority: "Medium"
created: "2026-07-16"
last_updated: "2026-07-16"
related_cips: []
tags: ["cli", "yaml", "linting", "developer-experience"]
---

# Task: Add `referia check` CLI subcommand

## Description

A `referia check [--root PATH]` command that scans all `_referia.yml`
files under a root directory and emits a structured, LLM-readable report of
problems — file path, error line, surrounding context, error category, and
suggested fix — so that a coding agent can fix every issue in a single pass
without manual file inspection.

The immediate motivation is the 9 broken configs discovered when building the
root-server directory listing (see the `/errors` endpoint added in
`fd3e802`).  All 9 fall into a small number of recurring fix templates:

| Category | Example | Fix |
|---|---|---|
| `*` bare value (alias confusion) | `glob: *` | `glob: "*"` |
| Unquoted `:` in title | `title: Foo: Bar` | `title: "Foo: Bar"` |
| Invalid escape in double-quoted string | `regexp: "\("` | switch to single quotes |
| Inline value + sub-mapping conflict | `index: Name\n  key: ...` | remove inline scalar |
| Bad indentation in block mapping | 7 spaces vs 8 | fix to consistent indent |
| Stray `"` in block scalar | lone `"` on its own line | remove the line |
| `*` at start of line inside criterion block | `* Is it credible...` | use `criterion: \|` literal block |

## Acceptance Criteria

- [ ] `referia check` (or `referia check --root PATH`) scans all
  `_referia.yml` under the target directory
- [ ] Exit code 0 if no errors, non-zero if any errors found
- [ ] Output includes for each broken file:
  - Absolute path to the `_referia.yml`
  - Error category (one of the fix templates above, or "unknown")
  - Error message from the YAML parser
  - Lines N-3 to N+3 of context around the error line (N = error line number)
- [ ] A `--format json` option emits machine-readable JSON for LLM consumption
- [ ] A `--format text` option (default) emits human-readable output
- [ ] `referia check --root ~/OneDrive/referia` cleanly reports the 9 known
  broken files and 0 errors for the remaining 268 files

## Implementation Notes

- Add `check` subcommand to `referia/cli.py` (alongside `serve`)
- Core scanning logic can reuse `_read_config_meta()` from `referia/web/routes.py`
  (already catches and returns YAML errors) — or factor out a shared
  `scan_configs(root) -> list[dict]` helper
- Error categorisation: pattern-match the YAML error message and the
  offending line against the known fix templates above
- Context extraction: open the file and slice lines `[error_line-4 : error_line+3]`
- JSON output schema:
  ```json
  {
    "root": "/path/to/root",
    "total_scanned": 277,
    "errors": [
      {
        "path": "/path/to/_referia.yml",
        "line": 14,
        "column": 9,
        "category": "unquoted_glob_star",
        "message": "while scanning an alias ...",
        "context": ["  type: directory", "  glob: *_foo.pdf", "  index:"],
        "suggested_fix": "Quote the value: glob: \"*_foo.pdf\""
      }
    ]
  }
  ```
- The JSON output is designed to be pasted directly into a new chat as
  context for an LLM agent to fix all files in one pass

## Related

- `/errors` endpoint: `fd3e802` — web-facing equivalent for root-server mode
- Known broken files (as of 2026-07-16, 9 of 277):
  - `applications/2022-09-27_cdei_pets-prize-challenge/whitepaper/_referia.yml`
  - `applications/2023-07-12_accelerate_smle-position/video/_referia.yml`
  - `applications/2024-06-28_accelerate_smle-position/video/_referia.yml`
  - `marking/2021-12-17-ads-final-assignment/_referia.yml`
  - `marking/2021-12-17-ads-final-assignment/files/_referia.yml`
  - `marking/2022-02-24-deepnn-assignment-1/_referia.yml`
  - `marking/2022-05-24-information-theory-supervision-1/_referia.yml`
  - `supervision/students/aims/_referia.yml`
  - `theses/examined/review/_referia.yml`

## Progress Updates

### 2026-07-16
Task created.  Root cause identified: all 9 errors are old-format YAML
issues (pre-dating stricter YAML parsing), not referia logic errors.
