---
id: "001A"
title: "Reviewers can produce a redacted PDF from an explicit term list"
status: "Proposed"
priority: "Medium"
created: "2026-11-08"
last_updated: "2026-11-08"
related_tenets:
  - "document-centric-management"
  - "progressive-augmentation"
  - "pragmatic-automation"
  - "user-oriented-convenience"
stakeholders:
  - "paper / thesis reviewers needing blind or anonymised PDFs"
  - "any review flow that must obscure configured identity strings on a PDF"
tags:
  - documents
  - pdf
  - redaction
---

# REQ-001A: Reviewers can produce a redacted PDF from an explicit term list

> Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Reviewers can take a PDF attached to the current review record and produce a **redacted copy** in which an **explicit list of terms** (names, emails, or other configured identity strings) is removed or obscured. The term list is under reviewer control: it may be edited before redaction runs. How the list was first populated — manual entry, document extract, or another upstream step — is out of scope for this requirement.

Failures must be visible. Zero matches when terms were non-empty must not look like success. Scanned / image-only PDFs must fail clearly unless a later OCR capability is explicitly in scope.

**Why this matters**: Document-centric review already copies, crops, and serves PDFs; anonymity and conflict handling need the same workflow for identity on the page. Progressive augmentation means referia composes infrastructure apply (lynguine term-based PDF redaction) rather than owning a parallel stack. The reviewer stays in control of what is redacted.

**Who benefits**: Reviewers preparing blind or anonymised reading copies; any flow that already has terms and only needs PDF apply + store/serve.

## Acceptance Criteria

- [ ] A reviewer can produce a redacted PDF for the current record from a **configured, editable term list** and a source PDF.
- [ ] Terms can be corrected or extended by the reviewer before redaction runs.
- [ ] When configured terms find no matches on the PDF, the failure/warning is visible (no silent success with an unchanged identity leak).
- [ ] Scanned / image-only PDFs fail clearly unless OCR is explicitly in scope.
- [ ] The redacted file is available as a review document (stored and servable in the usual document path).

## Notes (Optional)

**Not in this requirement (HOW / other WHAT):**

- Obtaining title/authors from a paper PDF is **not** an acceptance criterion here. That is document-structure extract (lynguine REQ-000D / CIP-0013) and a convenience path described in [CIP-0025](../cip/cip0025.md).
- Shared term contract and PDF apply mechanics: lynguine [REQ-0011](https://github.com/lawrennd/lynguine/blob/main/requirements/req0011_term-based-document-redaction.md) / [CIP-001A](https://github.com/lawrennd/lynguine/blob/main/cip/cip001A.md).

## References

- **Related Tenets**: document-centric-management, progressive-augmentation, pragmatic-automation, user-oriented-convenience
- **Related CIP**: [CIP-0025](../cip/cip0025.md) (one HOW: soft-fill terms from paper front matter, then apply)
- **Upstream**: lynguine REQ-0011 / CIP-001A (RedactTerms + `redact_pdf`)

## Progress Updates

### 2026-11-08
Created as paper author extract + redact; same day **split**: this requirement is redaction-only. Author acquisition moved to HOW (CIP-0025) / lynguine extract (REQ-000D). File renamed from `req001A_paper-author-name-redaction.md`.
