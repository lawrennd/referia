---
author: "Neil D. Lawrence"
created: "2026-10-29"
id: "001E"
last_updated: "2026-10-29"
status: "In Progress"
compressed: false
related_requirements: ["0015", "0010"]
related_cips: ["0015", "0016", "001A", "001D"]
tags:
- cip
- compute
- dialogue
- formats
- jsd
- grounds
- validation
title: "Formats Part A compare, Part B grounds, and word-list floor as referia stages"
---

# CIP-001E: Formats Part A compare, Part B grounds, and word-list floor as referia stages

> **Note**: CIPs describe HOW to achieve requirements (WHAT).
> Use `related_requirements` to link to the requirements this CIP implements.

## Status

- [x] Proposed - Initial idea documented
- [ ] Accepted - Approved, ready to start work
- [x] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented
- [ ] Deferred - Postponed

Marked In Progress because the study configs and the stats/LLM compute land with this CIP. Pause before treating the paper numbers as a replay of Jess’s frozen k=40 run.

## Summary

Add four (plus two documentary) chained referia configs after `04_grain` so the formats study can produce the paper’s Part A tables and Part B grounds from named stores.

| Config | Jess notebook | Compute | LLM? |
|--------|---------------|---------|------|
| `05_distance` (already) | extra geometry | CIP-0016 EMD / MDS | no |
| `06_compare` | `03_part_a` | `run_format_share_compare` | no |
| `07_grounds` | `04_part_b` classify | `llm_classify_grounds` | yes, one call / unit |
| `08_questions` | `04_part_b` question types | `run_question_type_stress` | no |
| `09_validate` | `05_validation` word list | `run_wordlist_floor` | no (own-words deferred) |
| `10_sequence` | stories-follow-stories | not in this slice | — |
| `11_multiverse` | `06_multiverse` | not a referia; package replay | — |

Addresses [REQ-0015](../requirements/req0015_formats-part-a-b-in-referia.md). Complements [REQ-0010](../requirements/req0010_dialogue-pipeline-in-referia.md) (first deployment stopped at EMD).

## Motivation

`04_grain` yields five MPPCA topics on a 64-cell codebook. That is not Jess’s frozen k=40 / 11 lenses, so it cannot replace Table 1, but it *can* answer the same Part A question on this grain: do the two formats raise the same agenda? 05_distance answers a different question (EMD geometry). The draft’s CBC mix, JSD, and experience gap are not in 05.

Part B is one JSON call per unit over the unit’s points. That is the same populate-all shape as extract (CIP-001D). The stage must still exist; skip/flush is 001D’s job.

## Detailed Description

### 06_compare — one packed row

Input `records.parquet` + data `scores.yml` (join on `Name`), same as 05. Wrapper fills `cluster_ids` from `codebook.parquet` and `kinds` from `phrases.yml` when the pack has no `kinds` column. Phrase-level membership is `QR`. Document histograms use pack `doc_id`. Bootstrap resamples documents (D5). JSD is base 2 on the two format mean lens profiles (`multilogue.weight.jsd` contract, copied so referia does not import multilogue at runtime).

Output `info/part_a.yml`: `type_mix`, `lens_mix`, `jsd`, markdown fields.

### 07_grounds — one unit (`side_by_side`) plus Classify all

Input `chunks.yml`. Wrapper groups `phrases.yml` by `unit_id` into `points`. `llm_classify_grounds` renders `<<UNIT>>` / `<<POINTS>>`, calls the LLM, writes `grounds_payload` + a list of `{phrase_id, basis, ...}`. Explode to `info/grounds.yml`. Empty phrase lists are a no-op. Layout stays **`side_by_side`**: a 2013-row `inline_list` GET (set_index × N) pegs the single worker, the same failure as 02_embed. **Classify all** is `PopulateButton` `args.all: true`, which emits the populate-all chrome without building the listing (CIP-001D).

### 08_questions / 09_validate — one packed row

Regex on chatbot `context` (chunks) and on each point’s quote. No model. Own-words recode, hand-check sheets, and stories-follow-stories stay out of this slice: they need a sample loop, speaker labels, and CIP-001D.

### 11_multiverse

Viewer only. Canonical 1080-config run remains `dialogue_formats.Run(replay=True)`. Do not wrap 1080 populate-all POSTs.

### Not in the generic `template/`

Part B and question types are formats-specific. Draghi / L172 copies of 01–05 stay as they are.

## Implementation Plan

1. Compute modules `compare.py` and `grounds.py`; register façades that read sibling `info/` files the way CIP-0016 already loads `codebook.parquet`.
2. Study configs `06_compare` … `11_multiverse` under `dialogue-analysis/ai-dialogue-formats/`.
3. Tests for JSD, two-group tables, grounds JSON parse, word-list, question regex.
4. Own-words, sequence, multiverse compute — later slice.

## Backward Compatibility

New configs and new compute names. 01–05 unchanged. Pack may later grow a `kinds` column; 06 already falls back to `phrases.yml`.

## Testing Strategy

- `tests/test_compute_compare.py` — JSD identities; two-group lens JSD = 1 on orthogonal topics; CBC rows; chatbot-only question counts; word-list hit.
- `tests/test_compute_grounds.py` — aliases, empty no-op, JSON `n` mapping, missing point → `unclear`, context wrapper.

## Related Requirements

- [REQ-0015](../requirements/req0015_formats-part-a-b-in-referia.md)
- [REQ-0010](../requirements/req0010_dialogue-pipeline-in-referia.md)

## Implementation Status

- [x] `run_format_share_compare` / JSD
- [x] `llm_classify_grounds`
- [x] `run_question_type_stress`
- [x] `run_wordlist_floor`
- [x] Study `_referia.yml` 06–11
- [x] `07_grounds` `side_by_side` + Classify all (`args.all`, no 2013-row GET)
- [ ] Own-words recode
- [ ] Stories-follow-stories
- [ ] Multiverse as compute (explicitly out of slice)

## References

- `ai-dialogue-formats` `dialogue_formats/{compare,grounds,validate,stats}.py`
- `config/canonical/clusters_and_lenses.json`
- Study `GAP.md`
