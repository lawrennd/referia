---
id: "2026-11-04_cip0024-declared-sidecar-loads"
title: "CIP-0024: load_declared_yaml_rows + migrate compute wrappers"
status: "In Progress"
priority: "High"
created: "2026-11-04"
last_updated: "2026-11-04"
category: "features"
related_cips: ["0024"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- features
- cip0024
- dataflow
---

# Task: Declared sidecar loads in referia compute

> Linked CIP: 0024.

## Description

Add `load_declared_yaml_rows` / path helpers and migrate
`_load_info_yaml_rows` callers to prefer product-named interface stores
(`grounds`, `phrases`, `turns`, `chunks`, …).

## Acceptance Criteria

- [ ] Helper resolves path from declared store spec on the interface
- [ ] Wrappers in the CIP-0024 inventory prefer declared roles
- [ ] Deprecation fallback logs when declaration missing
- [ ] Unit tests cover declared load + discovery edges

## Implementation Notes

Class B keys are not lynguine `valid_data_types`; Interface retains them;
`from_flow` does not join them.

## Related

- CIP: 0024

## Progress Updates

### 2026-11-04

Task created with CIP acceptance; implementation started.
