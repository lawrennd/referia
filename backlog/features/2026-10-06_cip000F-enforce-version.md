---
id: "2026-10-06_cip000F-enforce-version"
title: "CIP-000F: Warn then error on missing referia_config_version"
status: "Proposed"
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

- [ ] Warn phase: load still succeeds; warning names the file path
- [ ] `check` reports missing version as warning (then as error in error phase)
- [ ] Error phase: `Interface` raises a clear error for missing version
- [ ] Escape hatch for archaeology: `--allow-unversioned` / constructor flag
- [ ] Declared version greater than supported: refuse with clear message
- [ ] Tests cover warn and error modes

## Implementation Notes

Do not enable error phase until stamp corpus is done. Keep inference for
dialect when version is present but keys are old (stamped v1).

## Related

- CIP: 000F

## Progress Updates

### 2026-10-06

Task created on CIP-000F acceptance. Blocked on stamp pass.
