---
id: "2025-12-21_document-mode-include-query"
title: "Document Mode and include_query Features"
status: "Proposed"
priority: "Low"
created: "2025-12-21"
last_updated: "2025-12-21"
owner: ""
github_issue: ""
dependencies: "2025-12-21_implement-mode-parameter-compute, 2025-12-21_include-query-flag-llm-custom-query"
tags:
- backlog
- documentation
- compute
---

# Task: Document Mode and include_query Features

## Description

Create comprehensive documentation for the new `mode` parameter and `include_query` flag added to the compute system. This documentation should help users understand when and how to use these features effectively.

The documentation should cover:
- The three write modes (replace, append, prepend)
- When to use each mode
- How to configure the separator
- The include_query flag for llm_custom_query
- Examples of common use cases
- Best practices for conversation histories

## Acceptance Criteria

- [ ] Add section to compute system documentation explaining `mode` parameter
- [ ] Document all three modes with examples
- [ ] Document `separator` parameter and customization options
- [ ] Add section to LLM integration docs explaining `include_query` flag
- [ ] Provide complete configuration examples for thesis review use case
- [ ] Include troubleshooting section for common issues
- [ ] Add API reference documentation for affected functions
- [ ] Update any existing tutorials or guides that should mention these features
- [ ] Add examples to the documentation that users can copy/paste

## Implementation Notes

### Documentation Locations

1. **Compute System Documentation**
   - Location: `docs/compute.md` or similar
   - Add section: "Write Modes"
   - Add section: "Accumulating Results"

2. **LLM Integration Documentation**
   - Location: `docs/llm_integration.md` or similar
   - Add section: "Including Queries in Responses"
   - Update examples for custom queries

3. **Configuration Reference**
   - Update schema documentation
   - Add parameter descriptions for `mode` and `separator`

4. **User Guide / Tutorial**
   - Add walkthrough for building conversation histories
   - Show before/after examples

### Example Documentation Sections

#### Write Modes
```markdown
## Write Modes

The compute system supports three write modes that control how results are written to fields:

### Replace Mode (Default)
Replaces the existing field value with new content.
```yaml
compute:
  mode: "replace"  # or omit for default
```

### Append Mode
Appends new content to the end of existing content with a separator.
```yaml
compute:
  mode: "append"
  separator: "\n\n---\n\n"  # optional
```

### Prepend Mode
Adds new content to the beginning of existing content with a separator.
```yaml
compute:
  mode: "prepend"
  separator: "\n\n---\n\n"  # optional
```
```

#### Include Query Example
```markdown
## Including Questions with LLM Responses

When using `llm_custom_query`, you can include the original question with the response:

```yaml
compute:
  function: llm_custom_query
  include_query: true
```

This formats the output as:
```
**Question:** What are the main contributions?

**Response:** The main contributions are...
```
```

### Documentation Standards
- Use clear, concise language
- Provide runnable examples
- Include both YAML and Python examples where applicable
- Add visual separators or formatting to make examples stand out
- Include "See Also" sections linking related features

## Related

- CIP: 0007 (Append Mode for Compute Operations)
- Depends on: Task 2025-12-21_implement-mode-parameter-compute
- Depends on: Task 2025-12-21_include-query-flag-llm-custom-query
- Related: Sphinx documentation system (CIP-0003)

## Progress Updates

### 2025-12-21

Task created as part of CIP-0007 implementation planning. Documentation should be written after the features are implemented and tested.

