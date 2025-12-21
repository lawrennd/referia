---
id: "2025-12-21_include-query-flag-llm-custom-query"
title: "Add include_query Flag to llm_custom_query Function"
status: "Proposed"
priority: "Medium"
created: "2025-12-21"
last_updated: "2025-12-21"
owner: ""
github_issue: ""
dependencies: ""
tags:
- backlog
- feature
- llm
- compute
---

# Task: Add include_query Flag to llm_custom_query Function

## Description

Modify the `llm_custom_query` function to optionally include the user's question before the LLM response. This enables better conversation tracking by showing both what was asked and what was answered, rather than just the answer.

Currently, when a user asks a custom question via the UI, only the LLM's response is returned. With `include_query: true`, the output would be formatted as:

```
**Question:** What are the main contributions?

**Response:** The chapter presents three main contributions...
```

This is particularly useful when combined with append mode (CIP-0007), allowing users to build up a complete Q&A history.

## Acceptance Criteria

- [ ] Add `include_query` parameter to `llm_custom_query` function signature (default: false)
- [ ] When `include_query: true`, read the query text from the field specified in `row_args.custom_prompt`
- [ ] Format output with question and response sections using markdown formatting
- [ ] When `include_query: false` or omitted, return only the response (backward compatible)
- [ ] Handle empty or missing query gracefully
- [ ] Add unit tests for both true and false cases
- [ ] Update function documentation

## Implementation Notes

### Function Signature
```python
def llm_custom_query(
    filename,
    custom_prompt,
    directory,
    model,
    temperature=0.7,
    max_chars=50000,
    include_query=False,  # New parameter
    **kwargs
):
    # ...
```

### Output Formatting
```python
if include_query and custom_prompt:
    output = f"**Question:** {custom_prompt}\n\n**Response:** {response}"
else:
    output = response
```

### Reading Query from Field
The query text is passed via `row_args.custom_prompt` which references a field name. The function needs to read the actual value from that field in the current row data.

### Edge Cases
- Empty query string
- Very long queries (consider truncation or wrapping)
- Queries containing special markdown characters
- Missing custom_prompt parameter

## Related

- CIP: 0007 (Append Mode for Compute Operations)
- Related to thesis review UI in `theses/examined/introduction/_referia.yml`
- Part of conversation history feature set

## Progress Updates

### 2025-12-21

Task created as part of CIP-0007 implementation planning.

