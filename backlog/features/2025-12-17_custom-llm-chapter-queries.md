---
id: "2025-12-17_custom-llm-chapter-queries"
title: "Custom LLM Query Interface for Chapters"
status: "Completed"
priority: "Medium"
created: "2025-12-17"
last_updated: "2025-12-17"
owner: "Neil Lawrence"
github_issue: ""
dependencies: "LLM dependencies (poetry install --with llm), existing pdf_extract_text function"
tags:
- backlog
- feature
- llm
- user-interface
- thesis-review
---

# Task: Custom LLM Query Interface for Chapters

## Description

Add an interactive feature that allows users to ask custom questions about thesis chapters using LLM capabilities. This extends the existing summary button functionality by allowing users to provide their own prompts instead of using pre-defined summary templates.

The feature consists of three components per chapter:
1. **Prompt textarea**: Where users enter their custom question/prompt
2. **Response textarea**: Where the LLM-generated answer is displayed
3. **Populate button**: Triggers the LLM query combining the user's prompt with the chapter content

This enables flexible, exploratory interaction with chapter content - users can ask specific questions like "What are the methodological contributions?", "What are the limitations discussed?", "How does this relate to prior work?", etc.

## Acceptance Criteria

- [x] New compute function `llm_custom_query` added to `_llm_functions_list()` in `referia/assess/compute.py`
- [x] Function extracts chapter text from PDF using existing `pdf_extract_text`
- [x] Function retrieves user's custom prompt from data via row_args
- [x] Function combines prompt + chapter text and sends to LLM
- [x] Function handles edge cases (empty prompt, PDF extraction errors, LLM API errors)
- [x] Returns user-friendly error messages when appropriate
- [x] Configuration example added to documentation (in docstring)
- [x] Comprehensive test suite (9 tests) covering all scenarios
- [x] Works with both OpenAI and Anthropic providers

## Implementation Notes

### Technical Approach

**New Compute Function: `llm_custom_query`**

Add to `referia/assess/compute.py` in the `_llm_functions_list()` method:

```python
def llm_custom_query(prompt_field: str, chapter_file: str, 
                     start_page: int, directory: str = "",
                     model: str = "gpt-4o-mini", 
                     max_chars: int = 50000,
                     temperature: float = 0.7,
                     system_prompt: str = None,
                     **kwargs) -> str:
    """
    Answer a custom user prompt about a chapter using LLM.
    
    Extracts text from a PDF chapter and combines it with a user-provided
    prompt to generate a custom LLM response. This enables flexible 
    exploration of chapter content with arbitrary questions.
    
    :param prompt_field: Field name containing the user's custom prompt
    :param chapter_file: PDF filename for the chapter
    :param start_page: Starting page of the chapter
    :param directory: Directory containing the PDF
    :param model: LLM model to use (default: gpt-4o-mini)
    :param max_chars: Maximum characters to extract from PDF
    :param temperature: LLM temperature (default: 0.7)
    :param system_prompt: Optional system prompt to guide LLM behavior
    :return: LLM response text or error message
    
    Example in _referia.yml:
        - type: Textarea
          field: chapter1CustomPrompt
          args:
            description: "Ask a question about Chapter 1"
        
        - type: Textarea
          field: chapter1CustomResponse
          args:
            description: "LLM Response"
        
        - type: PopulateButton
          args:
            target: chapter1CustomResponse
            compute:
              field: chapter1CustomResponse
              function: llm_custom_query
              row_args:
                prompt_field: chapter1CustomPrompt
                chapter_file: "{Name}_thesis_chapter1.pdf"
                start_page: Chapter1FP
              args:
                directory: $HOME/Documents/theses/examined/
                model: "gpt-4o-mini"
    """
    # 1. Get the user's custom prompt from the data
    custom_prompt = self.data.get(prompt_field, "")
    if not custom_prompt or not custom_prompt.strip():
        return "⚠️ Please enter a question in the prompt field above."
    
    # 2. Extract chapter text from PDF
    try:
        chapter_text = pdf_extract_text(
            filename=chapter_file,
            directory=directory,
            start_page=start_page,
            max_chars=max_chars
        )
        
        if not chapter_text or not chapter_text.strip():
            return f"⚠️ Could not extract text from {chapter_file}"
            
    except Exception as e:
        return f"❌ Error extracting PDF: {str(e)}"
    
    # 3. Combine prompt with chapter text
    full_prompt = f"{custom_prompt.strip()}\n\n---\nChapter text:\n{chapter_text}"
    
    # 4. Query LLM
    try:
        llm_config = getattr(self, 'interface', {}).get("llm", {}) if hasattr(self, 'interface') else {}
        manager = get_llm_manager(llm_config)
        
        response = manager.call(
            prompt=full_prompt,
            model=model,
            temperature=temperature,
            system_prompt=system_prompt or "You are a helpful assistant analyzing academic thesis chapters. Provide clear, structured answers to questions about the content.",
            **kwargs
        )
        
        return response
        
    except Exception as e:
        return f"❌ LLM Error: {str(e)}"
```

**Function Registration:**

Add to the return list in `_llm_functions_list()`:

```python
{
    "name": "llm_custom_query",
    "function": llm_custom_query,
    "args": ["prompt_field", "chapter_file", "start_page"],
    "kwargs": ["directory", "model", "max_chars", "temperature", "system_prompt"],
    "defaults": {"directory": "", "model": "gpt-4o-mini", "max_chars": 50000, 
                 "temperature": 0.7, "system_prompt": None},
    "docstr": "Answer a custom user prompt about a chapter using LLM.",
}
```

### Configuration Pattern in _referia.yml

For each chapter, add this three-part pattern:

```yaml
# === Chapter 1 Custom Query ===
- type: Markdown
  liquid: "### Ask a Question About This Chapter"
  
- type: Textarea
  field: chapter1CustomPrompt
  args:
    description: "Your question or prompt"
    placeholder: "e.g., What are the key methodological contributions?"
    layout:
      width: 800px
      rows: 3

- type: Textarea
  field: chapter1CustomResponse
  args:
    description: "LLM Response"
    layout:
      width: 800px
      rows: 10

- type: PopulateButton
  args:
    description: "Ask LLM"
    target: chapter1CustomResponse
    compute:
      field: chapter1CustomResponse
      function: llm_custom_query
      row_args:
        prompt_field: chapter1CustomPrompt
        chapter_file: "{Name}_thesis_chapter1.pdf"
        start_page: Chapter1FP
      args:
        directory: $HOME/Documents/theses/examined/
        model: "gpt-4o-mini"
        temperature: 0.7
```

### Edge Cases to Handle

1. **Empty prompt**: Return friendly message asking user to enter a question
2. **PDF extraction failure**: Catch exception and return error message
3. **LLM API errors**: Catch and return user-friendly error
4. **Missing field**: Handle case where prompt_field doesn't exist in data
5. **Context window overflow**: Truncate chapter text if needed (max_chars parameter)

### Files to Modify

- `referia/assess/compute.py` - Add new function to `_llm_functions_list()`
- `examples/thesis_llm_review_example.py` - Add example usage (optional)
- Documentation - Add to LLM features documentation

## Related

- CIP: (none yet - could create CIP-0006 if this becomes larger architectural change)
- PRs: (to be created)
- Documentation: `referia/assess/compute.py` docstrings, existing LLM documentation
- Related Functions: `llm_complete`, `llm_pdf_review`, `pdf_extract_text`

## Progress Updates

### 2025-12-17 - Initial Creation

Task created with Proposed status. Feature requested by user to enable flexible, custom LLM queries on thesis chapters, extending beyond pre-defined summary functionality.

### 2025-12-17 - Implementation Complete

**Status changed to Completed.**

Successfully implemented `llm_custom_query` function with:
- Full function implementation in `referia/assess/compute.py` (lines 838-948)
- Comprehensive test suite with 9 test cases in `referia/tests/test_llm_integration.py`
- All tests passing ✅
- Function properly registered in LLM functions list
- Complete docstring with YAML configuration examples

**Implementation details:**
- Function signature accepts `custom_prompt` (from row_args), `chapter_file`, optional page range
- Extracts PDF text using existing `pdf_extract_text` function
- Combines user prompt with chapter content and queries LLM
- Robust error handling for empty prompts, PDF errors, and LLM API failures
- User-friendly error messages with emoji indicators (⚠️, ❌)
- Default system prompt optimized for academic thesis analysis
- Support for custom system prompts and temperature settings

**Test coverage:**
1. Valid inputs with mocked LLM response ✅
2. Empty prompt handling ✅
3. Missing/None prompt handling ✅
4. PDF extraction failures ✅
5. Empty PDF text ✅
6. LLM API errors ✅
7. Custom system prompts ✅
8. Page range support ✅
9. Function registry verification ✅

**Commits:**
- `4b48274`: Add backlog task for custom LLM chapter query feature
- `ccb9415`: Implement llm_custom_query function with comprehensive tests
