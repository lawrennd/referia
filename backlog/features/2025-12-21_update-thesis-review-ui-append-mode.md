---
id: "2025-12-21_update-thesis-review-ui-append-mode"
title: "Update Thesis Review UI to Use Append Mode"
status: "Completed"
priority: "Medium"
created: "2025-12-21"
last_updated: "2025-12-21"
owner: ""
github_issue: ""
dependencies: "2025-12-21_implement-mode-parameter-compute, 2025-12-21_include-query-flag-llm-custom-query"
tags:
- backlog
- feature
- ui
- thesis-review
---

# Task: Update Thesis Review UI to Use Append Mode

## Description

Update the thesis review `_referia.yml` configuration files to use the new append mode and include_query features. This enables examiners to build up conversation histories with the LLM by asking multiple questions about each chapter without losing previous Q&A pairs.

Currently, when an examiner asks multiple custom questions about a chapter, each new question overwrites the previous response. With this update, all questions and answers will accumulate in a structured history.

## Acceptance Criteria

- [x] Update all `llm_custom_query` calls in thesis review configs to use `include_query: true`
- [x] Set `mode: "append"` for all custom query response fields
- [x] Update placeholder text to indicate appending behavior (e.g., "Questions and responses will accumulate here...")
- [ ] Test the updated configuration with multiple queries (manual testing required)
- [ ] Verify accumulated content displays correctly in UI (manual testing required)
- [ ] Verify accumulated content exports correctly to Excel (manual testing required)
- [ ] Consider adding "Clear" button functionality for append-mode fields (optional, future work)
- [ ] Update any related documentation or user guides (future work)

## Implementation Notes

### Configuration Changes

**Before:**
```yaml
- type: Textarea
  field: ch1CustomResponse
  args: 
    description: "LLM Response"
    placeholder: "LLM response to your custom question will appear here..."
    rows: 10
- type: PopulateButton
  args:
    target: ch1CustomResponse
    compute:
      field: ch1CustomResponse
      function: llm_custom_query
      # No mode or include_query
```

**After:**
```yaml
- type: Textarea
  field: ch1CustomResponse
  args: 
    description: "LLM Response"
    placeholder: "Questions and responses will accumulate here. Each query is separated by ---"
    rows: 15  # Increased for accumulated content
- type: PopulateButton
  args:
    description: "Ask LLM"
    target: ch1CustomResponse
    compute:
      field: ch1CustomResponse
      function: llm_custom_query
      mode: "append"           # New
      include_query: true      # New
      separator: "\n\n---\n\n" # Optional, this is default
```

### Files to Update
- `/Users/neil/Library/CloudStorage/OneDrive-Personal/referia/theses/examined/introduction/_referia.yml`
- Any other thesis review configuration files

### UI Considerations
- Consider increasing `rows` parameter for response fields to accommodate longer accumulated content
- Consider adding clear/reset functionality for fields in append mode
- Ensure textarea scrolling works well with long content

### Testing Checklist
- [ ] Ask first question → verify formatted output with question and response
- [ ] Ask second question → verify both Q&A pairs appear separated by `---`
- [ ] Ask third question → verify all three Q&A pairs accumulate correctly
- [ ] Export to Excel → verify accumulated content appears correctly
- [ ] Test with empty initial field
- [ ] Test with very long questions and responses

## Related

- CIP: 0007 (Append Mode for Compute Operations)
- Depends on: Task 2025-12-21_implement-mode-parameter-compute
- Depends on: Task 2025-12-21_include-query-flag-llm-custom-query
- Configuration file: `theses/examined/introduction/_referia.yml`

## Progress Updates

### 2025-12-21

Task created as part of CIP-0007 implementation planning. This task should be completed after the core functionality is implemented and tested.

**COMPLETED**: Updated all thesis review UI configurations to use append mode and include_query:

Updated 8 llm_custom_query configurations in `/theses/examined/introduction/_referia.yml`:
- ✅ Foreword custom query
- ✅ Prologue custom query  
- ✅ Chapter 1-6 custom queries

Changes applied to each:
- Added `mode: "append"` to enable conversation history
- Added `separator: "\n\n---\n\n"` for clear Q&A separation
- Added `include_query: true` in args to show questions with responses
- Updated placeholder text: "Questions and responses will accumulate here. Each Q&A is separated by ---"
- Increased textarea rows from 10 to 15 to accommodate accumulated content

The thesis review UI is now ready for conversation-style interactions with accumulated Q&A history!

**Next steps** (manual testing):
- Test with actual thesis review workflows
- Verify UI rendering of accumulated content
- Test Excel export functionality

