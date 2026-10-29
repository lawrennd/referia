---
id: "0017"
title: "An inline list remains usable when the working set is large"
status: "Proposed"
priority: "High"
created: "2026-10-29"
last_updated: "2026-10-29"
related_tenets:
- user-oriented-convenience
- template-driven-composition
- pragmatic-automation
stakeholders:
- Review authors
- Reviewers
- Maintainers
tags:
- requirement
- layout
- inline_list
- web
- htmx
---

# REQ-0017: An inline list remains usable when the working set is large

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Opening a review that lists the working set must stay interactive when that set has hundreds or thousands of rows. The first response shows a bounded window of entries. The author sets how many entries that window holds, and whether further entries **append** (scroll) or **replace** (a paged view). Filter and sort still apply to the full working set; populate-all still means every matching row, not only the rows on screen.

REQ-000E already says authors pick a named list composition. It does not say the GET may walk every row before the browser sees HTML. Catalogs survive today because they are thin and usually pre-filtered (CIP-001C’s today window). Unit workbenches with a widget strip per row do not.

**Why this matters**: *User-oriented convenience* is a page that opens. *Template-driven composition* keeps `inline_list` as the list document class rather than forcing every large review back to one-row `side_by_side`. *Pragmatic automation* refuses to peg the single worker on listing HTML.

**Who benefits**: Anyone serving `inline_list` over chunk, extract, or catalog rows numbered in the thousands; anyone whose seasonal `/year/` list outgrows one paint.

## Acceptance Criteria

- [ ] A first GET of `inline_list` returns in interactive time when the filtered working set has thousands of rows
- [ ] Remaining rows can be revealed without walking the whole working set on GET
- [ ] Authors can choose append (scroll / load more) or a paged view (prev / next, page k of n) without a new named layout
- [ ] Authors can set entries per page; omitting it uses a documented default; `0` restores the unbounded walk
- [ ] Filter and sort still address the full working set; the window is a view of that ordered set
- [ ] Populate-all still targets every working row, not only the painted page
- [ ] The same bound and paging choice apply on Jupyter even if infinite scroll is web-only

## Notes

This is listing GET cost, not populate-all duration (REQ-0010 / CIP-001D) and not “one record per URL” (CIP-0010 rejected that for catalogs).

## References

- Tenets as in YAML `related_tenets`
- REQ: [REQ-000E](./req000E_named-layout-compositions.md)
- CIP: [CIP-0020](../cip/cip0020.md)

## Progress Updates

### 2026-10-29

Requirement created (Proposed) after `07_grounds` `inline_list` over 2013 units pegged the 8003 worker on GET.

### 2026-10-29 (paging variant)

Acceptance now includes a paged view and an author-set page size, not only append.
