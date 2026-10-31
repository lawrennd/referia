---
author: "Neil D. Lawrence"
created: "2026-10-29"
id: "001E"
last_updated: "2026-10-30"
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
| `01_turns` | speaker turns (Access) | `run_rebuild_speaker_turns` (Jess Labels → `turns.yml`) | no |
| `10_sequence` | stories-follow-stories | `run_stories_follow_stories` (`turns.yml` + 07 codes) | no |
| `11_multiverse` | `06_multiverse` | `run_analysis_multiverse` (main-run 07 codes; not 1080 LLM jobs) | no |

Addresses [REQ-0015](../requirements/req0015_formats-part-a-b-in-referia.md). Complements [REQ-0010](../requirements/req0010_dialogue-pipeline-in-referia.md) (first deployment stopped at EMD).

## Motivation

`04_grain` yields five MPPCA topics on a 64-cell codebook. That is not Jess’s frozen k=40 / 11 lenses, so it cannot replace Table 1, but it *can* answer the same Part A question on this grain: do the two formats raise the same agenda? 05_distance answers a different question (EMD geometry). The draft’s CBC mix, JSD, and experience gap are not in 05.

Part B is one JSON call per unit over the unit’s points. That is the same populate-all shape as extract (CIP-001D). The stage must still exist; skip/flush is 001D’s job.

## Detailed Description

### 06_compare — one packed row

Input `records.parquet` + data `scores.yml` (join on `Name`), same as 05. Wrapper fills `cluster_ids` from `codebook.parquet` and `kinds` from `phrases.yml` when the pack has no `kinds` column. Phrase-level membership is `QR`. Document histograms use pack `doc_id`. Bootstrap resamples documents (D5). JSD is base 2 on the two format mean lens profiles (`multilogue.weight.jsd` contract, copied so referia does not import multilogue at runtime).

Output `info/part_a.yml`: `type_mix`, `lens_mix`, `jsd`, markdown fields.

### 07_grounds — one unit plus Classify all

Input `chunks.yml` (`unit_id`). **`data:`** is a parquet projection of 02's unit-grained extract nest (`_extract_phrases.parquet`: `unit_id`, `extraction_phrases`). Same index. Do not join `_extract_cache.yml.gz` on GET — that file still holds `extraction_payload` and PyYAML `safe_load` is ~11s. Classify `row_args` maps `extraction_phrases` → `points`. Compute must not open exploded `phrases.yml` (phrase grain, CIP-0015). `llm_classify_grounds` renders `<<UNIT>>` / `<<POINTS>>`, calls the LLM, writes `grounds_payload` + a list of `{phrase_id, basis, ...}`. Explode to `info/grounds.yml`. Empty phrase lists are a no-op. Listing is windowed `inline_list` (CIP-0020); **Classify all** is rolling populate-all (CIP-0021). `inline_list` Liquid injects `rows` only when the template uses it — otherwise GET walks 2013 nested phrase lists twice (~40s) even with a cached reviewer.

### 08_questions / 09_validate — one packed row

Regex on chatbot `context` (chunks) and on each point’s quote. No model. Own-words recode and hand-check sheets wait on a later coding pass; 09 is the word-list floor only.

### 01_turns — Access speaker-turn grain

Parallel to `01_chunk`. Chunks stay ~150-word extract units. This stage rebuilds labelled workshop **speaker turns** with Jess `Labels` (case-insensitive `Speaker N` / `S2` / facilitator names, tab or colon, mid-paragraph split) into `info/turns.yml`. Viewer is counts only. Does not rerun 02–07.

### 10_sequence

One corpus row. Load `turns.yml` from `01_turns`, filter `labelled_round` (spring), place 07 grounds by quote substring, look-backs L ∈ {1,2,3,5}, within-transcript shuffle. Do not rebuild DOCX here. Output is counts and gaps — no quote text. Own-words is a later column. Within-topic is blank until points carry a VQ/grain id. Waits on `01_turns` Save and spring 07 Save.

### 11_multiverse

One corpus row. Experience-gap product over definition × weighting × exclusion × threshold × round on **main-run 07 codes**. That is the methodology of the 1080-config table with one coding, not 1080 populate-all LLM jobs. Own-words coding variants wait on recode. k=25/60 is a refit of 03 → 04 → 06.

### Not in the generic `template/`

Part B and question types are formats-specific. Draghi / L172 copies of 01–05 stay as they are.

## Implementation Plan

1. Compute modules `compare.py` and `grounds.py`. 07 takes `points` from the Access join (`extraction_phrases`). 06 still fills `cluster_ids` / `kinds` from sibling `info/` when the pack has no those columns (CIP-0016 pattern).
2. Study configs `06_compare` … `11_multiverse` under `dialogue-analysis/ai-dialogue-formats/`.
3. Tests for JSD, two-group tables, grounds JSON parse, word-list, question regex.
4. Sequence and analysis-choice product on main-run 07 codes. Own-words recode remains a later coding pass.

## Backward Compatibility

New configs and new compute names. 01–05 unchanged. Pack may later grow a `kinds` column; 06 already falls back to `phrases.yml`.

## Testing Strategy

- `tests/test_compute_compare.py` — JSD identities; two-group lens JSD = 1 on orthogonal topics; CBC rows; chatbot-only question counts; word-list hit.
- `tests/test_compute_sequence.py` — labelled turns; quote placement; look-back gap vs shuffle; no quote text in markdown.
- `tests/test_compute_multiverse.py` — workshop-higher experience product; waits on 07.
- `tests/test_compute_grounds.py` — aliases, empty no-op, JSON `n` mapping, missing point → `unclear`, context wrapper, façade does not open `phrases.yml`.

## Related Requirements

- [REQ-0015](../requirements/req0015_formats-part-a-b-in-referia.md)
- [REQ-0010](../requirements/req0010_dialogue-pipeline-in-referia.md)

## Implementation Status

- [x] `run_format_share_compare` / JSD
- [x] `llm_classify_grounds`
- [x] `run_question_type_stress`
- [x] `run_wordlist_floor`
- [x] Study `_referia.yml` 06–11
- [x] `07_grounds` windowed `inline_list` + Classify all (CIP-0020/0021)
- [x] `07_grounds` joins 02 extract phrases parquet as `data:` (`extraction_phrases` → `points`)
- [x] `inline_list` Liquid skips `get_rows()` unless the template uses `rows`
- [x] Per-row Classify greys after fill unless Refresh classification; Cache **Refresh all** uses `skip_filled: false`
- [x] Classify greys and populate-all passes over units with 0 points (`skip_empty: extraction_phrases`)
- [x] Speaker-turn Access grain (`01_turns` `run_rebuild_speaker_turns`; Jess Labels)
- [x] Stories-follow-stories (`run_stories_follow_stories` on `turns.yml` + main-run 07 codes)
- [x] Analysis-choice product (`run_analysis_multiverse`; not 1080 LLM jobs)
- [ ] Own-words recode (explicit wait; not a listing stub)

## References

- `ai-dialogue-formats` `dialogue_formats/{compare,grounds,validate,stats}.py`
- `config/canonical/clusters_and_lenses.json`
- Study `GAP.md`
