---
id: "2026-10-21_permanova-markdown-viewer"
title: "Review pane Markdown for PERMANOVA / PERMDISP and selected-document topic profile"
status: "Proposed"
priority: "Medium"
created: "2026-10-21"
last_updated: "2026-10-21"
category: "features"
related_cips: ["0016"]
owner: "lawrennd"
dependencies:
- "2026-10-21_document-emd-compute"
tags:
- backlog
- cip0016
- viewer
- markdown
- permanova
---

# Task: PERMANOVA Markdown viewer

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Surface `distance_tests_md` and a selected-document topic profile in the
`04_distance` review pane. Group field is a declared parameter (widget writing
an output/parameter field), not a Python default. Liquid over the `P` row for
the current `selected_doc`.

## Acceptance Criteria

- [ ] Review Markdown renders PERMANOVA / PERMDISP / axis-correlate summary
      from `distance_tests_md` (an output column)
- [ ] Selected-document profile lists topic shares for `selected_doc`
- [ ] Group column name is a config/widget field later steps can read
- [ ] Draft `04_distance/_referia.yml` review section names these fields

## Implementation Notes

Compute that fills `distance_tests_md` is `2026-10-21_document-emd-compute`.
This task is the viewer/review YAML plus any tiny Liquid helpers — no new
maths.

Proposed only: do not implement until CIP-0016 is Accepted.

## Related

- CIP: 0016
- Draft: OneDrive `applications/2026-10-21_dialogue-analysis/04_distance/`

## Progress Updates

### 2026-10-21

Task created as Proposed from CIP-0016.
