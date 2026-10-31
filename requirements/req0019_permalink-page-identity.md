---
id: "0019"
title: "Study pages share a permalink identity with Jekyll and are not named after the tool"
status: "In Progress"
priority: "High"
created: "2026-10-31"
last_updated: "2026-10-31"
related_tenets:
- user-oriented-convenience
- explicit-implicit-separation
- document-centric-management
stakeholders:
- Review authors
- Dialogue / public-engagement analysts
- Maintainers
tags:
- requirement
- web
- routing
- jekyll
- permalink
---

# REQ-0019: Study pages share a permalink identity with Jekyll and are not named after the tool

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

A DODS (or other public) study can be both a live referia session and a Jekyll site from the same markdown files. The public URL of each stage is an explicit permalink in that file’s YAML, not a path inferred from a tool-branded filename or from the directory that happened to hold `_referia.yml`.

The page files themselves are ordinary Jekyll pages. Their names are not `referia.md` or `_referia.md`. Referia still recognises them as configs. Thesis and grant reviews that keep `_referia.yml` and filesystem URLs continue to work.

**Why this matters**: Underscore files are Jekyll’s “not a page” convention. Naming the public write-up after the tool couples the site to the runtime. The URL should be a declared identity both engines read.

**Who benefits**: Analysts handing a reconstruction to a colleague who reads GitHub Pages; authors who already use Giki layouts and permalinks.

## Acceptance Criteria

- [ ] A markdown page with Jekyll frontmatter can be a referia config without being named `_referia.yml`, `_referia.md`, or `referia.md`
- [ ] The public URL of that page is the permalink in its YAML, and Jekyll and referia agree on that URL
- [ ] A server mode exists that addresses configs by that permalink tree rather than by filesystem-relative `_referia.yml` paths
- [ ] Existing path-based root serving (`_referia.yml` under a directory → `/that/directory/`) still works when that mode is off
- [ ] Store paths in the YAML still resolve from the file’s folder, not from the permalink (top-level study pages use `directory: info` and `directory: 01_turns`)

## Notes

REQ-0009 remains the outcome for path-derived multi-config hosting. This requirement adds a second identity: permalink-declared pages that Jekyll can render.

Do not require Jekyll at serve time. The live session still runs widgets; Jekyll renders the markdown body only.

## References

- **Related Tenets**: user-oriented-convenience, explicit-implicit-separation, document-centric-management
- **Related requirements**: REQ-0009 (path URLs), REQ-0010 (chained study configs)

## Progress Updates

### 2026-10-31
Proposed after converting DODS stages to markdown and hitting Jekyll’s underscore skip plus the mismatch between filesystem URLs and Giki permalinks.
