---
id: "0011"
title: "Reviewers can see named cache and store status in the review interface"
status: "Proposed"
priority: "High"
created: "2026-10-21"
last_updated: "2026-10-21"
related_tenets:
- user-oriented-convenience
- explicit-implicit-separation
- pragmatic-automation
stakeholders:
- Review authors
- Dialogue / public-engagement analysts
- Reviewers
tags:
- requirement
- cache
- viewer
- review
- stores
- yaml
---

# REQ-0011: Reviewers can see named cache and store status in the review interface

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

When a `_referia.yml` names a cache (or any durable store), the person serving that config can tell **that the cache is in use**, **when it was last written**, and **what it holds at a summary level** (path, size, compression, row count, column names) without opening the file in an editor or dumping payloads into the review pane.

Analysis cache (the named YAML/JSON store) is distinct from an LLM client diskcache used for API cost. Both, if present, must be labelled so a reviewer does not treat cost-cache hits as the analysis source of truth.

**Why this matters**: *User-oriented convenience* — large extract/embed runs look like “nothing happened” if cache already has values. *Explicit–implicit separation* — cache is a declared store, not a hidden checkpoint directory; the UI should show that store. *Pragmatic automation* — skip-if-present compute is fine only when the human can see what is being skipped.

**Who benefits**: Analysts running chained dialogue configs; review authors deciding whether to delete a cache and re-run; anyone who would otherwise discover a stale cache only by reading YAML on disk.

## Acceptance Criteria

- [ ] Serving a config that declares `cache:` shows that the cache store is loaded (or absent), its path, last-write time, and on-disk size
- [ ] The same summary can include whether the file is compressed and the logical type (`yaml`)
- [ ] The reviewer can see what the cache contains at catalogue level (index name, row count, column names) without rendering full payloads or embedding vectors
- [ ] LLM client diskcache, if present, is labelled as API-cost only and is not presented as the analysis cache
- [ ] A PopulateButton / compute that would skip because the target field already has a value is distinguishable from a first run (the existing artefact’s date is visible)

## Notes

File facts (path, mtime, size, codec) are an Access outcome (lynguine REQ-000E / CIP-0015 `store_stat`). This requirement is the **review-facing** display of those facts plus row/column catalogue of the loaded store.

Does not require a new layout region: existing `viewer:` / `review:` Liquid or a small typed widget is enough (referia CIP-0011 contract can host a non-interactive status entry).

## References

- Tenet: [user-oriented-convenience](../tenets/referia/user-oriented-convenience.md)
- Tenet: [explicit-implicit-separation](../tenets/referia/explicit-implicit-separation.md)
- Tenet: [pragmatic-automation](../tenets/referia/pragmatic-automation.md)
- Related: [REQ-0010](./req0010_dialogue-pipeline-in-referia.md), [REQ-000F](./req000F_interactive-viewer-components.md)
- Lynguine: [REQ-000E](https://github.com/lawrennd/lynguine/blob/main/requirements/req000E_compressed-yaml-stores.md)

## Progress Updates

### 2026-10-21

Requirement created (Proposed) from dialogue-pipeline cache size and staleness concerns. Paired with CIP-0017.
