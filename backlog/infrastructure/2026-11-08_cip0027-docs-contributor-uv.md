---
id: "2026-11-08_cip0027-docs-contributor-uv"
title: "Update Sphinx conf, contributor docs, examples, and Cursor poetry rule for uv"
status: "Completed"
priority: "Medium"
created: "2026-11-08"
last_updated: "2026-11-08"
category: "infrastructure"
related_cips: ["0027"]
owner: "Neil D. Lawrence"
dependencies: ["2026-11-08_cip0027-pep621-uv-lock"]
tags:
- backlog
- packaging
- uv
- documentation
---

# Task: Update Sphinx conf, contributor docs, examples, and Cursor poetry rule for uv

> Implements CIP-0027.

## Description

- Point `docs/conf.py` at PEP 621 `[project]` (prefer `tomllib`)
- Replace contributor-facing `poetry install` / `poetry run` with `uv sync` / `uv run` in README, installation/contributing docs, LLM docs, and `examples/**`
- Change CIP-0026-era `poetry run referia serve` strings to `uv run referia serve`
- Update `.cursor/rules/general.mdc` away from “Always use poetry for builds”

## Acceptance Criteria

- [x] Sphinx conf reads `[project]` successfully
- [x] README / installation / contributing / LLM docs use uv (or plain pip) wording
- [x] Package examples advertise `uv run referia serve`
- [x] Cursor general rule prefers uv for builds
- [x] Local `uv build` smoke succeeds

## Related

- CIP: 0027
- Documentation: `docs/conf.py`, `README.md`, `examples/`

## Progress Updates

### 2026-11-08

Task created (Ready) after CIP-0027 acceptance.

### 2026-11-08

Completed: implemented on `cip0027-poetry-to-uv` (PEP 621 + uv workflows + docs).
