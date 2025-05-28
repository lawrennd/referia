---
id: "2025-05-28_index-missing-from-mapping"
title: "Index isn't picked up by the mapping code"
status: "Proposed"
priority: "High"
effort: "Medium"
type: "bug"
created: "2025-05-28"
last_updated: "2025-05-28"
owner: "lawrennd"
github_issue: null
dependencies: null
---

## Description

This assertion fails

```python
interface = rf.config.interface.Interface.from_yaml("""input:
  type: local
  index: BGN  # index column is BGN
  select: 2032A
  data:
    - BGN: 2032A
      Title: A Project title
  mapping:
    BGN: BGN # BGN is in mapping
    Title: project_title""")
data = rf.assess.data.CustomDataFrame.from_flow(interface)
assert("BGN" in data.mapping()) # This assertion fails
```

we find that `BGN` is not in the mapping. Switching index to Title confirms that Title goes missing from the mapping. Diagnosis is that the index column is not being picked up in the mapping generation. It should be.

## Acceptance Criteria

- [ ] Minimal example running without assertion error
- [ ] Test cases created to ensure that index error doesn't recurr.

## Implementation Notes

### Analysis (2025-05-28)

- The index column is set as the DataFrame index and then deleted from the columns after being set, so it is not present in the columns list used to generate the mapping.
- The mapping is generated from the DataFrame columns, so the index column is excluded by design.
- This is a common pandas pattern, but for this use case, the index column should be explicitly included in the mapping.

### Decision

- The correct pattern is to explicitly add the index column to the mapping after generating it from the columns.
- This will ensure that the mapping always includes the index, regardless of whether it is present as a DataFrame column.

[Technical notes about implementation approach]

## Related

- CIP: [CIP number if related]
- PRs: [Pull request numbers]
- Documentation: [Links to relevant documentation]

## Progress Updates

### 2025-05-28

Create stub and minimal example.

Reflecting this might be a bug in the underlying lynguine package.

### 2025-05-28

Reviewed the implementation. Decision: explicitly add the index column to the mapping after generating it from the columns. This will ensure the mapping is complete and meets user expectations.
