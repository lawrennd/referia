---
id: "2026-07-14_web-inherit-not-applied"
title: "Web interface does not apply inherit: sections"
status: "Proposed"
priority: "Medium"
created: "2026-07-14"
last_updated: "2026-07-14"
related_cips: []
tags: ["web", "inherit", "rendering"]
---

# Task: Web interface does not apply `inherit:` sections

## Description

Some `_referia.yml` files use an `inherit:` section to pull in shared
configuration (viewer blocks, mappings, etc.) from a parent directory.  For
example, the thesis assessment config inherits from `../pdfpages/`:

```yaml
inherit:
  directory: ../pdfpages/
  writable: False
  append:
    - mapping
    - viewer
```

The Jupyter path resolves inheritance through `lynguine`/`referia`'s
`config/interface.py` machinery.  The web interface reads the config through
`WebReviewer.__init__`, but it is not yet confirmed whether inheritance is fully
resolved before the interface dict is stored in `self._interface`.

## Observed behaviour

When running the thesis assessment config in the web interface, only the widgets
defined directly in the local `_referia.yml` appear.  Any viewer or review
content provided by inherited files may be absent (needs confirmation with a
config that uses `inherit:` for review widgets).

## Acceptance Criteria

- [ ] Confirm whether `WebReviewer._interface` already contains fully-resolved
      inherited content or only the local file's content.
- [ ] If not resolved: implement inheritance loading in `WebReviewer.__init__`
      or in the config loading path it calls.
- [ ] Viewer blocks from inherited files appear in the web interface.
- [ ] Mappings from inherited files are applied correctly.
- [ ] Tests cover a config with `inherit:` and verify the inherited content
      appears.

## Implementation Notes

- Check `referia/config/interface.py` to see how it resolves `inherit:` and
  whether `WebReviewer` calls that machinery or reads the raw YAML directly.
- If `lynguine`'s `Interface` class already handles `inherit:`, it may just be
  a matter of ensuring `WebReviewer` uses `Interface` rather than raw `yaml.safe_load`.
- This bug may be partially masked by the template-expansion bug
  (`2026-07-14_web-template-expansion-missing`) — fix that first and re-test.

## Related

- Bug: 2026-07-14_web-template-expansion-missing
- Tenet: progressive-augmentation
