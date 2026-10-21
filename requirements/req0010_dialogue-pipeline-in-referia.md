---
id: "0010"
title: "Dialogue analysis runs from chained referia configs with stateless compute"
status: "Proposed"
priority: "High"
created: "2026-10-21"
last_updated: "2026-10-21"
related_tenets:
- document-centric-management
- pragmatic-automation
- user-oriented-convenience
- explicit-implicit-separation
- progressive-augmentation
- template-driven-composition
stakeholders:
- Review authors
- Dialogue / public-engagement analysts
- Maintainers
tags:
- requirement
- dialogue
- documents
- embeddings
- clustering
- emd
- compute
- dataflow
---

# REQ-0010: Dialogue analysis runs from chained referia configs with stateless compute

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

A reviewer can run the public-dialogue analysis path — local PDF or DOCX files to paragraph or dialogue units, LLM phrase extraction, embeddings, interactive subject grain, then document-level Earth Mover's Distance with tests and visualisations — entirely from chained `_referia.yml` configs. They do not need the pub-dialogue, ai-dialogue-formats, or multilogue notebooks as the runtime.

Compute is stateless. Every intermediate is a column in a store the config already names: input, cache, constants, parameters, or output. Sidecar checkpoint directories, process-global result dicts, and “if the notebook was already run, skip” are not how analysis state is kept.

The first deployment covers eleven steps grouped into four configs (chunk, extract/embed, grain, distance). Later analyses (lenses, temporal tests, validation, multiverse) may follow as further configs; they are not required for this outcome.

**Why this matters**: *Document-centric management* keeps documents in and assessments (topics, distances) out. *Pragmatic automation* uses LLM extract and embed only where they help. *User-oriented convenience* lets an analyst serve each config without knowing lynguine internals. *Explicit–implicit separation* keeps review convenience in referia stores, not hidden files. *Progressive augmentation* extends lynguine Access rather than forking segmenters. *Template-driven composition* reuses one grain loop and one distance viewer across corpora.

**Who benefits**: Analysts reconstructing pub-dialogue / formats-style studies in referia; review authors who want document → topic geometry without a parallel Python pipeline; maintainers who keep one compute registry.

## Acceptance Criteria

- [ ] An analyst can run the eleven deployment steps from four chained `_referia.yml` configs sharing named stores under one `info/` directory
- [ ] Local PDF and DOCX files (catalogued in config) become unit rows without a study-specific Access package
- [ ] Phrase extraction and embeddings are invoked as named compute from config; results are columns on declared cache or output stores
- [ ] Interactive subject grain (propose / confirm / undo / name) consumes a declared corpus-row store and writes catalogue state to output
- [ ] Document-level topic histograms, EMD, MDS, and permutation tests are output columns; visualisations bind to those columns
- [ ] Compute functions are field-in / field-out: they do not own undeclared files, and a later config can load earlier artefacts without an in-memory object from the previous process
- [ ] Constants (prompts, models, `min_chunk_words`, `min_mass`, seeds) and analyst parameters (σ², EM knobs, group field) live in `_referia.yml` or output fields, not in Python defaults that later steps cannot see
- [ ] Deleting a cache store and re-running the declared PopulateButton / compute recreates that cache; output of a later config is not the only copy of an earlier artefact unless the config says so
- [ ] An LLM client diskcache for API cost, if present, is not the analysis source of truth

## Notes

The studies embed **extracted phrases**, not raw paragraphs. That grain is part of the outcome: the extract step is not optional in the first deployment.

Deferred later analyses (chunk quality flags, merge, framing lenses, lens σ²-by-EMD, cross-cutting coverage, temporal / AI-distinctiveness, Part B grounds, validation sheets, multiverse) are out of scope for this requirement’s first outcome.

Implements via referia CIP-0015 (extract, embed, seed fit) and CIP-0016 (row-local distance after pack; Plotly stays referia), and lynguine CIP-0014 (explode, pack, catalog; extending CIP-0013). Complements REQ-000F (interactive viewer) and REQ-0004 (declarative LLM compute).

## References

- Tenet: [document-centric-management](../tenets/referia/document-centric-management.md)
- Tenet: [pragmatic-automation](../tenets/referia/pragmatic-automation.md)
- Tenet: [user-oriented-convenience](../tenets/referia/user-oriented-convenience.md)
- Tenet: [explicit-implicit-separation](../tenets/referia/explicit-implicit-separation.md)
- Tenet: [progressive-augmentation](../tenets/referia/progressive-augmentation.md)
- Tenet: [template-driven-composition](../tenets/referia/template-driven-composition.md)
- CIP: [CIP-0015](../cip/cip0015.md), [CIP-0016](../cip/cip0016.md)
- Related: [REQ-0004](./req0004_declarative-llm-compute.md), [REQ-000F](./req000F_interactive-viewer-components.md), [CIP-0011](../cip/cip0011.md), [CIP-0012](../cip/cip0012.md)
- Lynguine: [CIP-0013](https://github.com/lawrennd/lynguine/blob/main/cip/cip0013.md), [CIP-0014](https://github.com/lawrennd/lynguine/blob/main/cip/cip0014.md)

## Progress Updates

### 2026-10-21

Requirement created (Proposed) from the dialogue-pipeline reconstruction plan. Paired with referia CIP-0015 / CIP-0016 and lynguine CIP-0014.

### 2026-10-21 (amendment)

Pack is Access IO (lynguine CIP-0014), not referia compute. CIP-0015 is extract / embed / seed only. CIP-0016 is row-local on the packed corpus row.
