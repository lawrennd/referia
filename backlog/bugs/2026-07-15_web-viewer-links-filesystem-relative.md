---
id: "2026-07-15_web-viewer-links-filesystem-relative"
title: "Viewer HTML links use filesystem-relative paths, breaking root-server mode"
status: "Proposed"
priority: "Medium"
created: "2026-07-15"
last_updated: "2026-07-15"
related_cips: ["000C"]
---

# Bug: Viewer HTML links use filesystem-relative paths, breaking root-server mode

## Description

`_referia.yml` viewer sections can produce anchor links whose `href` values
are relative filesystem paths, e.g.:

```html
<a href="../../../Library/CloudStorage/OneDrive-Personal/referia/theses/examined/pdfpages">
  here
</a>
```

In Jupyter / single-config mode this is harmless — the link isn't clickable
in a meaningful way.  In root-server mode the browser resolves the relative
URL against the current page URL:

```
current URL:  http://127.0.0.1:8764/theses/examined/introduction
3x ../ →      http://127.0.0.1:8764/
+ Library/CloudStorage/… →
              http://127.0.0.1:8764/Library/CloudStorage/OneDrive-Personal/referia/theses/examined/pdfpages
```

`_resolve_config_path` then tries to find:

```
<root>/Library/CloudStorage/.../pdfpages/_referia.yml
```

which does not exist → 404.

The correct root-relative URL would be `/theses/examined/pdfpages`.

## Root cause

Links are authored in `_referia.yml` as filesystem paths relative to the
config directory (or as absolute filesystem paths).  Neither translates
cleanly to a web URL in root-server mode.

Two sources:

1. **Explicit long relative paths** in `liquid:` viewer entries — e.g.
   `[here](../../../Library/CloudStorage/…/pdfpages)`.
2. **Data column values** containing filesystem paths that are interpolated
   via Liquid into href attributes.

## Proposed fix

In `WebReviewer.render_viewer_html()` (or in the route that renders the
viewer), post-process the returned HTML with a regex / BeautifulSoup pass
that:

1. For each `<a href="…">` in viewer HTML:
   - Resolve the href against the config directory (absolute path).
   - If the resolved path is under the server root, replace the href with the
     root-relative URL path (i.e. strip the root prefix and ensure a leading
     `/`).
   - If not under root, leave unchanged (external or genuinely relative link).

This post-processing should only run in root-server mode (when
`app.state.root` is set) and should be applied to viewer HTML only (not the
review form).

## Acceptance criteria

- `[here](../../../Library/…/pdfpages)` in viewer HTML becomes
  `<a href="/theses/examined/pdfpages">` when the linked directory is under
  the root.
- Links to paths outside the root are left unchanged.
- Single-config mode is unaffected.
- Unit test: `_rewrite_viewer_links(html, config_dir, root)` correctly
  rewrites in-root hrefs and leaves out-of-root hrefs alone.

## Workaround

Until fixed, use single-config mode (`referia serve --directory <path>`) for
configs with cross-config viewer links.
