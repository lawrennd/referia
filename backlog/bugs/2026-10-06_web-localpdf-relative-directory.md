---
id: "2026-10-06_web-localpdf-relative-directory"
title: "Web localpdf/editpdf relative directories resolve against process cwd, not config directory"
status: "Ready"
priority: "High"
created: "2026-10-06"
last_updated: "2026-10-06"
category: "bugs"
related_cips: ["000B"]
owner: "Neil D. Lawrence"
dependencies: ["2026-07-13_web-document-serving"]
tags:
- backlog
- web
- documents
- pdf
- localpdf
- path-resolution
---

# Bug: Resolve relative `localpdf` / `editpdf` directories against the config directory

> Backlog tasks are DOING the work defined in CIPs (HOW).
> Linked CIP: 000B (web display). Related feature task:
> `2026-07-13_web-document-serving`.

## Description

In `_referia.yml`, `localpdf` and `editpdf` entries commonly use directories
relative to the config file, for example:

```yaml
localpdf:
- directory: ../files
  field: ApplicationPDF
- directory: ..
  liquid: 2023-11-29_PG-CS-admissions-wednesday-slides.pdf
```

`WebReviewer._resolve_local_file` (and the analogous `editpdf` path logic)
builds paths as:

```python
directory = os.path.expandvars(view.get("directory") or "")
return Path(directory, val).expanduser()
```

Relative `directory` values are therefore resolved against the **server
process current working directory** (wherever `referia serve` was launched),
not against `self._directory` (the config directory). The same mistake
affects `allowed_roots_for_document` when it expands relative roots.

Observed with MPhil admissions configs under root-server mode
(`referia serve --root ~/OneDrive`): the PDFs exist on disk under
`applications/2024-04-29_mphil-admissions/files/`, but the review panel shows
"PDF not found" for both the application PDF and the shared slides PDF.
`preliminary/` fails the same way — the bug is not inherit-specific.

Jupyter often works by accident because notebooks are started from the
config directory, so cwd and config dir coincide.

## Acceptance Criteria

- [ ] Relative `directory` / `sourcedirectory` / `storedirectory` values in
      `localpdf` and `editpdf` resolve against the config directory
      (`WebReviewer._directory`).
- [ ] Absolute paths and `$HOME` / env-expanded paths continue to work.
- [ ] `allowed_roots_for_document` uses the same base so serving and
      existence checks agree.
- [ ] Unit tests cover: relative `../files`, absolute path, `$HOME/...`,
      and a cwd that is *not* the config directory (regression for this bug).
- [ ] Root-server listing for
      `applications/2024-04-29_mphil-admissions/preliminary/` embeds
      `files/<ApplicationPDF>` when the file exists on disk.

## Implementation Notes

Join relative directories to `Path(self._directory)` before
`expanduser()` / `resolve()`:

```python
base = Path(self._directory)
directory = Path(os.path.expandvars(view.get("directory") or ""))
if not directory.is_absolute():
    directory = (base / directory).resolve()
else:
    directory = directory.expanduser().resolve()
return directory / val
```

Apply the same helper in `_resolve_editpdf_file` and
`allowed_roots_for_document`.

Do **not** change config files to absolute paths as the primary fix;
configs already encode the intended relative layout.

## Related

- CIP: 000B
- Feature: `2026-07-13_web-document-serving`
- Distinct from completed bug
  `2026-07-15_web-viewer-links-filesystem-relative` (viewer HTML href
  rewriting, not PDF filesystem resolution)
- Reproduced: 2026-10-06 against
  `applications/2024-04-29_mphil-admissions/interview-confirm/` and
  `…/preliminary/` under root-server mode

## Progress Updates

### 2026-10-06

Bug identified while loading MPhil interview-confirm in root-server mode.
PDFs present under `../files` relative to the cohort directory; web UI
reports missing because resolution used process cwd.
