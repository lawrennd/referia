---
id: "2026-08-13_dependabot-langchain-ecosystem"
title: "Resolve Dependabot alerts in optional LangChain dependencies"
status: "Proposed"
priority: "Medium"
created: "2026-08-13"
last_updated: "2026-08-18"
category: "infrastructure"
related_cips: ["0006", "000D"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- security
- dependabot
- langchain
- llm
- cip0006
---

# Task: Resolve Dependabot alerts in optional LangChain dependencies

## Description

Six open Dependabot alerts affect packages in referia's **optional `llm` dependency group**
(`pyproject.toml` `[tool.poetry.group.llm]`). These packages were introduced under
**CIP-0006** (LLM Integration for Compute Framework, status: implemented).

Current locked versions use the **0.2.x / 0.3.x** LangChain line; GitHub advisories cite patched
versions on the **1.x** line. Upgrading may require a **major LangChain migration** and test updates
for `referia/assess/compute` LLM functions — not a simple patch bump.

| Package | Locked | Advisory patched | Alert # | Severity | GHSA / CVE |
|---------|--------|------------------|---------|----------|------------|
| langchain-core | 0.3.86 | ≥ 1.2.22 | 74 | high | GHSA-qh6h-p6c9-ff54 / CVE-2026-34070 (path traversal in legacy `load_prompt`) |
| langchain-core | 0.3.86 | ≥ 1.2.11 | 72 | low | GHSA-2g6r-c272-w58r (SSRF in token counting) |
| langchain | 0.3.30 | ≥ 1.3.9 | 77 | medium | GHSA-gr75-jv2w-4656 / CVE-2026-55443 |
| langchain-anthropic | 0.2.4 | ≥ 1.4.6 | 78 | medium | GHSA-gr75-jv2w-4656 / CVE-2026-55443 |
| langchain-openai | 0.2.14 | ≥ 1.1.14 | 76 | low | GHSA-r7w7-9xr2-qq2r / CVE-2026-41488 |
| langchain-text-splitters | 0.3.11 | ≥ 1.1.2 | 75 | medium | GHSA-fv5p-p927-qmxr / CVE-2026-41481 |

CIP-0006 documents security considerations (API keys, prompt injection, audit logging) but does
not track dependency CVE remediation.

## Acceptance Criteria

- [ ] Assess whether 0.3.x receives backported fixes or migration to LangChain 1.x is required
- [ ] Upgrade path chosen and documented (with breaking-change notes if migrating to 1.x)
- [ ] `poetry.lock` updated for all affected `llm` group packages
- [ ] LLM compute tests pass (`pytest` with llm group installed)
- [ ] Dependabot alerts #72, #74–#78 closed
- [ ] CIP-0006 security section updated if mitigation differs from upgrade (e.g. disabling vulnerable loaders)

## Implementation Notes

1. Review whether referia uses affected APIs (`load_prompt`, `HTMLHeaderTextSplitter.split_text_from_url`, image token counting).
2. If unused, document non-exposure and consider pinning/minimum versions without full 1.x migration.
3. LangChain 1.x migration scoped in **[CIP-000D](../../cip/cip000D.md)** (Proposed). Implement this
   backlog task after CIP-000D is **Accepted**.
4. Install group: `poetry install --with llm`

## Related

- CIP: [CIP-0006](../../cip/cip0006.md) — LLM Integration (implemented on 0.3.x)
- CIP: [CIP-000D](../../cip/cip000D.md) — LangChain 1.x migration (design; execute after acceptance)
- Dependabot: https://github.com/lawrennd/referia/security/dependabot
- Existing backlog `2025-12-21_fix-llm-integration-test.md` covers test failures, not CVEs.

## Progress Updates

### 2026-08-13

Task created from Dependabot alert triage. Related to CIP-0006 scope but no existing backlog for CVE remediation.

### 2026-08-18

Code audit confirms referia uses a narrow LangChain surface (`ChatOpenAI`, `ChatAnthropic`, message
types, `invoke`) and does not call vulnerable APIs (`load_prompt`, URL text splitters). Migration
to 1.x still required to close Dependabot alerts. **[CIP-000D](../../cip/cip000D.md)** created for
migration design; defer implementation until CIP is Accepted.
