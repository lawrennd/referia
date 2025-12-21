---
id: "2025-12-21_implement-history-parameter-llm-functions"
title: "Implement History Parameter in LLM Functions"
status: "Proposed"
priority: "High"
created: "2025-12-21"
last_updated: "2025-12-21"
owner: ""
github_issue: ""
dependencies: "2025-12-21_implement-mode-parameter-compute"
tags:
- backlog
- feature
- llm
- conversation
---

# Task: Implement History Parameter in LLM Functions

## Description

Add `include_history` and `history` parameters to referia's LLM functions (`llm_custom_query`, `llm_pdf_review`) to enable conversational context. This allows LLM functions to include previous conversation history when generating responses, enabling follow-up questions and iterative analysis.

This is the core implementation task for CIP-0008 (Conversational Context for LLM Functions).

## Acceptance Criteria

- [ ] Add `include_history` parameter (boolean) to `llm_custom_query`
- [ ] Add `history` parameter (text) to `llm_custom_query`
- [ ] Format history with clear header: "## Previous Conversation"
- [ ] Add separator between history and current context
- [ ] Only include history if `include_history=True` AND `history` is non-empty
- [ ] Add `include_history` and `history` parameters to `llm_pdf_review`
- [ ] Test with self-referential history (field includes own previous content)
- [ ] Test with cross-field history (use summary as context for questions)
- [ ] Verify history doesn't break existing functionality (backward compatible)
- [ ] Handle empty/None history gracefully

## Implementation Notes

### Modified Function Signature

```python
def llm_custom_query(
    data,
    custom_prompt,
    filename,
    start_page=None,
    directory=None,
    model="gpt-4o-mini",
    temperature=0.7,
    max_chars=50000,
    include_query=False,
    include_history=False,  # NEW: Enable/disable history
    history=None            # NEW: History text to include
):
    """
    Execute custom LLM query with optional conversation history.
    
    :param include_history: If True, include conversation history as context
    :param history: Previous conversation text to prepend to prompt
    """
```

### Implementation Logic

```python
def llm_custom_query(..., include_history=False, history=None):
    # Build prompt with optional history
    prompt_parts = []
    
    # Add conversation history if enabled and available
    if include_history and history and str(history).strip():
        prompt_parts.append("## Previous Conversation\n\n")
        prompt_parts.append(str(history))
        prompt_parts.append("\n\n---\n\n")
    
    # Extract PDF text
    pdf_text = extract_pdf_text(filename, start_page, directory, max_chars)
    prompt_parts.append(f"## Document Section\n\n{pdf_text}\n\n")
    
    # Add current question
    prompt_parts.append(f"## Current Question\n\n{custom_prompt}\n\n")
    
    # Call LLM with full context
    full_prompt = "".join(prompt_parts)
    response = call_llm(full_prompt, model, temperature)
    
    # Format output
    if include_query:
        return f"**Question:** {custom_prompt}\n\n**Response:** {response}"
    return response
```

### Testing Strategy

```python
# Test 1: History disabled (default behavior)
result = llm_custom_query(data, "What are the contributions?", "file.pdf")
# Should work exactly as before, no history

# Test 2: History enabled but empty
result = llm_custom_query(
    data, "What are the contributions?", "file.pdf",
    include_history=True, history=""
)
# Should work normally, no history added

# Test 3: History enabled with content
result = llm_custom_query(
    data, "How does contribution 2 relate?", "file.pdf",
    include_history=True,
    history="Q: What are the contributions?\nA: 1) X, 2) Y, 3) Z"
)
# Should include history in prompt

# Test 4: Self-referential (common case)
# Configure with row_args: { history: forewordCustomResponse }
# where forewordCustomResponse is also the target field
```

### Files to Modify

1. `/Users/neil/lawrennd/referia/referia/util/llm.py` (or wherever `llm_custom_query` is defined)
   - Add new parameters
   - Implement history formatting and inclusion logic
   
2. Test file for LLM functions
   - Add test cases for history parameter
   - Test with various history content (empty, short, long)

## Related

- CIP: 0008 (Conversational Context for LLM Functions)
- Depends on: 2025-12-21_implement-mode-parameter-compute (need append mode to accumulate history)
- Related to: 2025-12-21_add-history-checkboxes-ui (UI integration)

## Progress Updates

### 2025-12-21

Task created as part of CIP-0008 implementation planning. This is the core functionality that enables conversational LLM interactions.

