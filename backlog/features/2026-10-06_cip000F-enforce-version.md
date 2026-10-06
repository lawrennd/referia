---
id: "2026-10-06_cip000F-enforce-version"
title: "CIP-000F: Warn then error on missing referia_config_version"
status: "Completed"
priority: "Medium"
created: "2026-10-06"
last_updated: "2026-10-06"
category: "features"
related_cips: ["000F"]
owner: ""
dependencies:
- "2026-10-06_cip000F-stamp-machine-configs"
- "2026-10-06_cip000F-extract-normaliser"
tags:
- backlog
- cip000F
- versioning
- enforcement
---

# Task: Phased enforcement of config version field

## Description

After the machine-wide stamp pass, enforce `referia_config_version`:

1. **Warn** — `Interface` and `referia check` warn when version is absent
2. **Error** — on a subsequent package bump / cutover, missing version raises
   unless `--allow-unversioned` (CLI) or an explicit Interface flag is set

## Acceptance Criteria

- [x] Warn phase: load still succeeds; warning names the file path
- [x] `check` reports missing version as warning (then as error in error phase)
- [x] Error phase: `Interface` raises a clear error for missing version
- [x] Escape hatch for archaeology: `--allow-unversioned` / constructor flag
- [x] Declared version greater than supported: refuse with clear message
- [x] Tests cover warn and error modes

## Implementation Notes

Do not enable error phase until stamp corpus is done. Keep inference for
dialect when version is present but keys are old (stamped v1).

Default is **warn** (`DEFAULT_VERSION_ENFORCEMENT`). Override with
`REFERIA_CONFIG_VERSION_ENFORCEMENT=error|off|warn`, or per-call via
`Interface(..., version_enforcement=..., allow_unversioned=...)`.

Package cutover that changes the default to `error` is a later bump; the
error path is already implemented and tested.

## Related

- CIP: 000F

## Progress Updates

### 2026-10-06

Task created on CIP-000F acceptance. Blocked on stamp pass.

### 2026-10-06 (implementation)

Stamp corpus complete (314). Implemented `enforce_config_version` in
`referia/config/dialect.py`, wired into `Interface`, and extended
`referia check` warnings / strict error mode. Tests in
`referia/tests/test_config_dialect.py`.
