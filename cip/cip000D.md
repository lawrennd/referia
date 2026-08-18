---
author: "lawrennd"
created: "2026-08-18"
id: "000D"
last_updated: "2026-08-18"
status: "Proposed"
compressed: false
related_requirements: []
related_cips: ["0006"]
tags:
- cip
- langchain
- llm
- security
- dependabot
- migration
title: "LangChain 1.x Migration for LLM Integration"
---

# CIP-000D: LangChain 1.x Migration for LLM Integration

## Status

- [x] Proposed — Initial documentation complete
- [ ] Accepted — Plan reviewed and approved
- [ ] In Progress — Migration underway
- [ ] Implemented — Code and lockfile updated
- [ ] Closed — Tests pass, Dependabot alerts closed, docs updated
- [ ] Rejected
- [ ] Deferred

## Summary

Migrate referia's optional `llm` dependency group from LangChain **0.2.x / 0.3.x** to **1.x** so
Dependabot security alerts can be closed. CIP-0006 implemented LLM compute functions on the 0.3
line; advisories cite patched versions only on 1.x, with no indication of backported fixes for
0.3.x.

This CIP covers dependency constraints, code compatibility, test updates, and documentation — not
runtime behaviour changes for reviewers.

## Motivation

### Dependabot alerts (open as of 2026-08-18)

Six alerts affect packages in `[tool.poetry.group.llm]`:

| Package | Locked | Patched | Alert # | Severity | Issue |
|---------|--------|---------|---------|----------|-------|
| langchain-core | 0.3.86 | ≥ 1.2.22 | 74 | high | Path traversal in legacy `load_prompt` (CVE-2026-34070) |
| langchain-core | 0.3.86 | ≥ 1.2.11 | 72 | low | SSRF in token counting (GHSA-2g6r-c272-w58r) |
| langchain | 0.3.30 | ≥ 1.3.9 | 77 | medium | CVE-2026-55443 |
| langchain-anthropic | 0.2.4 | ≥ 1.4.6 | 78 | medium | CVE-2026-55443 |
| langchain-openai | 0.2.14 | ≥ 1.1.14 | 76 | low | CVE-2026-41488 |
| langchain-text-splitters | 0.3.11 | ≥ 1.1.2 | 75 | medium | CVE-2026-41481 |

### Why a CIP, not a backlog-only fix

- **Major version jump** across five coordinated packages
- **Multiple touchpoints**: `pyproject.toml`, `poetry.lock`, `referia/util/llm.py`, compute
  registration, tests, `docs/llm_integration.md`
- **Design choices**: confirm minimal LangChain surface area, avoid reintroducing deprecated
  patterns from CIP-0006 sketches (`LLMChain`, legacy import paths)
- Backlog item `2026-08-13_dependabot-langchain-ecosystem.md` tracks alert closure; this CIP
  defines *how* to migrate

## Detailed Description

### Current LangChain usage (audit)

Referia's production LLM code uses a **narrow API surface** through `referia/util/llm.py`:

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
# ...
client.invoke(messages, **call_kwargs)
```

Compute functions in `referia/assess/compute.py` call `LLMManager.call()` only; they do not import
LangChain directly.

**Not used** (relevant to CVE exposure):

- `load_prompt` / filesystem prompt loading (alert #74)
- `HTMLHeaderTextSplitter.split_text_from_url` (alert #75)
- Image token counting paths (alert #72)
- Legacy `langchain.chains.LLMChain` or `ChatPromptTemplate` (CIP-0006 examples only)

`langchain` and `langchain-text-splitters` are **transitive** dependencies (pulled by
`langchain-openai` / `langchain-anthropic` ecosystem), not direct imports in referia code.

**Implication**: Runtime exposure to several CVE code paths is likely **low**, but Dependabot still
reports vulnerable lockfile versions. Upgrading to 1.x is the supported remediation path.

### Target dependency set

Update `[tool.poetry.group.llm.dependencies]` to aligned 1.x constraints (minimums from advisories):

```toml
langchain = "^1.3.9"
langchain-core = "^1.2.22"
langchain-openai = "^1.1.14"
langchain-anthropic = "^1.4.6"
# langchain-text-splitters resolves transitively; pin explicitly if needed for alert #75
langchain-text-splitters = "^1.1.2"
```

Retain existing non-LangChain llm group deps (`openai`, `anthropic`, `tenacity`, `diskcache`,
`python-dotenv`) unless Poetry resolution requires minor bumps.

### Expected code changes

LangChain 1.x largely preserves the patterns referia already uses:

1. **`ChatOpenAI` / `ChatAnthropic`** — verify constructor kwargs (`max_tokens`, `temperature`,
   `api_key`) against 1.x docs; adjust if renamed or deprecated
2. **`invoke(messages)`** — confirm return type still exposes `.content`
3. **Message types** — `HumanMessage`, `SystemMessage`, `AIMessage` remain in `langchain_core.messages`
4. **Tests** — update mocks/patch paths if import locations change; re-run with
   `poetry install --with llm`

No change to compute YAML API or `LLMManager` public interface is intended.

### Out of scope

- Promoting LLM infrastructure to lynguine (future CIP per CIP-0006)
- Replacing LangChain with direct OpenAI/Anthropic SDK calls
- diskcache alert #73 (separate backlog; no upstream patch)
- CodeQL findings in `referia/web/routes.py`

### Alternatives considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Upgrade to LangChain 1.x** | Closes alerts; stays on supported line | Major bump; test churn | **Preferred** |
| Document non-exposure, defer upgrade | No code change | Alerts remain open; lockfile still flagged | Reject for production hygiene |
| Remove `langchain` meta-package; depend only on integration packages | Smaller dependency tree | May not clear transitive alert on text-splitters | Partial; still need 1.x versions |
| Drop LangChain; use SDKs directly | Fewer deps | Large rewrite of CIP-0006 work | Defer |

## Implementation Plan

1. **Spike (half day)**
   - Create branch `cip000D-langchain-1x-migration`
   - Bump constraints in `pyproject.toml`
   - Run `poetry update langchain langchain-core langchain-openai langchain-anthropic langchain-text-splitters --with llm`
   - Note any Poetry conflicts

2. **Code compatibility**
   - Run LLM unit tests: `poetry run pytest referia/tests/test_llm_integration.py -v`
   - Fix `referia/util/llm.py` if 1.x API differs
   - Grep for any remaining 0.x import paths

3. **Integration validation**
   - Optional: run integration-marked tests with API keys
   - Smoke-test one compute workflow (`llm_summarise` or `llm_pdf_review`) from a notebook or script

4. **Documentation**
   - Update `docs/llm_integration.md` version references
   - Add migration note to CIP-0006 "Future Enhancements" or cross-link

5. **Security verification**
   - Push to `main`; confirm Dependabot alerts #72, #74–#78 close
   - Mark backlog `2026-08-13_dependabot-langchain-ecosystem.md` completed

## Backward Compatibility

- **Compute YAML**: unchanged — users keep the same `compute:` function names and args
- **Optional install**: `poetry install --with llm` remains the install path
- **Graceful degradation**: referia without llm group unchanged
- **Breaking risk**: internal only if LangChain 1.x changes `invoke` response shape; covered by tests

## Testing Strategy

```bash
poetry install --with llm
poetry run pytest referia/tests/test_llm_integration.py -v
poetry run pytest tests/ -q   # full suite without requiring API keys
```

- Unit tests mock LangChain clients — update patch targets if imports move
- Integration tests (skipped without keys) validate real provider calls after migration
- No new tests unless 1.x exposes regressions in caching or retry paths

## Related Requirements

None formally tracked. Security remediation aligns with pragmatic-automation and user-oriented
convenience tenets (optional LLM group stays optional; alerts cleared without changing reviewer UX).

## Implementation Status

- [ ] Dependency constraints bumped to LangChain 1.x minimums
- [ ] `poetry.lock` updated for llm group
- [ ] `referia/util/llm.py` verified/updated for 1.x API
- [ ] LLM tests pass
- [ ] Full test suite passes
- [ ] Documentation updated
- [ ] Dependabot alerts #72, #74–#78 closed

## References

- [CIP-0006](./cip0006.md) — original LLM integration (implemented on 0.3.x)
- Backlog: `backlog/infrastructure/2026-08-13_dependabot-langchain-ecosystem.md`
- Code: `referia/util/llm.py`, `referia/assess/compute.py` (`_llm_functions_list`)
- [LangChain v1 migration guide](https://python.langchain.com/docs/versions/v0_2/)
- Dependabot: https://github.com/lawrennd/referia/security/dependabot
