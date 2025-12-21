---
id: "2025-12-21_verify-no-early-mapping-dependencies"
title: "Verify no code depends on mappings existing in __init__"
status: "Completed"
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

- [x] Survey all referia code for direct access to `_name_column_map` after construction
- [x] Survey all referia code for direct access to `_column_name_map` after construction
- [x] Identify any review workflow code that depends on early mapping availability
- [x] Document all found dependencies with file/line numbers
- [x] For each dependency, determine if it:
  - Uses `from_flow()` (safe - mappings will still exist)
  - Constructs directly then accesses mappings (unsafe - will break)
  - Can be refactored to work with delayed mapping creation
- [x] Create migration plan for any unsafe dependencies
- [x] Verify test suite doesn't depend on early mapping creation

**Result: ONE test needs trivial update, zero production dependencies.**

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

### 2025-12-21 (Morning)

Created backlog item as prerequisite for implementing CIP-0005. Need to survey codebase to understand risk of moving mapping creation from `__init__` to `from_flow()`.

### 2025-12-21 (Afternoon)

**Survey completed!** ✅

### Findings Summary

**Risk Level: LOW** - Only one test needs updating, no production code dependencies found.

### Detailed Findings

#### 1. Direct Mapping Access in Production Code: ✅ NONE FOUND

Searched for `_name_column_map` and `_column_name_map` in all referia production code:
- All accesses are internal to `CustomDataFrame` class itself
- Most accesses check `if cname not in self._column_name_map` before adding mappings
- These occur during flow processing, not after construction
- **No external code depends on mappings existing after construction**

#### 2. CustomDataFrame Construction Sites: ✅ ALL SAFE

Found 3 construction sites in production code:
1. `referia/assess/review.py:481` - Documentation example only
2. `referia/assess/data.py:152` - Documentation example only  
3. `referia/assess/compute.py:87` - Documentation example only

**All are documentation examples, not actual production code.**

#### 3. Review Workflow Dependencies: ✅ NONE FOUND

Searched review workflows (`review.py`, `review_new.py`):
- Review workflows use `_column_names_dict` (different from `_column_name_map`)
- No direct access to column mappings after construction
- All data access goes through `from_flow()` or explicit flow processing

#### 4. Test Dependencies: ⚠️ ONE TEST NEEDS UPDATE

**FOUND:** `referia/tests/test_assess_data.py:86-98` - `test_automapping_consistency()`

```python
def test_automapping_consistency():
    """Test that automapping produces consistent results with CustomDataFrame mapping."""
    columns = ['validColumn', 'invalid-column', 'class', '_']
    df = referia.assess.data.CustomDataFrame({col: [1] for col in columns})  # Line 89
    
    # Get mapping from CustomDataFrame
    df_mapping = df._name_column_map  # Line 95 - DEPENDS ON __init__ MAPPING
    
    # Compare mappings
    assert auto_mapping == df_mapping
```

**Impact:** This test will FAIL after CIP-0005 implementation because it expects mappings immediately after construction.

**Fix Required:** Update test to either:
- Option A: Call `_augment_column_names()` explicitly after construction
- Option B: Restructure test to use `from_flow()` instead of direct construction

#### 5. Other Test Files: ✅ ALL SAFE

- `tests/test_implicit_mapping_behavior.py` - Explicitly calls `_augment_column_names()` to simulate current behavior (aware of timing)
- `tests/test_from_flow_mapping_timing.py` - Our new tests, designed for CIP-0005

### Risk Assessment by Category

| Category | Risk Level | Count | Action Required |
|----------|------------|-------|-----------------|
| Production Code | ✅ **NONE** | 0 | No changes needed |
| Documentation Examples | ✅ **NONE** | 3 | No changes needed |
| Review Workflows | ✅ **NONE** | 0 | No changes needed |
| Test Suite | ⚠️ **LOW** | 1 | Update one test |

### Migration Plan

**Single Test Fix Required:**

`referia/tests/test_assess_data.py:test_automapping_consistency()` - Add explicit augmentation:

```python
def test_automapping_consistency():
    """Test that automapping produces consistent results with CustomDataFrame mapping."""
    columns = ['validColumn', 'invalid-column', 'class', '_']
    df = referia.assess.data.CustomDataFrame({col: [1] for col in columns})
    
    # After CIP-0005: Explicitly augment to populate mappings
    for typ in df._d:
        df._augment_column_names(df._d[typ])
    
    auto_mapping = referia.assess.data.automapping(columns)
    df_mapping = df._name_column_map
    assert auto_mapping == df_mapping
```

### Conclusion

**✅ CIP-0005 is SAFE to implement!**

- **Zero production dependencies** on early mapping creation
- **One trivial test update** required
- **No review workflow impact**
- **No breaking changes** for users (all use `from_flow()`)

**Recommendation:** Proceed with CIP-0005 Phase 1 implementation.

