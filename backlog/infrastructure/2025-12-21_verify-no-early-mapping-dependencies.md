---
id: "2025-12-21_verify-no-early-mapping-dependencies"
title: "Verify no code depends on mappings existing in __init__"
status: "Proposed"
priority: "High"
created: "2025-12-21"
last_updated: "2025-12-21"
owner: "lawrennd"
github_issue: null
dependencies: null
tags:
- backlog
- investigation
- mapping
- cip0005
---

# Task: Verify no code depends on mappings existing in __init__

## Description

Before implementing CIP-0005's proper fix (moving `_augment_column_names()` from `__init__` to `from_flow()`), we must verify that no existing code depends on mappings being available immediately after `CustomDataFrame` construction.

This is a **breaking change risk assessment** task.

## Current Behavior (Lines 178-180 in referia/assess/data.py)

```python
# Ensure _name_column_map is populated by calling _augment_column_names on each data type
for typ in self._d:
    self._augment_column_names(self._d[typ])
```

Mappings are created in `__init__`, so any code that constructs a `CustomDataFrame` and immediately accesses `_name_column_map` will have data.

## Acceptance Criteria

- [ ] Survey all referia code for direct access to `_name_column_map` after construction
- [ ] Survey all referia code for direct access to `_column_name_map` after construction
- [ ] Identify any review workflow code that depends on early mapping availability
- [ ] Document all found dependencies with file/line numbers
- [ ] For each dependency, determine if it:
  - Uses `from_flow()` (safe - mappings will still exist)
  - Constructs directly then accesses mappings (unsafe - will break)
  - Can be refactored to work with delayed mapping creation
- [ ] Create migration plan for any unsafe dependencies
- [ ] Verify test suite doesn't depend on early mapping creation

## Implementation Notes

### Search Strategy

1. **Grep for mapping access patterns:**
   ```bash
   # Search for direct mapping access
   grep -rn "_name_column_map" referia/
   grep -rn "_column_name_map" referia/
   
   # Search for CustomDataFrame construction
   grep -rn "CustomDataFrame(" referia/
   
   # Search for review workflow code
   grep -rn "review" referia/
   ```

2. **Check test suite:**
   ```bash
   grep -rn "CustomDataFrame" referia/tests/
   ```

3. **Check for patterns like:**
   ```python
   cdf = CustomDataFrame(data=df)
   cdf._name_column_map[...]  # ⚠️ Potential issue
   ```

### Risk Categories

**Low Risk:**
- Code that uses `from_flow()` - mappings will exist
- Code that accesses mappings after explicit `_augment_column_names()` call
- Code in test fixtures that can be updated

**High Risk:**
- Review workflow code that constructs CDF then immediately uses mappings
- Public API methods that promise mapping availability
- Code that other projects depend on

### Files to Examine

Priority files to check:
- `referia/assess/data.py` - CustomDataFrame class itself
- `referia/access/*.py` - Review workflow code
- `referia/config/*.py` - Configuration processing
- `referia/tests/*.py` - Test suite
- Any code in `referia/` that imports CustomDataFrame

## Expected Findings

Based on CIP-0005, the original motivation for early mapping creation was:
> "referia's need for early mapping availability (for user-facing review workflows)"

So we expect to find:
1. Review workflow code that depends on mappings after construction
2. These likely need refactoring or a different solution

## Related

- CIP: 0005
- Depends on: `2025-12-21_test-coverage-from-flow-mapping.md` (parallel work)
- Blocks: Implementation of CIP-0005 proper fix
- Related: `2025-10-10_implement-proper-layering-fix.md`

## Progress Updates

### 2025-12-21

Created backlog item as prerequisite for implementing CIP-0005. Need to survey codebase to understand risk of moving mapping creation from `__init__` to `from_flow()`.

