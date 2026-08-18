---
id: "2026-08-18_cip000D-api-compat"
title: "Verify and fix LangChain 1.x API in llm.py and tests"
status: "Ready"
priority: "High"
created: "2026-08-18"
last_updated: "2026-08-18"
category: "infrastructure"
related_cips: ["000D"]
owner: "lawrennd"
dependencies:
- "2026-08-18_cip000D-bump-constraints"
tags:
- backlog
- langchain
- llm
- cip000D
---

# Task: Verify and fix LangChain 1.x API in llm.py and tests

## Description

After the 1.x lock resolves, keep `LLMManager` behaviour the same for reviewers. CIP-000D expects
the existing surface (`ChatOpenAI`, `ChatAnthropic`, `HumanMessage` / `SystemMessage` / `AIMessage`,
`invoke`) to survive; adjust constructor kwargs or patch paths if 1.x renamed them.

Do not change compute YAML names or `LLMManager.call()`'s public contract.

## Acceptance Criteria

- [ ] `referia/util/llm.py` works with LangChain 1.x (`ChatOpenAI` / `ChatAnthropic` constructors,
      `invoke`, `.content`)
- [ ] No remaining 0.x import paths (`langchain.chat_models`, `LLMChain`, etc.) in production code
- [ ] `poetry run pytest referia/tests/test_llm_integration.py -v` passes with `--with llm`
- [ ] `poetry run pytest tests/ -q` still passes
- [ ] Optional: one smoke of `llm_summarise` or `llm_pdf_review` if API keys are available (skip
      if not; do not block on live providers)

## Implementation Notes

```bash
poetry install --with llm
poetry run pytest referia/tests/test_llm_integration.py -v
poetry run pytest tests/ -q
```

Grep for `langchain.`, `LLMChain`, `ChatPromptTemplate`, `load_prompt`. Unit tests mock clients —
update `@patch('referia.util.llm.ChatOpenAI')` only if the import moves.

## Related

- CIP: [CIP-000D](../../cip/cip000D.md)
- Code: `referia/util/llm.py`, `referia/assess/compute.py`, `referia/tests/test_llm_integration.py`
- Previous: [`2026-08-18_cip000D-bump-constraints`](./2026-08-18_cip000D-bump-constraints.md)

## Progress Updates

### 2026-08-18

Task created when CIP-000D was Accepted.
