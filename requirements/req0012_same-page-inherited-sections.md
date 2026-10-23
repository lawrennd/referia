---
id: "0012"
title: "Reviewers see inherited interface sections on the same page as the child"
status: "In Progress"
priority: "High"
created: "2026-10-22"
last_updated: "2026-10-23"
related_tenets:
- template-driven-composition
- user-oriented-convenience
- explicit-implicit-separation
stakeholders:
- Reviewers
- Review authors
tags:
- requirement
- inherit
- viewer
- review
- composition
- web
---

# REQ-0012: Reviewers see inherited interface sections on the same page as the child

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

When a `_referia.yml` inherits from another config, reviewers must be able to see the ancestor interface (viewer content and review sections) **on the same page** as the child, with ancestor material **above** the child's own sections. They must not have to open a separate parent assessor to recover that context.

The **default** page stays today's child view (parent is a link or a different URL). Switching to the stacked page is a reviewer-controlled option on the web request, not a required config change. That option must not change which files are loaded or what the session may write.

**Why this matters**: *Template-driven composition* treats inherit as reuse of a declared pattern, not a pointer to another window. *User-oriented convenience* keeps relationship, achievements, and letter (or pdfpages plus chapter review) in one reading. *Explicit–implicit separation* keeps inherit merge as an explicit config choice; the application then presents that chain without hiding where each block came from.

**Who benefits**: Reviewers working chained configs (people letters, thesis chapter assessments, marking that inherits a class list); authors who already share viewer and mapping through `inherit:` and currently duplicate parent context in the child viewer.

## Acceptance Criteria

- [ ] A child config can present ancestor `viewer:` and `review:` sections on the same page as its own, ancestor content above child content
- [ ] Each inherited block remains recognisable as coming from its ancestor (title or equivalent), not silently merged into the child's sections
- [ ] With no extra option, today's parent-link child view is unchanged
- [ ] On the web, a reviewer can switch to the stacked page through a browser-controlled option (bookmarkable) without editing `_referia.yml`
- [ ] That option cannot change loaded paths, inherit directories, or writability
- [ ] Ancestor review fields are not silently written through the child when inherit is not writable
- [ ] Deep inherit chains (parent of parent) appear in ancestor-first order, not only the immediate parent

## Notes

Distinct from REQ-000E named layouts: stacking inherited *content* is orthogonal to whether the page is `side_by_side` or `inline_list`. Distinct from REQ-0009: navigating to the parent URL remains available; this requirement is about not *needing* that navigation to see the ancestor sections.

## References

- Tenet: [template-driven-composition](../tenets/referia/template-driven-composition.md)
- Tenet: [user-oriented-convenience](../tenets/referia/user-oriented-convenience.md)
- Tenet: [explicit-implicit-separation](../tenets/referia/explicit-implicit-separation.md)
- Related: [REQ-0006](./req0006_template-driven-interfaces.md), [REQ-0008](./req0008_web-review-without-jupyter.md), [REQ-0009](./req0009_multi-config-web-hosting.md), [REQ-000E](./req000E_named-layout-compositions.md)

## Progress Updates

### 2026-10-23

CIP-0018 Accepted. Backlog tasks created. Status In Progress.

### 2026-10-22

Requirement created (Proposed). Paired with CIP-0018.

Revised the same day: default view stays today's child page; stacked composition is a web request option, not a required YAML knob.
