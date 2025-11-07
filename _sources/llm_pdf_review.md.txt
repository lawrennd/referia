# LLM-Powered PDF Review for Thesis Assessment

## Overview

This feature combines PDF text extraction with LLM capabilities to automatically generate initial reviews and comments for thesis chapters or any PDF documents. It's particularly useful for:

- **Thesis examiners**: Auto-generate initial chapter comments
- **Document reviewers**: Quick summaries and assessments
- **Batch processing**: Process multiple chapters/documents efficiently

## Quick Start

### 1. Installation

```bash
# Install LLM dependencies
cd referia
poetry install --with llm
```

### 2. API Key Setup

Create a `.env` file in your project directory:

```bash
# For OpenAI
OPENAI_API_KEY=your-openai-key-here

# Or for Anthropic
ANTHROPIC_API_KEY=your-anthropic-key-here
```

### 3. Update Your Review Configuration

Modify your `_referia.yml` to add LLM-powered populate buttons:

```yaml
# Add LLM configuration
llm:
  default_provider: openai
  default_model: gpt-4o-mini  # Cost-effective
  cache_enabled: true
  budget_per_run: 2.00  # $2 per run

review:
  # Your existing review structure...
  
  - type: Markdown
    liquid: "### Chapter 1"
    args:
      layout:
        width: 800px
  
  - type: Textarea
    field: ch1GeneralComments
    args: 
      description: "General Comments"
      layout:
        width: 800px
  
  # NEW: LLM-powered populate button
  - type: PopulateButton
    args:
      target: ch1GeneralComments
      compute:
        field: ch1GeneralComments
        function: llm_pdf_review
        view_args:
          filename:
            display: "{Name}_thesis_ch1.pdf"
        args:
          directory: $HOME/Documents/theses/examined
          review_type: "general"
          model: gpt-4o-mini
```

## Available Functions

### 1. `pdf_extract_text`

Extracts plain text from PDF files.

**Parameters:**
- `filename` (str): PDF filename
- `directory` (str): Directory containing the PDF
- `start_page` (int, optional): Starting page (1-indexed)
- `end_page` (int, optional): Ending page (1-indexed)
- `max_chars` (int, optional): Maximum characters to extract

**Example:**

```yaml
compute:
  - function: pdf_extract_text
    field: chapter_text
    view_args:
      filename:
        display: "{Name}_thesis_ch1.pdf"
    args:
      directory: "$HOME/Documents/theses/examined"
      max_chars: 50000
```

### 2. `llm_pdf_review`

Extracts text from PDF and generates an LLM-based review.

**Parameters:**
- `filename` (str): PDF filename to review
- `directory` (str): Directory containing the PDF
- `review_type` (str): Type of review (see below)
- `max_chars` (int): Max characters to extract (default: 30000)
- `model` (str): LLM model to use (default: gpt-4o-mini)
- `temperature` (float): Sampling temperature (default: 0.3)
- `system_prompt` (str, optional): Custom system prompt

**Review Types:**

| Type | Purpose | Word Limit |
|------|---------|------------|
| `general` | Balanced, constructive general comments | ~200 words |
| `strengths` | Focus on positive aspects and contributions | ~200 words |
| `weaknesses` | Constructive areas for improvement | ~200 words |
| `technical` | Detailed technical/methodological assessment | ~250 words |
| `summary` | Concise summary of key points | ~150 words |
| `questions` | Viva-style questions for examining understanding | ~150 words |

**Example:**

```yaml
compute:
  - function: llm_pdf_review
    field: ch1GeneralComments
    view_args:
      filename:
        display: "{Name}_thesis_ch1.pdf"
    args:
      directory: "$HOME/Documents/theses/examined"
      review_type: "general"
      model: "gpt-4o-mini"
      max_chars: 30000
```

## Migrating Your Existing Configuration

### Before (Manual Comments Only)

```yaml
review:
  - type: Textarea
    field: ch1GeneralComments
    args: 
      description: "General"
  
  - type: PopulateButton
    args:
      target: ch1GeneralComments
      compute:
        function: pdf_extract_comments  # Only gets annotations
        # ...
```

### After (LLM + Manual Comments)

```yaml
review:
  # General comments - prefilled by LLM
  - type: Textarea
    field: ch1GeneralComments
    args: 
      description: "General (LLM-assisted)"
  
  - type: PopulateButton
    args:
      target: ch1GeneralComments
      compute:
        function: llm_pdf_review  # Auto-generates initial review
        view_args:
          filename:
            display: "{Name}_thesis_ch1.pdf"
        args:
          directory: $HOME/Documents/theses/examined
          review_type: "general"
  
  # Detailed comments - from your PDF annotations
  - type: Textarea
    field: ch1DetailedComments
    args: 
      description: "Annotations"
  
  - type: PopulateButton
    args:
      target: ch1DetailedComments
      compute:
        function: pdf_extract_comments  # Keep existing annotation extraction
        view_args:
          filename:
            display: "{Name}_thesis_ch1.pdf"
        args:
          directory: $HOME/Documents/theses/examined
          comment_types: ["Highlight", "StrikeOut"]
```

## Advanced Usage

### Custom System Prompts

For specialized reviews, provide your own system prompt:

```yaml
compute:
  - function: llm_pdf_review
    field: ch3_methodology_review
    view_args:
      filename:
        display: "{Name}_thesis_ch3.pdf"
    args:
      directory: $HOME/Documents/theses/examined
      system_prompt: |
        You are an expert in statistical methodology. Review this chapter focusing on:
        1. Appropriateness of statistical methods
        2. Sample size justification
        3. Handling of confounding variables
        4. Validity of statistical conclusions
        Provide specific, actionable feedback in under 200 words.
```

### Multiple Review Types per Chapter

Generate different perspectives on the same content:

```yaml
compute:
  # General overview
  - function: llm_pdf_review
    field: ch1_general
    view_args:
      filename: {display: "{Name}_thesis_ch1.pdf"}
    args:
      directory: $HOME/Documents/theses/examined
      review_type: "general"
  
  # Strengths
  - function: llm_pdf_review
    field: ch1_strengths
    view_args:
      filename: {display: "{Name}_thesis_ch1.pdf"}
    args:
      directory: $HOME/Documents/theses/examined
      review_type: "strengths"
  
  # Areas for improvement
  - function: llm_pdf_review
    field: ch1_weaknesses
    view_args:
      filename: {display: "{Name}_thesis_ch1.pdf"}
    args:
      directory: $HOME/Documents/theses/examined
      review_type: "weaknesses"
```

### Batch Processing

Process all chapters at once in the compute section:

```yaml
compute:
  # Auto-generate summaries for all chapters
  - function: llm_pdf_review
    field: ch1_summary
    view_args:
      filename: {display: "{Name}_thesis_ch1.pdf"}
    args:
      directory: $HOME/Documents/theses/examined
      review_type: "summary"
  
  - function: llm_pdf_review
    field: ch2_summary
    view_args:
      filename: {display: "{Name}_thesis_ch2.pdf"}
    args:
      directory: $HOME/Documents/theses/examined
      review_type: "summary"
  
  # ... repeat for all chapters
```

## Cost Management

### Estimated Costs (using gpt-4o-mini)

- **Short chapter** (~10 pages): $0.15 - $0.30
- **Medium chapter** (~20 pages): $0.30 - $0.60
- **Long chapter** (~30 pages): $0.60 - $1.00

### Cost Control Features

1. **Budget Limits**: Set `budget_per_run` to prevent overspending
2. **Caching**: Enable `cache_enabled: true` to reuse previous results
3. **Context Limits**: Use `max_chars` to limit text sent to LLM
4. **Model Choice**: Use `gpt-4o-mini` for cost-effective reviews

```yaml
llm:
  default_model: gpt-4o-mini
  cache_enabled: true
  budget_per_run: 5.00  # Stop if costs exceed $5
  max_chars: 30000  # Limit context per document
```

## Best Practices

### 1. Start with Summaries

Begin by generating summaries to get oriented:

```yaml
review_type: "summary"  # Start here
```

Then move to more detailed reviews:

```yaml
review_type: "general"  # Balanced review
review_type: "technical"  # Deep dive
```

### 2. Combine LLM and Manual Review

Use LLM for initial comments, then:
- Review and edit the LLM output
- Add your own annotations using PDF tools
- Extract annotations with `pdf_extract_comments`

### 3. Handle Long Chapters

For chapters >30 pages, limit context:

```yaml
args:
  max_chars: 30000  # ~10-15 pages of text
```

Or review in sections:

```yaml
args:
  start_page: 1
  end_page: 15
```

### 4. Iterative Refinement

1. Generate initial review with `review_type: "general"`
2. Click button to populate field
3. Edit and refine the LLM output
4. Add specific annotations to PDF
5. Extract annotations with `pdf_extract_comments`

### 5. Quality Control

**Remember**: LLM output is a starting point, not the final review.

✅ **Do:**
- Review and edit all LLM-generated content
- Check for factual accuracy
- Verify specific page references
- Add your expert judgment
- Combine with manual annotations

❌ **Don't:**
- Use LLM output verbatim without review
- Rely on LLM for numerical accuracy
- Skip manual verification
- Forget to check against actual content

## Troubleshooting

### API Key Issues

**Error**: "Authentication failed"

**Solution**:
```bash
# Check your .env file exists
ls -la .env

# Verify the key is set
cat .env | grep API_KEY

# Make sure there are no quotes around the key in .env
# Good: OPENAI_API_KEY=sk-proj-...
# Bad:  OPENAI_API_KEY="sk-proj-..."
```

### PDF Not Found

**Error**: "File missing in pdf_extract_text"

**Solution**:
- Verify the PDF path is correct
- Check directory expansion (use `$HOME` not `~`)
- Verify file naming matches the pattern

### Budget Exceeded

**Error**: "Budget exceeded"

**Solution**:
```yaml
llm:
  budget_per_run: 10.00  # Increase budget
```

Or reduce costs:
```yaml
args:
  max_chars: 20000  # Reduce context
  review_type: "summary"  # Shorter reviews
```

### Rate Limits

**Error**: "Rate limit exceeded"

**Solution**: The system automatically retries with exponential backoff. If persistent:
- Wait a few minutes
- Check your API tier/limits
- Consider caching to reduce calls

## Examples

See the `examples/` directory:

- `examples/thesis_llm_review_example.yml` - Complete YAML configuration
- `examples/thesis_llm_review_example.py` - Programmatic usage
- `examples/llm_integration_example.yml` - General LLM examples
- `examples/llm_usage_example.py` - Python API examples

## Related Documentation

- [LLM Integration Guide](llm_integration.md) - Full LLM capabilities
- [Compute Framework](usage/compute.rst) - Understanding compute functions
- [CIP-0006](../cip/cip0006.md) - LLM integration design document

## Feedback and Contributions

This is a new feature! Please share:
- Use cases and workflows
- Suggested review types
- System prompt improvements
- Bug reports and feature requests

