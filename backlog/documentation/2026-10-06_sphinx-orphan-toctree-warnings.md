---
id: "2026-10-06_sphinx-orphan-toctree-warnings"
title: "Resolve Sphinx orphan toctree warnings in docs/"
status: "Ready"
priority: "Medium"
created: "2026-10-06"
last_updated: "2026-10-06"
category: "documentation"
related_cips: ["0003", "000F"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- documentation
- sphinx
- toctree
- docs-build
---

# Task: Resolve Sphinx orphan toctree warnings

> Backlog tasks are DOING the work defined in CIPs (HOW).
> Related: CIP-0003 (documentation system), CIP-000F compression
> (added `usage/config_dialect` to the toctree correctly).

## Description

A local Sphinx HTML build (`poetry install --with docs` then
`sphinx-build -b html docs docs/_build/html`) emits
`document isn't included in any toctree [toc.not_included]` for several
source files under `docs/`. The build still produces HTML, but
`sphinx-build -W` treats these as errors, so clean CI / Read the Docs
strict builds will fail once warnings-as-errors is enabled.

Observed orphans (2026-10-06):

| Path | Likely disposition |
|------|--------------------|
| `docs/usage/assessment.rst` | Wire into toctree (usage section) |
| `docs/usage/basic_concepts.rst` | Wire into toctree (usage section) |
| `docs/usage/compute.rst` | Wire into toctree (usage section) |
| `docs/llm_integration.md` | Wire into toctree **or** exclude if superseded |
| `docs/llm_pdf_review.md` | Wire into toctree **or** exclude if superseded |
| `docs/whats_next_script.md` | Exclude (VibeSafe tooling, not product docs) **or** move out of `docs/` |
| `docs/yaml_frontmatter_examples.md` | Exclude / move (VibeSafe), unless we want it published |
| `docs/cips/cip0005.md` | Untracked draft; do **not** publish as-is — delete, move to `cip/`, or exclude |

`docs/usage/config_dialect.rst` is already in `docs/index.rst` and is **not**
an orphan.

## Acceptance Criteria

- [ ] Every file under `docs/` that Sphinx discovers is either listed in a
      toctree (or reached from one) **or** listed in `exclude_patterns` /
      moved out of the Sphinx source tree.
- [ ] `docs/index.rst` has a coherent Usage (or similar) section for the
      intended user guides (`basic_concepts`, `assessment`, `compute`,
      `config_dialect`, and any kept LLM guides).
- [ ] VibeSafe-only markdown (`whats_next_script`, `yaml_frontmatter_examples`)
      is not published as referia product documentation unless explicitly
      desired.
- [ ] Decision recorded for `docs/cips/cip0005.md` (remove, exclude, or
      promote); do not leave an untracked orphan that Sphinx still picks up
      when present.
- [ ] `poetry run sphinx-build -b html -W docs docs/_build/html` completes
      with **no** `toc.not_included` warnings (other pre-existing warnings
      may remain and should be listed in progress notes if still open).

## Implementation Notes

1. Prefer wiring real user guides into the toctree over blanket excludes.
2. For non-product docs, prefer `exclude_patterns` in `docs/conf.py` or
   relocating files outside `docs/` over publishing incomplete pages.
3. Optional: add a docs CI job or `docs/test_build.py` check that fails on
   `toc.not_included` once the orphans are cleared.
4. Do not commit `docs/_build/`.

## Related

- CIP: 0003, 000F
- Sphinx `exclude_patterns` / toctree: `docs/conf.py`, `docs/index.rst`
- Compression of CIP-000F already added `usage/config_dialect` correctly

## Progress Updates

### 2026-10-06

Task created after CIP-000F documentation compression / Sphinx verify.
Orphan list taken from a local HTML build with the poetry `docs` group
installed.
