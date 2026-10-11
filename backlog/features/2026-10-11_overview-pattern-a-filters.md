---
id: "2026-10-11_overview-pattern-a-filters"
title: "Overview Pattern A presentation + general filters bar"
status: "Abandoned"
priority: "High"
created: "2026-10-11"
last_updated: "2026-10-11"
category: "features"
related_cips: ["0010"]
owner: "Neil D. Lawrence"
dependencies:
- "2026-10-11_root-load-referia-yml"
tags:
- backlog
- features
- abandoned
- cip0010
---

# Task: Overview Pattern A presentation + filters

> **Abandoned** — superseded by tall-first same-page plan (no required `wide_flatten` / Pattern A for overviews).

## Description

Originally: wire overview via Pattern A + `flattenKeys` / wide names + filters. Design shifted: lynguine keeps **tall** discovery/scores; referia `display.layout: inline_list` lists them with `rows` + filter/sort.

## Acceptance Criteria

- [ ] ~~Pattern A / wide_flatten overview~~ — abandoned
- [ ] See replacement tasks below

## Related

- CIP: 0010
- Superseded by: `2026-10-11_inline-list-same-page`
- Also: lynguine `2026-10-11_directory-include-start-directory`

## Progress Updates

### 2026-10-11

Task created (Ready) from Accepted CIP-0010.

### 2026-10-11 (later)

Abandoned after tall-first design shift (checkpoint `37ed710`, then CIP amend). Replacement: `2026-10-11_inline-list-same-page`.
