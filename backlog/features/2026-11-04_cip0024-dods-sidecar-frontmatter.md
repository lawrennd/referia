---
id: "2026-11-04_cip0024-dods-sidecar-frontmatter"
title: "CIP-0024: Declare sidecar stores on dods-ai-dialogue consumers"
status: "In Progress"
priority: "High"
created: "2026-11-04"
last_updated: "2026-11-04"
category: "features"
related_cips: ["0024"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-11-04_cip0024-declared-sidecar-loads"
tags:
- backlog
- features
- cip0024
- dialogue
---

# Task: Declare sidecar stores on formats-study pages

> Linked CIP: 0024.

## Description

Add `grounds:`, `phrases:`, `turns:`, `chunks:`, `codebook:`, `roster:`
(as needed) to consumer stage markdown so Option B discovery and
`named_store_status` see the real Access deps.

## Acceptance Criteria

- [ ] `07_part_b`, `10_sequence`, `11_multiverse`, `08_questions`,
      `09_validate`, sidings, and partial fills on `05`/`06` declare
      the products their compute reads
- [ ] Store status Liquid mentions new roles where useful
- [ ] Pages still load under `referia serve`

## Related

- CIP: 0024

## Progress Updates

### 2026-11-04

Task created with CIP acceptance.
