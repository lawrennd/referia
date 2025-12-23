---
id: "pragmatic-automation"
title: "Pragmatic Automation for Human Enhancement"
created: "2025-12-23"
last_updated: "2025-12-23"
version: "1.0"
tags:
- tenet
- automation
- human-enhancement
- pragmatic
- tools
---

# Pragmatic Automation for Human Enhancement

## Tenet

**Description**: Referia integrates whatever automation tools are most convenient and effective for helping humans complete assessments—whether that's LLMs, classical text analysis, PDF extraction, web APIs, or custom compute functions. The choice of tool is driven by what makes the reviewer's task easier, not by technological novelty. Automated functions provide analysis, summaries, and insights that humans review, edit, and approve. The integration prioritises human workflow enhancement: reduce mechanical work, surface relevant information, and support decision-making. Tools should be transparently accessible (reviewers understand what was automated), cost-effective (budget controls), and optional (graceful degradation). Humans remain in control and can override any automated output.

**Quote**: *"Use whatever tools help humans review better"*

**Examples**:
- LLM summaries when they add value
- Classical text analysis (word count, readability scores) when sufficient
- PDF text extraction and parsing
- API calls to external validation services
- Custom domain-specific compute functions
- PopulateButton widgets that run any compute function
- Cost-aware tool selection (use cheaper tools when adequate)
- All tools optional—works without any automation
- Automated outputs clearly marked and editable

**Counter-examples**:
- Using LLMs because they're trendy, not because they help
- Technology-first approach that ignores user needs
- Forcing reviewers to use automation they don't trust
- Replacing human judgment with automation
- Tool choices that prioritize showcase over utility
- No fallbacks when tools fail or are unavailable

**Conflicts**:
- **vs Innovation**: When new tools seem promising but unproven
- Resolution: Pragmatically evaluate if new tools actually help the reviewing task; adopt when proven useful
- **vs Simplicity**: When too many tool options confuse users
- Resolution: Provide sensible defaults; expose options progressively as needed

