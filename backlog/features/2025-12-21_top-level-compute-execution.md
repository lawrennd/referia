---
id: "2025-12-21_top-level-compute-execution"
title: "Implement automatic execution for top-level compute operations"
status: "Proposed"
priority: "Medium"
created: "2025-12-21"
last_updated: "2025-12-21"
owner: "lawrennd"
github_issue: null
dependencies:
- "2025-12-21_fix-global-consts-scalar-loading"
tags:
- feature
- compute
- architecture
---

# Feature: Implement automatic execution for top-level compute operations

## Description

Currently, compute operations can be defined in two locations:

1. **Inside `input` specification**: Executes automatically during input loading
2. **At top-level in interface**: Does NOT execute automatically

This creates a problem when compute operations need to access `global_consts` or other parameters, because parameters load AFTER input (order 1 vs 0).

**Current Behavior**:
```yaml
input:
  type: yaml
  filename: data.yml
  compute:
    - field: result
      function: process
      row_args:
        data: value  # ✅ Works (auto-executes)
```

**Desired Behavior**:
```yaml
global_consts:
  type: local
  data:
    model: gpt-4o-mini
    
input:
  type: yaml
  filename: data.yml

compute:
  - field: result
    function: llm_summarize
    row_args:
      text: value
      model: model  # ❌ Doesn't work - needs global_consts loaded first
                     # ⏭️ Also doesn't auto-execute
```

## Motivation

### Use Case: Access Parameters in Compute

Users want to define reusable constants (model names, API keys, etc.) in `global_consts` and reference them in compute operations. This requires:

1. ✅ Parameters load before compute runs (achieved via top-level compute)
2. ❌ Top-level compute auto-executes (MISSING - this feature)

### Current Workaround

None. Users must either:
- Put compute inside `input` (can't access parameters loaded after)
- Manually call compute somehow (method doesn't exist)

## Proposed Solution

### Option 1: Auto-execute in `from_flow()`

Execute top-level compute automatically after all data is loaded:

```python
# In CustomDataFrame.from_flow(), after all data loaded:
if "compute" in interface and not found_in_input:
    cdf._execute_compute(interface["compute"])
```

**Pros**:
- Simple
- Consistent with input-level compute behavior
- No API changes

**Cons**:
- Always executes (can't defer)
- May conflict with existing expectations

### Option 2: Explicit `run_compute()` method

Add a method to trigger compute execution:

```python
cdf = CustomDataFrame.from_flow(interface)
cdf.run_compute()  # Explicit execution
```

**Pros**:
- Explicit control
- Can defer until needed
- Clear API

**Cons**:
- Extra step for users
- Inconsistent with input-level compute (auto-executes)

### Option 3: Load-time flag

Add flag to control execution:

```yaml
compute:
  auto_execute: true  # or false
  operations:
    - field: result
      ...
```

**Pros**:
- Maximum flexibility
- Backward compatible

**Cons**:
- More complex configuration
- More configuration options to document

## Recommendation

**Implement Option 1** (auto-execute) with escape hatch:

```python
# Auto-execute by default
if "compute" in interface:
    if interface.get("compute_auto_execute", True):  # Default True
        cdf._execute_compute(interface["compute"])
```

This provides:
- ✅ Sensible default (auto-execute like input-level compute)
- ✅ Escape hatch (`compute_auto_execute: false`)
- ✅ Minimal API changes

## Acceptance Criteria

- [ ] Top-level compute auto-executes after all data loaded
- [ ] Compute operations can access `global_consts` and other parameters
- [ ] Test from `test_global_consts.py` passes (currently skipped)
- [ ] Backward compatibility maintained (input-level compute still works)
- [ ] Optional flag to disable auto-execution
- [ ] Clear error messages if compute fails
- [ ] Documentation updated with examples

## Implementation Notes

### Execution Point

In `from_flow()` after the main loop:

```python
for key, item in sorted_items:
    # ... load all data ...

# After loop completes:
if "compute" in interface:
    log.debug("Executing top-level compute operations.")
    cdf._execute_compute(interface["compute"])
    
return cdf
```

### Testing Strategy

1. **Basic execution**: Top-level compute runs automatically
2. **Parameter access**: Compute can access global_consts
3. **Order verification**: Parameters loaded before compute executes
4. **Error handling**: Clear errors if compute fails
5. **Backward compat**: Input-level compute unaffected

### Related Code

- `CustomDataFrame.from_flow()` - Add execution call
- `CustomDataFrame.compute` property - Already exists
- `Compute.from_flow()` - Already parses compute operations
- Need to add: `CustomDataFrame._execute_compute()` method

## Related

- **Bug Fix**: `bugs/2025-12-21_fix-global-consts-scalar-loading.md` (Prerequisite)
- **Test**: `test_global_consts.py::test_access_globals_in_compute_row_args` (Currently skipped)
- **Feature Request**: `features/2025-12-21_simplify-global-constants-configuration.md`

## Benefits

- ✅ Users can access parameters in compute operations
- ✅ Cleaner separation of data loading vs processing
- ✅ More intuitive configuration structure
- ✅ Consistent with existing compute-in-input behavior
- ✅ Enables complex workflows (load constants → process data)

## Progress Updates

### 2025-12-21

Feature identified during global_consts bug fix implementation.

**Context**:
- Fixed global_consts scalar loading bug
- Created comprehensive test suite
- One test skipped: accessing global_consts in compute
- Root cause: Top-level compute doesn't auto-execute

**Status**: Proposed
**Priority**: Medium (blocks some use cases but workarounds exist)
**Complexity**: Low (execution mechanism already exists for input-level compute)

