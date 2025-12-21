---
id: "2025-12-21_implement-mode-parameter-compute"
title: "Implement Mode Parameter in Compute System"
status: "Proposed"
priority: "High"
created: "2025-12-21"
last_updated: "2025-12-21"
owner: ""
github_issue: ""
dependencies: ""
tags:
- backlog
- feature
- compute
- architecture
---

# Task: Implement Mode Parameter in Compute System

## Description

Add a `mode` parameter to the compute system that controls how results are written to target fields. This enables three write strategies:

1. **"replace"** (default): Replace existing field value (current behavior)
2. **"append"**: Append new content to end of existing value
3. **"prepend"**: Prepend new content to beginning of existing value

This is the core architectural change needed to support conversation histories and accumulating multiple analyses in a single field.

## Acceptance Criteria

- [ ] Add `mode` parameter to compute configuration schema
- [ ] Add `separator` parameter to compute configuration (default: `"\n\n---\n\n"`)
- [ ] Implement replace mode logic (existing behavior as default)
- [ ] Implement append mode logic (read → append separator → append content → write)
- [ ] Implement prepend mode logic (read → prepend content → prepend separator → write)
- [ ] Handle empty/null field values correctly for all modes
- [ ] Default to "replace" mode when parameter is omitted (backward compatibility)
- [ ] Work correctly with all data backends (Excel, YAML, etc.)
- [ ] Add unit tests for all three modes
- [ ] Add tests for separator customization (including empty string)
- [ ] Update compute system documentation

## Implementation Notes

### Configuration Schema
```yaml
compute:
  field: targetField
  function: some_function
  mode: "append"              # "replace" | "append" | "prepend"
  separator: "\n\n---\n\n"    # optional, default shown
  # ... other args
```

### Append Mode Logic
```python
def write_with_mode(field, new_content, mode="replace", separator="\n\n---\n\n"):
    if mode == "replace":
        return new_content
    
    current = read_field(field)
    
    if mode == "append":
        if current:
            return current + separator + new_content
        return new_content
    
    elif mode == "prepend":
        if current:
            return new_content + separator + current
        return new_content
    
    raise ValueError(f"Unknown mode: {mode}")
```

### Data Backend Compatibility

Ensure the following backends support read-modify-write:
- Excel backend (openpyxl)
- YAML backend
- Any other output backends

### Edge Cases

- Empty or null current field value
- Very long accumulated content (performance)
- Custom separator with special characters
- Mode parameter with invalid value (should error clearly)
- Separator parameter with None value (should use empty string)

### Performance Considerations

- For very long accumulated fields (10K+ characters), consider:
  - Limiting field size
  - Warning users about performance impact
  - Testing Excel rendering performance

## Related

- CIP: 0007 (Append Mode for Compute Operations)
- Depends on: None (core functionality)
- Required by: Task 2025-12-21_include-query-flag-llm-custom-query
- Required by: Task 2025-12-21_update-thesis-review-ui-append-mode

## Progress Updates

### 2025-12-21

Task created as part of CIP-0007 implementation planning. This is a high-priority task as other features depend on it.

