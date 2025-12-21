---
id: "2025-10-10_implement-proper-layering-fix"
title: "Implement proper layering fix for mapping initialization timing conflict"
status: "Proposed"
priority: "High"
created: "2025-10-10"
last_updated: "2025-10-10"
owner: "lawrennd"
github_issue: null
dependencies: null
tags:
- backlog
- infrastructure
- mapping
- layering
- cip0005
---

# Task: Implement proper layering fix for mapping initialization timing conflict

## Description

Implement the correct architectural solution for the mapping initialization timing conflict by properly separating concerns between lynguine (infrastructure) and referia (application) layers.

**Current Problem**: The fix was applied in lynguine (infrastructure) to accept referia's implicit behavior, which made the conflation worse. Both layers are now implicit.

**Correct Solution**: 
- **lynguine**: Stay strict and explicit (revert the fix)
- **referia**: Handle implicit behavior explicitly by overriding `update_name_column_map()`

## Motivation

### Design Philosophy Tension

- **lynguine (DOA Infrastructure)**: Should be explicit, machine-understandable, flow-based processing
- **referia (User-Oriented Application)**: Should provide implicit, human-friendly convenience

### Current State (Wrong)

1. **lynguine**: Now accepts implicit behavior (identity mapping override)
2. **referia**: Still has implicit behavior
3. **Result**: Both layers are now implicit, conflation is worse

### Desired State (Correct)

1. **lynguine**: Strict and explicit (no implicit overrides)
2. **referia**: Handles implicit behavior explicitly (override method)
3. **Result**: Clear separation of concerns, proper layering

## Implementation Plan

### Phase 1: Revert lynguine fix (Low risk)
- [x] Revert `lynguine/assess/data.py` line 3071 to strict behavior
- [x] Remove identity mapping override logic from lynguine
- [x] Ensure lynguine is strict for all mapping conflicts

### Phase 2: Implement referia override (Medium risk)
- [x] Override `update_name_column_map()` in `referia/assess/data.py`
- [x] Handle default mapping overrides (implicit behavior)
- [x] Reuse lynguine's strict logic for non-default cases
- [x] Add helper method `_is_default_mapping()`

### Phase 3: Testing (Medium risk)
- [x] Test lynguine: Strict behavior (no implicit overrides)
- [x] Test referia: Implicit behavior for default mappings, strict for others
- [x] Test integration: Both work together properly
- [x] Verify existing functionality still works

### Phase 4: Documentation (Low risk)
- [ ] Update CIP-0005 to reflect new approach
- [ ] Document the proper layering separation
- [ ] Explain when to use lynguine vs referia behavior

## Technical Details

### referia Implementation

```python
# In referia's CustomDataFrame
def _is_default_mapping(self, original_name, column):
    """Check if this is a default mapping that can be overridden."""
    from lynguine.util.misc import to_camel_case
    auto_generated_name = to_camel_case(column) # only do this if it's an invalid variable
    return original_name == auto_generated_name or original_name == column

def update_name_column_map(self, name, column):
    """
    Referia's user-friendly version that handles implicit behavior.
    Reuses lynguine's strict logic for non-default cases.
    """
    if column in self._column_name_map and self._column_name_map[column] != name:
        original_name = self._column_name_map[column]
        
        if self._is_default_mapping(original_name, column):
            # Handle default mapping override (implicit behavior)
            log.warning(f"Overwriting default mapping for column \"{column}\" from \"{original_name}\" to \"{name}\"")
            if original_name in self._name_column_map:
                del self._name_column_map[original_name]
        else:
            # For non-default mappings, use lynguine's strict logic
            return super().update_name_column_map(name, column)
    
    # If we get here, either no conflict or we handled the default case
    self._name_column_map[name] = column
    self._column_name_map[column] = name
```

## Acceptance Criteria

- [ ] lynguine is strict for all mapping conflicts
- [ ] referia handles default mapping overrides (implicit behavior)
- [ ] referia reuses lynguine's strict logic for non-default cases
- [ ] No code duplication between layers
- [ ] Clear separation of concerns
- [ ] All existing tests pass
- [ ] New tests verify proper layering

## Related

- **CIP**: 0005 (Fix Mapping Initialization Timing Conflict with lynguine)
- **Related lynguine CIP**: 0003 (Consistency in CustomDataFrame Initialization)
- **Related lynguine backlog**: 2025-10-10_implement-proper-layering-fix

## Progress Updates

### 2025-10-10
Task created with Proposed status. Identified the need for proper architectural layering fix.
