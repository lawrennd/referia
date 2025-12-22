---
id: "2025-12-22_document-mode-history-parameters"
title: "Document Mode and History Parameters for Compute Framework"
status: "Ready"
priority: "High"
created: "2025-12-22"
last_updated: "2025-12-22"
owner: ""
github_issue: ""
dependencies: ""
tags:
- backlog
- documentation
- compute
- llm
---

# Task: Document Mode and History Parameters for Compute Framework

## Description

The `mode` parameter (CIP-0007) and `include_history`/`history` parameters (CIP-0008) have been fully implemented and tested, but are not documented in user-facing documentation. Users cannot discover or effectively use these powerful features without proper documentation.

**What's Implemented:**
- `mode` parameter in lynguine compute system ("replace", "append", "prepend")
- `separator` parameter for controlling entry separators
- `include_history` parameter in `llm_custom_query` and `llm_pdf_review`
- `history` parameter for providing conversation context
- UI configurations already updated in thesis review templates
- Comprehensive test coverage (8/15 for modes, 11/11 for history)

**What's Missing:**
- Documentation in `lynguine/docs/compute_framework.md`
- Documentation in `referia/docs/llm_integration.md`
- Documentation in `referia/docs/llm_pdf_review.md`
- User guide for conversational workflows
- Examples showing append mode with LLM functions

## Acceptance Criteria

### Core Documentation Updates

- [ ] Update `lynguine/docs/compute_framework.md`:
  - [ ] Add `mode` parameter to "Key Fields" section
  - [ ] Add `separator` parameter to "Key Fields" section
  - [ ] Add new "Write Modes" section with examples
  - [ ] Document all three modes: replace, append, prepend
  - [ ] Show example of conversation accumulation

- [ ] Update `referia/docs/llm_integration.md`:
  - [ ] Document `include_history` parameter for all LLM functions
  - [ ] Document `history` parameter for all LLM functions
  - [ ] Add examples showing conversational workflows
  - [ ] Explain self-referential history pattern

- [ ] Update `referia/docs/llm_pdf_review.md`:
  - [ ] Document `include_history` and `history` parameters
  - [ ] Show example with conversation history
  - [ ] Explain how to build on previous reviews

### New Documentation

- [ ] Create `referia/docs/llm_conversations.md`:
  - [ ] Overview of conversational LLM interactions
  - [ ] Quick start example
  - [ ] How it works (step-by-step)
  - [ ] Use cases (thesis review, iterative analysis)
  - [ ] Configuration patterns
  - [ ] Best practices

### Configuration Templates and Examples

- [ ] Create `referia/docs/templates/` directory for reusable configuration blocks
- [ ] Create `referia/docs/templates/conversational_query_basic.yml`:
  - [ ] Complete pattern: Checkbox + Textarea (prompt) + PopulateButton + Textarea (response)
  - [ ] With `mode: "append"`, `separator`, `include_history`, `history` parameters
  - [ ] Inline comments explaining each component
  - [ ] Self-referential history pattern (field references itself)
  
- [ ] Create `referia/docs/templates/conversational_query_advanced.yml`:
  - [ ] Multi-source history composition using `view_args` with Liquid
  - [ ] Example: Combining summary + previous questions as context
  - [ ] Example: Cross-field history references
  - [ ] Token limit considerations and truncation patterns
  
- [ ] Create `referia/docs/templates/summary_with_history.yml`:
  - [ ] Pattern for summaries that use custom query conversation as context
  - [ ] Shows `include_history` checkbox for summaries
  - [ ] Demonstrates history parameter pointing to different field
  
- [ ] Document the thesis review reference implementation:
  - [ ] Add section in `llm_conversations.md` referencing `theses/examined/introduction/_referia.yml`
  - [ ] Extract and explain the repeating patterns (15 chapters using same structure)
  - [ ] Provide guidance on adapting the template for other document types
  - [ ] Link to full file as production reference

- [ ] Add "Configuration Cookbook" section to `llm_conversations.md`:
  - [ ] "Basic: Single field conversation history"
  - [ ] "Intermediate: Summary informs custom queries"
  - [ ] "Advanced: Multi-field history composition with Liquid templates"
  - [ ] Each with complete YAML block and explanation

### CIP Updates

- [ ] Update CIP-0007 status to "Implemented" (add documentation status)
- [ ] Update CIP-0008 status to "Implemented" (add documentation status)
- [ ] Add "Documentation Status" section to both CIPs
- [ ] Link CIPs to this documentation task

## Implementation Notes

### Location Map

**Files to Update:**

1. `/Users/neil/lawrennd/lynguine/docs/compute_framework.md`
   - Add after line 57 (in "Key Fields" section)
   - Add new section "Write Modes" after line 292 (after "Refresh Behavior")

2. `/Users/neil/lawrennd/referia/docs/llm_integration.md`
   - Update function documentation (lines 140-247)
   - Add new section "Conversational Interactions"

3. `/Users/neil/lawrennd/referia/docs/llm_pdf_review.md`
   - Update "Available Functions" section (lines 108-143)
   - Add conversation example

4. `/Users/neil/lawrennd/referia/docs/llm_conversations.md` (NEW FILE)
   - Create comprehensive conversational workflow guide

5. `/Users/neil/lawrennd/referia/cip/cip0007.md`
   - Update status field from "proposed" to "Implemented"
   - Add link to documentation task

6. `/Users/neil/lawrennd/referia/cip/cip0008.md`
   - Update status field from "Proposed" to "Implemented"
   - Add link to documentation task

### Content Outline for Write Modes Section

```markdown
## Write Modes

The compute framework supports three write modes that control how computation results are written to target fields:

### Mode Parameter

- **mode** (string): Write strategy
  - `"replace"` (default): Overwrite field with new content
  - `"append"`: Add new content after existing content
  - `"prepend"`: Add new content before existing content

- **separator** (string): Text inserted between entries (default: `"\n\n---\n\n"`)
  - Only used for append and prepend modes
  - Can be customized or set to empty string

### Example: Conversation History

```yaml
compute:
  - function: llm_custom_query
    field: conversation_history
    mode: "append"              # Accumulate responses
    separator: "\n\n---\n\n"    # Separate entries
    row_args:
      custom_prompt: user_question
    args:
      include_query: true       # Include question in output
```

### Behavior

**Replace Mode (default):**
- Always overwrites field value
- Existing content is lost
- Backward compatible (default behavior)

**Append Mode:**
- Reads current field value
- If non-empty, adds separator
- Appends new content after separator
- Perfect for building histories

**Prepend Mode:**
- Reads current field value
- Prepends new content
- If current value non-empty, adds separator after new content
- Useful for reverse-chronological ordering
```

### Content Outline for History Parameters

```markdown
## Conversational Context

LLM functions support including previous conversation history as context, enabling follow-up questions and iterative analysis.

### Parameters

- **include_history** (boolean): Enable conversation history (default: false)
- **history** (string): Previous conversation text to include as context

### Example: Self-Referential History

```yaml
- type: PopulateButton
  args:
    compute:
      field: ch1Response
      function: llm_custom_query
      mode: "append"                    # Accumulate conversation
      row_args:
        custom_prompt: ch1Prompt
        include_history: true           # Use previous Q&A as context
        history: ch1Response            # Self-referential
      args:
        include_query: true             # Format with question
```

### Example: Multi-Source History with Liquid Templates

```yaml
- type: PopulateButton
  args:
    compute:
      field: ch1Response
      function: llm_custom_query
      mode: "append"
      view_args:
        history:
          liquid: |
            ## Chapter Summary
            {{ ch1Summary }}
            
            ## Previous Questions
            {{ ch1Questions }}
            
            ## Custom Q&A History
            {{ ch1Response }}
      row_args:
        custom_prompt: ch1Prompt
        include_history: true
      args:
        include_query: true
```

### How It Works

1. **First Query**: LLM responds based on document + question
2. **Second Query**: LLM sees document + previous Q&A + new question
3. **Follow-up**: Can reference previous conversation naturally
4. **Multi-source**: Can combine multiple fields as context using Liquid

### Use Cases

- **Iterative Analysis**: Build understanding through multiple questions
- **Follow-up Questions**: Ask clarifying questions referencing previous answers
- **Comprehensive Reviews**: Accumulate multiple perspectives in one field
- **Cross-field Context**: Use summary and questions to inform custom queries
```

## Related

- **CIP-0007**: Append Mode for Compute Operations (needs status update to "Implemented")
- **CIP-0008**: Conversational Context for LLM Functions (needs status update to "Implemented")
- **Backlog Tasks**:
  - 2025-12-21_implement-mode-parameter-compute (Completed)
  - 2025-12-21_implement-history-parameter-llm-functions (Completed)
  - 2025-12-21_update-thesis-review-ui-append-mode (Completed)
- **Implementation Files**:
  - `lynguine/assess/compute.py` (mode implementation)
  - `referia/assess/compute.py` (llm function implementations)
  - `referia/tests/test_assess_compute_modes.py` (mode tests)
  - `referia/tests/test_assess_compute_llm_history.py` (history tests)
- **Reference Implementation**:
  - `referia/theses/examined/introduction/_referia.yml` (3120-line production config using all features)

## Progress Updates

### 2025-12-22

Task created based on documentation assessment. Both features (mode parameter and history parameters) are fully implemented and tested, but documentation is incomplete. This is blocking users from discovering and using these powerful features.

**Implementation Status**: ✅ Complete
- Mode parameter: 8/15 tests passing (core functionality validated)
- History parameters: 11/11 tests passing
- UI templates: Updated with append mode and history
- Reference implementation: 3120-line production config in thesis review template

**Documentation Status**: ❌ Incomplete
- Core compute framework docs: Missing mode/separator docs
- LLM integration docs: Missing history parameter docs
- User guides: No conversational workflow documentation
- **Configuration templates: Missing reusable YAML templates for common patterns**
- **Reference implementation: Not documented or linked**

**Gap Identified**: The `_referia.yml` thesis review configuration demonstrates:
- Full conversational query patterns (checkbox + prompt + button + response)
- Real-world integration of mode, separator, include_history, history parameters
- Liquid templates in view_args for dynamic filename generation
- Multi-field parameter extraction via row_args
- Repeating patterns across 15 chapters

These **configuration patterns need to be extracted, documented, and provided as copy-paste templates** for users.

**Priority**: High - Users cannot effectively use implemented features without documentation and templates.

