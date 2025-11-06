# Migrating Your Thesis Review Config to Use LLM

## For: ~/OneDrive/referia/theses/examined/introduction/_referia.yml

This guide shows you exactly how to update your existing config to add LLM-powered auto-review.

## Step 1: Add LLM Configuration (at the top)

Add this after the `timestamp_field` line:

```yaml
title: "PhD Thesis Assessment: Introduction"
date: 2022-12-12
author: Neil D. Lawrence
description: Assess individual PhD theses starting with the introduction.
browser: Google Chrome.app
timestamp_field: "Introduction Timestamp"
created_field: "Introduction Created"

# ADD THIS NEW SECTION:
llm:
  default_provider: openai
  default_model: gpt-4o-mini  # Cost-effective, ~$0.30-0.60 per chapter
  cache_enabled: true
  budget_per_run: 5.00  # $5 budget for safety

global_consts:
  # ... rest of your config
```

## Step 2: Create .env File

In `~/OneDrive/referia/theses/examined/introduction/` create a `.env` file:

```bash
# Copy the template
cp ~/lawrennd/referia/examples/env_template.txt ~/OneDrive/referia/theses/examined/introduction/.env

# Edit to add your actual API key
# Change: OPENAI_API_KEY=your-openai-key-here
# To:     OPENAI_API_KEY=sk-proj-QQkGE9P5o...  (your actual key)
```

## Step 3: Update Chapter Review Sections

For each chapter, you currently have this pattern:

```yaml
# CURRENT (lines 367-406):
- type: Textarea
  field: ch1GeneralComments
  args: 
    description: "General"
    layout:
      width: 800px

- type: PopulateButton
  args:
    target: ch1GeneralComments
    compute:
      field: ch1GeneralComments
      function: pdf_extract_comments  # Only gets your manual PDF annotations
      view_args:
        filename:
          display: "{Name}_thesis_ch1.pdf"
      args:
        directory: $HOME/Documents/theses/examined
        comment_types: "FreeText"
      row_args:
        start_page: Ch1FP
```

### Option A: Replace with LLM (Recommended)

Change the PopulateButton function to use LLM:

```yaml
- type: Textarea
  field: ch1GeneralComments
  args: 
    description: "General (LLM-assisted)"  # Updated label
    layout:
      width: 800px

- type: PopulateButton
  args:
    target: ch1GeneralComments
    compute:
      field: ch1GeneralComments
      function: llm_pdf_review  # NEW: Auto-generates initial review
      view_args:
        filename:
          display: "{Name}_thesis_ch1.pdf"
      args:
        directory: $HOME/Documents/theses/examined
        review_type: "general"  # Options: general, strengths, weaknesses, technical, summary
        model: gpt-4o-mini
        max_chars: 30000  # Limits context for LLM
```

### Option B: Add Both (Most Flexible)

Keep your annotations AND add LLM:

```yaml
# General comments - LLM-generated
- type: Textarea
  field: ch1GeneralComments
  args: 
    description: "General (LLM-assisted)"
    layout:
      width: 800px

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

# Keep your existing annotation extraction (rename the button label)
- type: Textarea
  field: ch1DetailedComments
  args: 
    description: "Annotations (from PDF)"  # Keep this
    layout:
      width: 800px

- type: PopulateButton
  args:
    target: ch1DetailedComments
    compute:
      field: ch1DetailedComments
      function: pdf_extract_comments  # Keep this for your manual annotations
      view_args:
        filename:
          display: "{Name}_thesis_ch1.pdf"
      args:
        directory: $HOME/Documents/theses/examined
        comment_types: ["Highlight", "StrikeOut"]
      row_args:
        start_page: Ch1FP
```

## Step 4: Repeat for All Chapters

Apply the same pattern for:
- Abstract (lines 278-316)
- Acknowledgments (lines 272-336)
- Table of Contents (lines 318-361)
- Foreword, Prologue
- Chapter 1-12 (lines 363-901)
- Epilogue, References, Appendix, Index

Just change:
- `ch1` → `abstract`, `toc`, `ch2`, etc.
- `Ch1FP` → `AbstractFP`, `ToCFP`, `Ch2FP`, etc.
- The filename pattern

## Step 5: Test with One Chapter First

1. Start with just Chapter 1
2. Open referia with your modified config
3. Click the new "PopulateButton" 
4. Review the LLM-generated content
5. Edit and refine as needed
6. If satisfied, apply to other chapters

## Different Review Types for Different Chapters

You can use different review types for different chapters:

```yaml
# Introduction chapter - focus on summary
- function: llm_pdf_review
  args:
    review_type: "summary"

# Methodology chapter - technical review
- function: llm_pdf_review
  args:
    review_type: "technical"

# Results chapter - general review
- function: llm_pdf_review
  args:
    review_type: "general"

# Conclusion - strengths
- function: llm_pdf_review
  args:
    review_type: "strengths"
```

## Custom Review Prompts

For very specific needs, use custom prompts:

```yaml
- function: llm_pdf_review
  args:
    directory: $HOME/Documents/theses/examined
    system_prompt: |
      You are examining a PhD thesis introduction chapter. Focus on:
      1. Research question clarity and motivation
      2. Literature review comprehensiveness
      3. Contribution and novelty statement
      4. Chapter structure and flow
      Provide constructive feedback in under 200 words.
```

## Cost Estimates

For a typical thesis with 8 chapters:

- **First run**: ~$2-5 (generates all reviews)
- **Subsequent runs**: Nearly free (cached)
- **Per chapter**: $0.15-0.60 with gpt-4o-mini

## Workflow Recommendations

### First Time Setup (1-2 hours)
1. Modify config for Chapter 1 only
2. Test with one candidate
3. Review and refine prompts
4. Apply to all chapters

### Per Thesis Review (30 mins per thesis)
1. Click populate buttons for all chapters
2. LLM generates initial reviews (~2-3 minutes)
3. Read each chapter while editing LLM comments
4. Add your manual annotations to PDF
5. Extract your annotations using existing buttons
6. Combine LLM + manual comments in final report

### Best Practice Workflow
1. **First pass**: LLM generates general comments
2. **Second pass**: You read and annotate PDF
3. **Third pass**: Extract annotations, combine with LLM text
4. **Final**: Edit and refine all comments

## Full Example for One Chapter

Here's a complete example for Chapter 1:

```yaml
# In review section:
- type: Markdown
  liquid: "### Chapter 1"
  args:
    layout:
      width: 800px

# General comments - LLM assisted
- type: Textarea
  field: ch1GeneralComments
  args: 
    description: "General Comments (click button to auto-generate)"
    layout:
      width: 800px

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
        max_chars: 30000

# Detailed comments - Your PDF annotations
- type: Textarea
  field: ch1DetailedComments
  args: 
    description: "Detailed Comments (from your PDF annotations)"
    layout:
      width: 800px

- type: PopulateButton
  args:
    target: ch1DetailedComments
    compute:
      field: ch1DetailedComments
      function: pdf_extract_comments
      view_args:
        filename:
          display: "{Name}_thesis_ch1.pdf"
      args:
        directory: $HOME/Documents/theses/examined
        comment_types: ["Highlight", "StrikeOut"]
      row_args:
        start_page: Ch1FP
```

## Questions?

See full documentation in:
- `~/lawrennd/referia/docs/llm_pdf_review.md`
- `~/lawrennd/referia/examples/thesis_llm_review_example.yml`

## Quick Reference

| Current Function | Purpose | Replace With |
|-----------------|---------|--------------|
| `pdf_extract_comments` | Extract your manual PDF annotations | Keep for detailed comments |
| (none) | Auto-generate initial review | Add `llm_pdf_review` for general comments |

| Review Type | Use For | Output Length |
|-------------|---------|---------------|
| `summary` | Quick overview | ~150 words |
| `general` | Balanced review | ~200 words |
| `strengths` | Positive aspects | ~200 words |
| `weaknesses` | Areas to improve | ~200 words |
| `technical` | Detailed assessment | ~250 words |

