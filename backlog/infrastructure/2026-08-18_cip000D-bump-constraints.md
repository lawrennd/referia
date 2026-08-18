---
id: "2026-08-18_cip000D-bump-constraints"
title: "Bump optional llm group to LangChain 1.x (pyproject + lock)"
status: "Ready"
priority: "High"
created: "2026-08-18"
last_updated: "2026-08-18"
category: "infrastructure"
related_cips: ["000D"]
owner: "lawrennd"
dependencies: []
tags:
- backlog
- security
- dependabot
- langchain
- llm
- cip000D
---

# Task: Bump optional llm group to LangChain 1.x

## Description

CIP-000D spike: move `[tool.poetry.group.llm.dependencies]` from the 0.2/0.3 line to advisory
minimums on 1.x, then refresh `poetry.lock`.

Target constraints:

```toml
langchain = "^1.3.9"
langchain-core = "^1.2.22"
langchain-openai = "^1.1.14"
langchain-anthropic = "^1.4.6"
langchain-text-splitters = "^1.1.2"
```

Keep non-LangChain llm-group packages (`openai`, `anthropic`, `tenacity`, `diskcache`,
`python-dotenv`) unless Poetry requires a minor bump. Do not change `referia/util/llm.py` in this
task unless the lock cannot resolve without it.

Work on branch `cip000D-langchain-1x-migration`.

## Acceptance Criteria

- [ ] `pyproject.toml` llm-group LangChain packages use the 1.x constraints above
- [ ] `poetry.lock` resolves those packages at or above the patched versions
- [ ] `poetry install --with llm` succeeds
- [ ] Poetry conflicts (if any) are recorded in this task or in CIP-000D

## Implementation Notes

```bash
git checkout -b cip000D-langchain-1x-migration
# edit pyproject.toml
poetry update langchain langchain-core langchain-openai langchain-anthropic langchain-text-splitters --with llm
```

`langchain` and `langchain-text-splitters` are currently transitive; pin them explicitly so
Dependabot alerts #77 and #75 can close.

## Related

- CIP: [CIP-000D](../../cip/cip000D.md)
- Next: [`2026-08-18_cip000D-api-compat`](./2026-08-18_cip000D-api-compat.md)

## Progress Updates

### 2026-08-18

Task created when CIP-000D was Accepted.
