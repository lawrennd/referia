---
id: "2026-07-16_parent-assessor-link-index"
title: "Parent assessor link should carry current index as query parameter"
status: "Proposed"
priority: "Medium"
created: "2026-07-16"
last_updated: "2026-07-16"
related_cips: ["000C"]
tags: ["web", "navigation", "parent-assessor", "linking"]
---

# Task: Parent assessor link should carry current index as query parameter

## Description

When a `_referia.yml` inherits from a parent via the `inherit:` key, referia
automatically inserts a "Parent assesser available here" link into the viewer
section (see `referia/config/interface.py` around line 609).

Currently the link points only to the parent assessor's root path — it does
not include any index information.  When a reviewer clicks the link they land
on whichever record the parent assessor last had open, not the record they are
currently reviewing.

### Current behaviour

```html
<a href="/path/to/parent" target="_blank">here</a>
```

### Desired behaviour

```html
<a href="/path/to/parent?index=Alice" target="_blank">here</a>
```

where `Alice` is the current index value of the row being reviewed.

## The challenge

The link is generated **statically** during config processing
(`Interface._process_parent()`), before any data is loaded.  The current index
is a runtime value that varies per record.  The fix therefore requires one of:

1. **Liquid/template variable in the href** — generate the href as a Liquid
   template string that is expanded at render time using the current row's
   index value.  e.g.
   `href="/path/to/parent?index={{ Name }}"` (where `Name` is the index
   column).

2. **Web-interface render-time injection** — in `web_review.py` or the
   HTMX/render layer, detect `parent-assessor-link` elements and rewrite their
   `href` to append `?index=<current_index>` when rendering each panel.

3. **HTMX client-side rewrite** — use a small JS snippet (similar to the
   existing `htmx:configRequest` listener) to append the current index to
   parent-assessor link hrefs before navigation.

Option 1 is the most consistent with how other dynamic values work in referia
viewer content.  The index column name is known from the interface at config
time and can be embedded in the template.

## Acceptance criteria

- Clicking the parent assessor link from record `X` opens the parent assessor
  directly at record `X` (i.e. `?index=X` is present in the URL).
- Works in both Jupyter and web interfaces (or is clearly documented as
  web-only with a Jupyter follow-up).
- The link still degrades gracefully if the parent assessor is opened in a
  context where the index does not exist (falls back to first record).

## Implementation notes

- The link is currently constructed at line 609 of
  `referia/config/interface.py` in `Interface._process_parent()`.
- The index column name is available from `self._parent._data["allocation"]["index"]`
  at config-processing time.
- In the web interface, the current index is the `index` query parameter on
  the current request URL and is available in `WebReviewer` as
  `reviewer._index`.
- Consider whether `subindex` should also be forwarded if the parent assessor
  uses selectors.

## Related

- CIP: 000C (multi-config root server — defines the `?index=` query-parameter
  scheme that the link should use)
- Bug fix that corrected the path from a filesystem path to a web-server path
  (conversation 2026-07-16)

## Progress updates

### 2026-07-16
Backlog created.  Root cause and three implementation options documented.
