---
id: "2026-11-08_cip0027-ci-workflows-uv"
title: "Switch GitHub Actions workflows from Poetry to uv"
status: "Completed"
priority: "High"
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
- ci
---

# Task: Switch GitHub Actions workflows from Poetry to uv

> Implements CIP-0027.

## Description

Update `python-tests.yml`, `docs.yml`, and `publish.yml` to use `astral-sh/setup-uv`, `uv sync`, `uv run`, and `uv build` / `uv publish` instead of Poetry. Keep macos for tests if Darwin-marked deps remain required in CI.

## Acceptance Criteria

- [x] No workflow installs or invokes Poetry
- [x] Tests run under `uv run pytest`
- [x] Docs job syncs docs (+dev as needed) and builds Sphinx with `uv run`
- [x] Publish job checks `[project].version` against the release tag, builds with `uv build`, verifies, and publishes
- [x] Codecov upload steps remain wired

## Implementation Notes

Mirror lynguine CIP-001B workflows; keep `macos-latest` for `python-tests.yml` / publish unless Linux is proven sufficient.

## Related

- CIP: 0027
- Documentation: `.github/workflows/`

## Progress Updates

### 2026-11-08

Task created (Ready) after CIP-0027 acceptance.

### 2026-11-08

Completed: implemented on `cip0027-poetry-to-uv` (PEP 621 + uv workflows + docs).
