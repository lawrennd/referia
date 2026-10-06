---
id: "2026-10-06_readme-docs-badges-and-links"
title: "Add README documentation badges and published-docs links"
status: "Ready"
priority: "Low"
created: "2026-10-06"
last_updated: "2026-10-06"
category: "documentation"
related_cips: ["0003"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-10-06_sphinx-orphan-toctree-warnings"
tags:
- backlog
- documentation
- readme
- badges
- readthedocs
- github-pages
---

# Task: Add README documentation badges and published-docs links

## Description

The referia README shows Tests and Codecov badges only. The repo already has
`.readthedocs.yml` and `.github/workflows/docs.yml` (Sphinx → GitHub Pages),
but the README does not advertise either build or link to published docs.

Mirror the lynguine README pattern:

- Documentation (GitHub Actions `docs.yml`) badge → GitHub Pages
- Read the Docs badge → `https://referia.readthedocs.io/` (confirm slug)
- Short Documentation bullet/link in the intro

Do this after orphan toctree warnings are cleared so badges are not green
over a broken or warning-noisy docs site.

## Acceptance Criteria

- [ ] README has a docs CI badge linking to the Actions workflow (and/or
      GitHub Pages URL once confirmed live).
- [ ] README has a Read the Docs badge linking to the live project (import
      / confirm project on readthedocs.org if missing).
- [ ] README intro includes a Documentation link to the canonical published
      site (prefer RTD; Pages as fallback if RTD not yet live).
- [ ] Badge URLs and project slug verified (no placeholder tokens).

## Implementation Notes

Lynguine reference:

```markdown
[![Documentation](https://github.com/lawrennd/lynguine/actions/workflows/docs.yml/badge.svg)](https://lawrennd.github.io/lynguine/)
[![ReadTheDocs](https://readthedocs.org/projects/lynguine/badge/?version=latest)](https://lynguine.readthedocs.io/en/latest/)
```

Confirm whether Codecov’s `YOUR_CODECOV_TOKEN` placeholder should be fixed
or removed in the same pass (optional; out of scope if unclear).

## Related

- Depends on: `2026-10-06_sphinx-orphan-toctree-warnings`
- CIP: 0003
- Config already present: `.readthedocs.yml`, `.github/workflows/docs.yml`

## Progress Updates

### 2026-10-06

Task created after noting missing README docs surface vs lynguine.
