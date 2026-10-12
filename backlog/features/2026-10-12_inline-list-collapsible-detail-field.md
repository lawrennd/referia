---
id: "2026-10-12_inline-list-collapsible-detail-field"
title: "inline_list: collapsible display.detail_field per listing row"
status: "In Progress"
priority: "Medium"
created: "2026-10-12"
last_updated: "2026-10-12"
category: "features"
related_cips: ["0010"]
owner: "Neil D. Lawrence"
dependencies: []
tags:
- backlog
- web
- inline_list
- display
---

# Task: Collapsible detail field on inline_list rows

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

`display.layout: inline_list` already shows title, date, and `description` on each
row. Longer read-only text (talk `abstract`, proposal summary, etc.) should be
available without flooding the list — as a closed native `<details>` under the
row.

Add optional ``display.detail_field: <column>``. When set, each listing row whose
data has a non-empty value for that column renders:

```html
<details class="entry-detail" data-detail-field="abstract">
  <summary>Abstract</summary>
  <div class="entry-detail-body">…escaped text…</div>
</details>
```

Motivated by the talks calendar overview (`~/lawrennd/talks/_referia.yml`),
where front matter includes `abstract` and the short `description` line is
already used for subtitle · venue.

## Acceptance Criteria

- [x] `display.detail_field` readable via `WebReviewer.get_display_detail_field()`
- [x] `render_inline_listing(..., detail_field=…)` emits closed `<details>` when value present
- [x] Empty / missing values skip the details chrome
- [x] Wired through `routes._build_review_context` for `inline_list`
- [x] CSS for `.entry-detail` / `.entry-detail-body`
- [x] Unit tests in `tests/test_web_render.py`
- [x] Talks overview sets `detail_field: abstract`

## Implementation Notes

- Plain HTML-escaped text with `white-space: pre-wrap` (same safety model as `.desc`).
- Do not reuse review `Section` widgets here: listing extras go through
  `render_widget`, not `render_form`, so Section `<details>` would not apply.
- Summary label is the field name title-cased (`abstract` → `Abstract`).

## Related

- CIP: 0010
- Talks config: `/Users/neil/lawrennd/talks/_referia.yml`

## Progress Updates

### 2026-10-12

Task created; implementation landed in the same session (render + reviewer +
routes + CSS + tests + talks wiring).
