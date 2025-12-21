---
id: "2025-12-21_fix-failing-write-modes-tests"
title: "Fix 7 failing write modes tests"
status: "Proposed"
priority: "Medium"
created: "2025-12-21"
last_updated: "2025-12-21"
owner: "lawrennd"
github_issue: null
dependencies: null
tags:
- backlog
- bugs
- testing
- write-modes
---

# Bug: Fix 7 failing write modes tests

## Description

7 tests in `referia/tests/test_write_modes.py` are currently failing. These failures are **pre-existing** and not related to CIP-0005 implementation. They were discovered during Phase 2 regression testing.

The tests relate to file write operations with different modes (append, prepend) and separators.

## Failing Tests

All in `referia/tests/test_write_modes.py`:

1. `TestWriteModes::test_append_mode_with_existing_content`
   - Expected: Existing content followed by new content
   - Actual: Content appears truncated or formatted incorrectly

2. `TestWriteModes::test_append_mode_with_empty_field`
   - Expected: New content only
   - Actual: Extra DataFrame formatting appears

3. `TestWriteModes::test_prepend_mode_with_existing_content`
   - Expected: New content followed by existing content
   - Actual: Content order or formatting incorrect

4. `TestWriteModes::test_prepend_mode_with_empty_field`
   - Expected: New content only
   - Actual: Extra DataFrame formatting appears

5. `TestWriteModes::test_custom_separator`
   - Expected: Content separated by custom separator
   - Actual: Separator not applied correctly

6. `TestWriteModes::test_empty_string_separator`
   - Expected: Content concatenated without separator
   - Actual: Formatting incorrect

7. `TestWriteModes::test_unicode_separator`
   - Expected: Content separated by unicode separator
   - Actual: Assertion fails

## Error Pattern

Common issue appears to be DataFrame formatting appearing in output when it shouldn't:
```
Expected: 'new content'
Actual: '  field2\n0 ...\nnew content'
```

This suggests the write operation might be including DataFrame representation instead of just the field value.

## Impact

- **Test Suite**: 7/225 tests failing (3.1% failure rate)
- **Functionality**: Write modes feature may not work as expected
- **User Impact**: Users using append/prepend modes may see unexpected output
- **Severity**: Medium - feature exists but may not work correctly

## Discovery Context

Found during CIP-0005 Phase 2 regression testing on 2025-12-21. These are **not caused by CIP-0005** - they are pre-existing failures. CIP-0005 related tests all pass (82/82 core tests, 11/11 CIP-0005 tests).

## Acceptance Criteria

- [ ] All 7 write modes tests pass
- [ ] Append mode correctly appends content without DataFrame formatting
- [ ] Prepend mode correctly prepends content without DataFrame formatting
- [ ] Custom separators work correctly
- [ ] Empty separators work correctly (no separator between content)
- [ ] Unicode separators work correctly
- [ ] No regressions in other write functionality

## Investigation Notes

### Hypothesis 1: DataFrame serialization issue
The tests expect raw field values but are getting DataFrame string representations. This suggests the write operation might be serializing the DataFrame instead of extracting field values.

### Hypothesis 2: Mode implementation incomplete
The append/prepend modes might not be fully implemented or might have bitrot since they were added.

### Files to Examine

- `referia/tests/test_write_modes.py` - Test file (check what behavior is expected)
- Source files handling write operations (need to identify)
- Look for `mode` parameter handling in write operations

## Related

- Discovered during: CIP-0005 Phase 2 regression testing
- Not related to: CIP-0005 mapping timing implementation
- May be related to: Recent changes to write functionality

## Progress Updates

### 2025-12-21

Bug identified during CIP-0005 Phase 2 regression testing. Confirmed as pre-existing (not caused by CIP-0005). Created backlog item to track the issue for future resolution.

