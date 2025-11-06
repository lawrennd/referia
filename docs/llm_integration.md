# LLM Integration for Referia

## Overview

Referia now supports Large Language Model (LLM) integration through the compute framework. This enables AI-powered text analysis, generation, summarisation, and transformation operations using a simple declarative configuration.

## Quick Start

Get started in 3 simple steps:

```bash
# 1. Install LLM dependencies
poetry install --with llm

# 2. Set up your API key using .env file
cp examples/env_template.txt .env
nano .env  # Add your OPENAI_API_KEY

# 3. Use in your configuration
```

```yaml
compute:
  - function: llm_summarise
    field: summary
    row_args:
      text: review_text
```

That's it! Your LLM integration is ready to use.

## Installation

LLM capabilities are optional. To install the required dependencies:

```bash
poetry install --with llm
```

This installs:
- `langchain` - LLM framework
- `langchain-openai` - OpenAI integration
- `langchain-anthropic` - Anthropic integration
- `openai` - OpenAI Python SDK
- `anthropic` - Anthropic Python SDK
- `tenacity` - Retry logic
- `diskcache` - Response caching

## Configuration

### API Keys

Referia supports multiple ways to provide API keys (in order of precedence):

1. **Direct configuration** (in YAML - not recommended for security)
2. **Environment variables**
3. **.env file** (recommended for development)

#### Option 1: Using .env File (Recommended) 🌟

Create a `.env` file in your project root:

```bash
# Copy the template
cp examples/env_template.txt .env

# Edit with your actual keys
nano .env
```

Your `.env` file should contain:

```bash
OPENAI_API_KEY=sk-your-actual-key-here
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

The `.env` file is automatically loaded when you use referia's LLM features.

**Important:** The `.env` file is already in `.gitignore` to prevent accidentally committing your API keys!

#### Option 2: Environment Variables

Set your API key as an environment variable:

```bash
# For OpenAI
export OPENAI_API_KEY="your-openai-key"

# For Anthropic
export ANTHROPIC_API_KEY="your-anthropic-key"
```

To make these permanent, add them to your shell profile (`~/.zshrc` or `~/.bashrc`).

#### Option 3: Configuration File (Not Recommended)

You can also specify keys directly in your interface configuration, but this is **not recommended** for security reasons:

```yaml
llm:
  api_keys:
    openai: "sk-your-key"  # Don't commit this!
    anthropic: "sk-ant-your-key"
```

### Configuration File

Add an `llm` section to your interface configuration:

```yaml
llm:
  default_provider: "openai"  # or "anthropic"
  default_model: "gpt-4o-mini"
  
  # Optional: API keys in config (not recommended - use environment variables)
  # api_keys:
  #   openai: ${OPENAI_API_KEY}
  
  # Retry configuration
  retry_attempts: 3
  retry_backoff: 2
  
  # Caching
  cache_enabled: true
  cache_dir: ".llm_cache"
  cache_ttl: 3600  # 1 hour
  
  # Budget enforcement (optional)
  budget_per_run: 1.00  # Maximum $1 per run
```

## Available Functions

### llm_complete

General-purpose text completion.

```yaml
compute:
  - function: llm_complete
    field: response
    row_args:
      text: prompt_text
    args:
      model: "gpt-4o-mini"
      temperature: 0.7
      max_tokens: 200
      system_prompt: "You are a helpful assistant."
```

**Arguments:**
- `text` (required): Input text/prompt
- `model`: Model to use (default: "gpt-4o-mini")
- `temperature`: 0-1, higher = more creative (default: 0.7)
- `max_tokens`: Maximum response length
- `system_prompt`: System prompt to guide behavior

### llm_summarise

Specialised text summarisation.

```yaml
compute:
  - function: llm_summarise
    field: summary
    row_args:
      text: review_text
    args:
      model: "gpt-4o-mini"
      temperature: 0.3
      max_tokens: 150
```

**Arguments:**
- `text` (required): Text to summarise
- `model`: Model to use (default: "gpt-4o-mini")
- `temperature`: Sampling temperature (default: 0.3 for consistency)
- `max_tokens`: Maximum summary length (default: 150)
- `system_prompt`: Custom system prompt (optional)

### llm_extract

Extract structured information from text.

```yaml
compute:
  - function: llm_extract
    field: key_points
    row_args:
      text: document_text
    args:
      extraction_type: "3-5 key points as a bullet list"
      model: "gpt-4o-mini"
      temperature: 0.2
```

**Arguments:**
- `text` (required): Text to extract from
- `extraction_type` (required): What to extract (e.g., "key points", "action items", "dates")
- `model`: Model to use (default: "gpt-4o-mini")
- `temperature`: Sampling temperature (default: 0.2 for precision)

### llm_classify

Classify text into categories.

```yaml
compute:
  - function: llm_classify
    field: sentiment
    row_args:
      text: review_text
    args:
      categories: ["positive", "negative", "neutral"]
      model: "gpt-4o-mini"
      temperature: 0.1
```

**Arguments:**
- `text` (required): Text to classify
- `categories` (required): List of possible categories
- `model`: Model to use (default: "gpt-4o-mini")
- `temperature`: Sampling temperature (default: 0.1 for consistency)

### llm_chat

Chat-style interaction with context.

```yaml
compute:
  - function: llm_chat
    field: response
    row_args:
      text: user_message
      context: conversation_history
    args:
      model: "gpt-4o-mini"
      temperature: 0.7
      system_prompt: "You are a helpful assistant."
```

**Arguments:**
- `text` (required): User message
- `context`: Previous conversation context (optional)
- `model`: Model to use (default: "gpt-4o-mini")
- `temperature`: Sampling temperature (default: 0.7)

## Supported Models

### OpenAI Models

- `gpt-4o`: Most capable, expensive
- `gpt-4o-mini`: **Recommended** - Fast, cheap, high quality
- `gpt-4-turbo`: Previous generation, powerful
- `gpt-3.5-turbo`: Older, cheapest

### Anthropic Models

- `claude-3-5-sonnet-20241022`: Latest Claude, very capable
- `claude-3-opus-20240229`: Most powerful Claude
- `claude-3-sonnet-20240229`: Balanced
- `claude-3-haiku-20240307`: **Recommended** - Fast and cheap

## Cost Management

### Token Tracking

The system automatically tracks token usage and costs:

```python
from referia.util.llm import get_llm_manager

manager = get_llm_manager()
# ... make some calls ...

summary = manager.get_cost_summary()
print(summary)
# {
#   "total_calls": 5,
#   "total_tokens": 2500,
#   "total_cost": 0.0042,
#   "budget_remaining": 0.9958
# }
```

### Budget Enforcement

Set a budget limit to prevent runaway costs:

```yaml
llm:
  budget_per_run: 1.00  # Maximum $1 per run
```

When the budget is exceeded, a `LLMBudgetError` is raised.

### Cost Optimization Tips

1. **Use cheap models**: `gpt-4o-mini` or `claude-3-haiku-20240307` for most tasks
2. **Enable caching**: Reuse responses for identical prompts
3. **Limit max_tokens**: Set appropriate limits for each task
4. **Lower temperature**: Use 0.1-0.3 for deterministic tasks
5. **Batch similar operations**: Process multiple items together

## Caching

Responses are automatically cached by default to reduce costs and improve performance:

- **Cache key**: Hash of (prompt, model, temperature, other parameters)
- **TTL**: Configurable (default: 1 hour)
- **Storage**: Disk-based (using diskcache)

To disable caching for a specific call:

```yaml
compute:
  - function: llm_summarise
    field: summary
    row_args:
      text: review_text
    args:
      use_cache: false  # Disable caching for this call
```

## Error Handling

### Automatic Retry

Failed requests are automatically retried with exponential backoff:

```yaml
llm:
  retry_attempts: 3
  retry_backoff: 2  # Wait 1s, 2s, 4s between retries
```

### Fallback Functions

You can specify a fallback function if LLM fails:

```yaml
compute:
  - function: llm_summarise
    field: summary
    row_args:
      text: review_text
    args:
      fallback_function: text_summarizer  # Use classical summarizer if LLM fails
```

## Examples

### Example 1: Review Summarisation

```yaml
llm:
  default_model: "gpt-4o-mini"
  cache_enabled: true

compute:
  - function: llm_summarise
    field: summary
    row_args:
      text: review_text
    args:
      temperature: 0.3
      max_tokens: 100
```

### Example 2: Sentiment Analysis

```yaml
compute:
  - function: llm_classify
    field: sentiment
    row_args:
      text: review_text
    args:
      categories: ["positive", "negative", "neutral", "mixed"]
      temperature: 0.1
```

### Example 3: Multi-Step Analysis

```yaml
compute:
  # Step 1: Extract key points
  - function: llm_extract
    field: key_points
    row_args:
      text: review_text
    args:
      extraction_type: "3-5 main points as bullet list"
  
  # Step 2: Generate response based on key points
  - function: llm_complete
    field: response_draft
    row_args:
      text: key_points
    args:
      system_prompt: "Draft a response addressing these key points."
      temperature: 0.7
```

### Example 4: Using Claude

```yaml
compute:
  - function: llm_summarise
    field: claude_summary
    row_args:
      text: review_text
    args:
      model: "claude-3-haiku-20240307"
      temperature: 0.3
```

## Programmatic Usage

```python
from referia.util.llm import get_llm_manager

# Get manager
manager = get_llm_manager({
    "cache_enabled": True,
    "budget_per_run": 0.50
})

# Make a call
response = manager.call(
    prompt="Summarise this text: ...",
    model="gpt-4o-mini",
    temperature=0.3
)

# Check costs
summary = manager.get_cost_summary()
print(f"Cost: ${summary['total_cost']:.4f}")
```

## Troubleshooting

### "LangChain is not installed"

Install LLM dependencies:
```bash
poetry install --with llm
```

### "API key not found"

Set your API key:
```bash
export OPENAI_API_KEY="your-key"
```

### "Budget exceeded"

Increase your budget or optimize your prompts:
```yaml
llm:
  budget_per_run: 5.00  # Increase limit
```

### Slow responses

1. Enable caching (if not already enabled)
2. Use faster models (gpt-4o-mini, claude-3-haiku-20240307)
3. Reduce max_tokens
4. Consider batching requests

## Best Practices

1. **Start with cheap models**: Use `gpt-4o-mini` for development
2. **Enable caching**: Saves money and improves performance
3. **Set budgets**: Prevent unexpected costs
4. **Use appropriate temperatures**: 
   - 0.1-0.3 for factual/deterministic tasks
   - 0.7-0.9 for creative tasks
5. **Limit max_tokens**: Set sensible limits for each task
6. **Test with small datasets**: Before running on large datasets
7. **Monitor costs**: Check `get_cost_summary()` regularly

## Reference

For implementation details, see:
- [CIP-0006: LLM Integration](../cip/cip0006.md)
- [LLM Manager API](../referia/util/llm.py)
- [Compute Functions](../referia/assess/compute.py)

## Support

For issues or questions:
- Check examples: `examples/llm_usage_example.py`
- Review tests: `referia/tests/test_llm_integration.py`
- See CIP-0006 for design decisions and architecture

