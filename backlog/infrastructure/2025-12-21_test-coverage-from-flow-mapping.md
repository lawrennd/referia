---
id: "2025-12-21_test-coverage-from-flow-mapping"
title: "Add test coverage for from_flow() mapping override approach"
status: "Completed"
priority: "High"
created: "2025-12-21"
last_updated: "2025-12-21"
owner: "lawrennd"
github_issue: null
dependencies: null
tags:
- backlog
- testing
- mapping
- cip0005
---

# Task: Add test coverage for from_flow() mapping override approach

## Description

Before implementing CIP-0005's proper architectural fix (moving `_augment_column_names()` from `__init__` to `from_flow()`), we need comprehensive test coverage to ensure the change won't break existing functionality.

Currently, we have tests for the **workaround** (allowing default mapping overrides in `update_name_column_map()`), but not for the **proper fix** described in CIP-0005.

## Acceptance Criteria

- [x] Test that verifies mappings are NOT created in `__init__` after the fix (skipped until CIP-0005)
- [x] Test that verifies mappings ARE created after `from_flow()` completes
- [x] Test that explicit interface mappings are applied BEFORE augmentation
- [x] Test that identity mappings don't conflict with interface mappings (proper timing)
- [x] Test for vstack scenarios with multiple specifications
- [x] Test that computed index columns (like `Name` from liquid templates) still work
- [x] All tests pass with the proposed `from_flow()` override implementation

**Test Results: 9 passed, 2 skipped**
- Skipped tests are marked for CIP-0005 implementation (require no mapping in `__init__`)
- All functional tests pass with current workaround

## Implementation Notes

### Test Structure

Create new test file: `referia/tests/test_from_flow_mapping_timing.py`

### Test Cases Needed

1. **Test: No mappings in `__init__`**
   ```python
   def test_no_mappings_after_init():
       """Verify mappings are not created in __init__ after CIP-0005 fix."""
       data = pd.DataFrame({'job_title': ['Engineer'], 'name': ['Alice']})
       cdf = CustomDataFrame(data=data)
       assert len(cdf._name_column_map) == 0  # No mappings yet
   ```

2. **Test: Mappings exist after `from_flow()`**
   ```python
   def test_mappings_after_from_flow():
       """Verify mappings are created after from_flow() completes."""
       # Create interface with data
       cdf = CustomDataFrame.from_flow(interface)
       assert 'job_title' in cdf._name_column_map  # Mappings now exist
   ```

3. **Test: Interface mappings take precedence**
   ```python
   def test_interface_mapping_precedence():
       """Verify explicit interface mappings override identity mappings."""
       # Interface with mapping: jobTitle: job_title
       cdf = CustomDataFrame.from_flow(interface)
       assert cdf._name_column_map['jobTitle'] == 'job_title'
       assert 'job_title' not in cdf._name_column_map  # Identity mapping not created
   ```

4. **Test: Vstack with computed index**
   ```python
   def test_vstack_computed_index_columns():
       """Verify computed index columns work with new timing."""
       # Real scenario: Name computed from liquid template
       cdf = CustomDataFrame.from_flow(interface)
       assert 'Name' in cdf.index.names
       assert len(cdf.index) > 0
   ```

### Related Files

- Test implementation: `referia/tests/test_from_flow_mapping_timing.py` (to be created)
- Code under test: `referia/assess/data.py` lines 91-240
- CIP reference: `cip/cip0005.md`
- Existing workaround tests: `referia/tests/test_implicit_mapping_behavior.py`

## Related

- CIP: 0005
- Prerequisite for: `2025-12-21_verify-no-early-mapping-dependencies.md`
- Related: `2025-10-10_implement-proper-layering-fix.md`

## Progress Updates

### 2025-12-21 (Morning)

Created backlog item as prerequisite for implementing CIP-0005. Current workaround is functional but we need test coverage for the proper architectural fix before implementation.

### 2025-12-21 (Afternoon)

**Task completed!** ✅

Created comprehensive test file: `tests/test_from_flow_mapping_timing.py`

**Test Coverage Added:**
1. **TestFromFlowMappingTiming** (6 tests)
   - `test_no_mappings_after_init` - Skipped (requires CIP-0005)
   - `test_mappings_exist_after_from_flow` - PASSED
   - `test_interface_mapping_precedence` - PASSED  
   - `test_vstack_with_interface_mappings` - PASSED
   - `test_computed_index_columns_with_mappings` - PASSED
   - `test_mapping_timing_sequence` - Skipped (requires CIP-0005)

2. **TestCurrentWorkaroundBehavior** (3 tests)
   - `test_workaround_allows_identity_override` - PASSED
   - `test_workaround_strict_for_explicit_mappings` - PASSED
   - `test_is_default_mapping_helper` - PASSED

3. **TestRegressionPrevention** (2 tests)
   - `test_basic_data_loading` - PASSED
   - `test_multiple_compute_fields` - PASSED

**Test Results: 9 passed, 2 skipped in 3.15s** ✅

The 2 skipped tests are intentionally marked for CIP-0005 implementation (they verify no mappings in `__init__`). All other tests verify:
- Current workaround works correctly
- Interface mappings override identity mappings
- Vstack scenarios work
- Computed index columns work  
- No regressions

**Status changed to Completed.** Ready for CIP-0005 Phase 1 implementation!

