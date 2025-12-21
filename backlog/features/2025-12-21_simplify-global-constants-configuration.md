---
id: 2025-12-21_simplify-global-constants-configuration
title: "Simplify Global Constants Configuration"
status: Proposed
priority: High
created: 2025-12-21
updated: 2025-12-21
owner: TBD
tags: [usability, configuration, global_consts]
---

## Description

The current `global_consts` mechanism in `_referia.yml` is non-intuitive and difficult to use for simple constant definitions. Users attempting to define reusable parameters (like LLM model names, temperatures, etc.) face significant complexity:

1. **No inline constant definition**: Users cannot define simple key-value constants directly in the YAML configuration
2. **Requires external files**: Even for simple constants, users must create separate YAML files
3. **Complex `hstack` configuration**: Combining multiple constant sources requires understanding `hstack` with proper `index` and `specifications` structure
4. **Constants don't appear as expected**: Despite correct configuration, constants from external files don't reliably appear as accessible columns
5. **No distinction between static values and row-varying data**: The system treats everything as dataframe columns, making it unclear how to define simple static parameters

### Current Workaround Attempts

Multiple approaches were attempted to define centralized LLM parameters:
- Using YAML anchors and references (doesn't work across `compute` boundaries)
- Creating `llm_params.yml` and trying to load via `global_consts` with `hstack`
- Using `type: series` with inline data (requires `specifications` field)
- Various `hstack` configurations with different `index` and `select` combinations

None reliably made the constants available as expected.

## Problem Statement

**As a user configuring a referia workflow**, I want to define reusable constant values (like model names, API settings, default parameters) **so that** I can:
- Centralize configuration in one place
- Avoid repetition across multiple compute operations
- Easily update values without hunting through the entire config
- Use simple, intuitive YAML syntax

**Currently**, this is unnecessarily difficult because:
- The `global_consts` mechanism assumes all data comes from external files
- The distinction between "constants" (static values) and "data" (row-varying values) is unclear
- The configuration syntax is complex and requires deep understanding of lynguine's data loading mechanisms

## Current Behavior

```yaml
# What users try (doesn't work):
global_consts:
  llm_model: gpt-4o-mini
  temperature: 0.3
  max_tokens: 2000

# What's required (complex and non-intuitive):
global_consts:
  index: index
  select: phd-theses
  type: hstack
  specifications:
    - type: yaml
      directory: $HOME/OneDrive/referia/theses/criteria/
      filename: theses.yml
      index: index
    - type: yaml
      directory: .
      filename: llm_params.yml
      index: index
```

And even the complex version doesn't reliably work.

## Desired Behavior

### Option 1: Inline Constants Section

```yaml
global_constants: (or whichever code is specifying, globals??)
  # Simple key-value pairs
  llm_model: gpt-4o-mini
  temperature: 0.3
  max_tokens: 2000
  api_endpoint: https://api.openai.com

# Reference in compute operations
compute:
  - field: summary
    function: llm_pdf_review
    args:
      model: $constants.llm_model
      temperature: $constants.temperature
      max_chars: $constants.max_tokens
```

Alternatively, one should be able to specify the file loading mechanism 

We need to investigate what's going on that this implementation isn't working.


## Acceptance Criteria

- [ ] Users can define simple constant key-value pairs directly in `_referia.yml`
- [ ] Constants are accessible in `compute` operations via `args` (not `row_args`)
- [ ] Constants can be defined inline or loaded from external files
- [ ] Multiple constant sources can be easily combined
- [ ] Clear documentation distinguishes between:
  - **Constants**: Static values that don't vary by row
  - **Global data**: Data that gets joined to every row (current `global_consts`)
- [ ] Backward compatibility maintained with existing `global_consts` configurations
- [ ] Clear error messages when constants are not found or misconfigured

## Implementation Notes

### Technical Considerations

1. **Storage**: Constants could be stored in `CustomDataFrame.constants` (separate from `_d` dataframes)
2. **Access**: Constants accessed differently from row data:
   - `row_args`: Expects column names (current behavior)
   - `args`: Could accept both literal values AND constant references (e.g., `$constants.model`)
3. **Loading**: Extend `Interface` to parse a new `constants` section
4. **Validation**: Validate constant references at configuration load time

### Related Code Areas

- `lynguine/lynguine/config/interface.py`: Parse new `constants` section
- `lynguine/lynguine/assess/data.py`: Store and access constants
- `lynguine/lynguine/assess/compute.py`: Resolve constant references in `args`
- `referia/referia/assess/data.py`: May need referia-specific extensions

### Testing Strategy

- Unit tests for constant definition and access
- Integration tests with compute operations using constants
- Tests for combining inline constants with file-based constants
- Tests for error handling (missing constants, circular references)

## Related

- Current conversation where this issue was identified
- User attempting to centralize LLM parameters across multiple compute operations
- Multiple failed attempts to use `global_consts` with `hstack`

## References

- `lynguine/lynguine/config/interface.py` - Interface parsing
- `lynguine/lynguine/access/io.py` - Data loading functions
- `lynguine/lynguine/assess/compute.py` - Compute function argument processing

## Progress Updates

### 2025-12-21
- Task created based on user experience attempting to centralize LLM configuration parameters
- Multiple configuration approaches attempted without success
- Issue stems from fundamental design where everything is treated as dataframe columns rather than distinguishing between static constants and row-varying data

