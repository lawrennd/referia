---
id: "2025-12-23_template-expansion-column-generation"
title: "Fix Template Expansion Column Auto-Generation and Namespace Clash"
status: "Completed"
priority: "High"
created: "2025-12-23"
last_updated: "2025-12-23"
owner: "neil"
github_issue: ""
dependencies: ""
tags:
- backlog
- bug
- template-expansion
- cip-0006
---

# Task: Fix Template Expansion Column Auto-Generation and Namespace Clash

## Description

Fixed two critical bugs in the CIP-0006 template expansion system:

1. **Missing output columns from template-expanded fields**: When the `columns` list was removed from the `output` section to enable full auto-generation, the system failed to create the list, resulting in `ValueError` about columns not in specification.

2. **Namespace clash between template parameters and Liquid syntax**: The template system was using `{{param}}` for template parameters, which collided with Liquid's `{{field}}` syntax for data binding, causing incorrect rendering of Markdown headings and confusion with display variables `{Name}`.

## Acceptance Criteria

- [x] Output columns are auto-generated from template-expanded review fields
- [x] `_modified` and `_created` timestamp columns are added for all fields
- [x] Template parameter syntax clearly distinguished from Liquid and display syntax
- [x] Markdown section titles render correctly
- [x] Comprehensive tests prevent regression

## Implementation Notes

### Fix 1: Column Auto-Generation

Modified `referia/config/interface.py` to initialize `columns` list with review fields if it doesn't exist:

```python
for output_type in output_types:
    if output_type in data:
        if "columns" not in data[output_type]:
            data[output_type]["columns"] = []
            for col in review_columns:
                data[output_type]["columns"].append(col)
```

### Fix 2: Template Parameter Syntax

Changed template parameter syntax from `{{param}}` to `%param%` to provide clear separation:
- `%param%` - Template expansion parameters (processed during config load)
- `{{field}}` - Liquid data binding (processed during Markdown rendering)
- `{Name}` - Display variables (processed during UI display)

Updated `_substitute_parameters()` to use `%(\w+)%` regex and added support for `%%param%%` escape sequences.

## Related

- CIP: 0006 (Template Expansion System)
- Commits:
  - `bff3a33`: Fix template expansion: auto-generate output columns and change parameter syntax to %param%
  - `d3b9985`: Add comprehensive tests for template expansion (CIP-0006)
- Tests: `tests/test_template_expansion.py` (9 tests, all passing)

## Progress Updates

### 2025-12-23

- Diagnosed column auto-generation failure causing `ValueError` on `_modified` columns
- Identified namespace clash between `{{param}}` template syntax and Liquid `{{field}}` syntax
- Implemented fix in `referia/config/interface.py` to create columns list when missing
- Changed template parameter syntax from `{{param}}` to `%param%` throughout
- Created comprehensive test suite with 9 tests covering:
  - Template parameter substitution
  - Liquid syntax preservation
  - Display variable substitution
  - Column auto-generation
  - Timestamp column addition
  - Error handling
- All tests passing
- Committed fixes to referia repository
- Task completed

