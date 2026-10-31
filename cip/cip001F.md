---
author: "Neil D. Lawrence"
created: "2026-10-29"
id: "001F"
last_updated: "2026-10-30"
status: "In Progress"
compressed: false
related_requirements: ["0016"]
related_cips: ["0015", "001E"]
tags:
- cip
- compute
- dialogue
- validation
- extract
- sklearn
title: "Siding: bag-of-words reconstruction of discrete phrase codes"
---

# CIP-001F: Siding — bag-of-words reconstruction of discrete phrase codes

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

Marked In Progress because the user asked for the siding config, not only the design. Pause before treating a high CV score as human validation of the extract.

## Summary

Add optional sibling configs beside the 01–11 pipeline that ask: can a linear bag-of-words model recover a discrete code from the phrase text? Three labels share one CV: extract `kind`, Part B `basis` (joined from `grounds.yml`), and hard grain lens (`argmax QR`). Default estimator is tf-idf + logistic regression with 5-fold stratified CV, plus majority, shuffled-label, and document-grouped baselines. Naïve Bayes and linear SVM are the same question with a different linear family. Hard lens is a grain diagnostic, not a check of Name strings.

Part B's paper coding is **experience vs rest**, not seven-way `basis` from phrase unigrams. 82% of labelled points are `principle`; class-balanced 7-way logreg then loses to the majority baseline (accuracy 0.71 vs 0.82; balanced accuracy 0.30). That is a feature/question mismatch, not a reason to fit a non-linear classifier on the same phrase BoW. `siding_basis` defaults to `label_mode: experience` on `text_source: quote_and_phrase` (what the point itself contains). Seven-way and `phrase`-only remain diagnostics. Do not switch this siding to embeddings.

Addresses [REQ-0016](../requirements/req0016_extract-kind-reconstruction-siding.md).

## Motivation

06_compare reports CBC mix as if `kind` is a stable coding. 07 reports experience shares as if `basis` is a stable coding. 09_validate is a word-list on *quotes* for experience language, not a check of those labels. An LLM extract or grounds pass can be noisy, format-skewed, or collapsed to cue words. A cheap reconstructability check, off the main line, is the right place to see that before quoting percentages. Hard-lens reconstruction asks the same of this grain, not of Name strings.

## Detailed Description

### Siding, not a cascade

Sibling folders `siding_kind/`, `siding_basis/`, `siding_lens/` so the parent glob lists them after `11_multiverse` and they are not numbered stages. Each reads `info/phrases.yml` (basis joins `grounds.yml`; lens expands codebook `R` via `cluster_ids`). They write `kind_check.yml` / `basis_check.yml` / `lens_check.yml`. They do not inherit 02 or 07 (different job; CIP-001D populate-all must not walk this CV). sklearn is already a referia dependency (CIP-0019). `run_kind_reconstruction` takes `label_name` and `missing_hint` so the three façades share one CV.

### Estimators

| `model` | Vectoriser | Classifier | Why |
|---------|------------|------------|-----|
| `logreg` (default) | tf-idf, 1–2 grams | logistic regression, balanced | User's request; coefficients are readable |
| `nb` | counts | multinomial naïve Bayes | Often stronger on short phrases |
| `linearsvc` | tf-idf | linear SVM | Same linear family, different loss |

Do **not** predict kind from embeddings. That tests grain geometry, not extract consistency. Do **not** predict grounds experience from embeddings either in this siding — quote-plus-phrase BoW is the cheap inspectable check; unit context the LLM saw is `quote_and_unit`.

`siding_basis` knobs: `label_mode` `experience` (default) or `seven`; `text_source` `quote_and_phrase` (default), `quote`, `quote_and_unit`, or `phrase`.

### What "nothing unusual" means

| Pattern | Flag |
|---------|------|
| Balanced accuracy within 0.08 of 1 / n classes | `near_chance` — labels not recoverable from this text |
| Raw accuracy below majority | `below_majority` (info) — expected with class_weight=balanced on a dump class; read balanced accuracy |
| Accuracy ≥ 0.95 | `lexical_collapse` — extract may be keywords |
| Document-grouped acc 0.10 below phrase-stratified | `document_leakage` — conversation style, not kind lexicon |
| One kind F1 < 0.35 while another > 0.70 | `class_collapse` |
| Format OOF error gap ≥ 0.10 | `format_gap` |
| No warn-level flags | `consistent` |

Phrase text is not written to the output store. Out-of-fold errors are `phrase_id`s for lookup in 02_embed.

### Page load

Do **not** precompute the CV. 11k phrases × 5 folds on first GET would stall the panel the way 02_embed's `inline_list` did. Store status on load; a button runs the check; Save writes `kind_check.yml`.

## Implementation Plan

1. `referia/assess/compute/verify.py` — `run_kind_reconstruction` + `hard_lens_labels`; façades load sibling info files.
2. Study configs `siding_kind/`, `siding_basis/`, `siding_lens/` under `dialogue-analysis/ai-dialogue-formats/`.
3. Tests on a tiny separable lexicon, shuffled labels, `label_name` / `missing_hint`, and hard-lens argmax.
4. Not in `template/` in this slice (formats study first; Part B stays off the generic template).

## Backward Compatibility

New compute name and a new sibling config. 01–11 unchanged.

## Testing Strategy

- Separable cue-word phrases → accuracy well above shuffled labels.
- Shuffled labels → `near_chance` (or a weak-class flag).
- `verified_only` drops unverified rows.
- Too few phrases → explanatory markdown, no crash.
- `model: nb` runs and does not emit logreg coefficients.

## Related Requirements

- [REQ-0016](../requirements/req0016_extract-kind-reconstruction-siding.md)

## Implementation Status

- [x] `run_kind_reconstruction` (`label_name`, `missing_hint`)
- [x] `hard_lens_labels`
- [x] Study `siding_kind/_referia.yml`
- [x] Study `siding_basis/_referia.yml`
- [x] Study `siding_lens/_referia.yml`
- [x] Grounds default: `label_mode: experience` on quote-plus-phrase; `near_chance` uses balanced accuracy
- [x] Binary OvR n-grams map onto `classes_[1]`; verdict copy does not call majority chance
- [ ] Copy into `template/` (deferred; Part B not in generic template)

## References

- sklearn `LogisticRegression`, `MultinomialNB`, `LinearSVC`, `StratifiedKFold`, `StratifiedGroupKFold`
- Study `GAP.md`
