---
id: "001A"
title: "Reviewers can redact author names from academic paper PDFs using extracted front matter"
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
  - "panel and grant workflows that already soft-fill from PDF extract"
tags:
  - documents
  - pdf
  - redaction
  - extraction
  - academic-papers
---

# REQ-001A: Reviewers can redact author names from academic paper PDFs using extracted front matter

> Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

Reviewers working with typical academic-style paper PDFs can obtain structured title and author information from the document, then produce a redacted PDF in which author names (and, where configured, related identity cues on the first page) are removed or obscured — without manually retyping names or hand-editing every file.

Extraction quality must be good enough for common digital layouts that reviewers actually receive. Perfect coverage of every publisher template is not required for the requirement to be met, but failures must be visible so a human can correct names before redaction runs.

**Why this matters**: Document-centric review already copies, crops, and serves PDFs; anonymity and conflict handling need the same workflow for identity on the page. Automation should reduce mechanical work while keeping the reviewer in control of what is redacted.

**Who benefits**: Reviewers preparing blind or anonymised reading copies; workflows that already soft-fill review fields from PDF extract (same convenience pattern as panel applicant email).

## Acceptance Criteria

- [ ] A review flow can obtain structured **title** and **author list** from a typical digital academic PDF (text layer present).
- [ ] Extracted authors are available as review data (editable) before any redaction runs.
- [ ] A reviewer can produce a redacted PDF for the current record that removes or obscures the configured author names.
- [ ] When extraction is incomplete or wrong, the failure is visible in the review UI / logs; the reviewer can correct names and still redact.
- [ ] Scanned / image-only PDFs fail clearly (no silent empty redaction) unless a later OCR capability is explicitly in scope.

## Notes (Optional)

Sibling capability today: Cambridge Panel flows soft-fill candidate email via lynguine `extract_form_fields` (`form_fields` aspect). Paper front matter is the same *kind* of outcome — one structured record per PDF — for a different document family.

End-of-paper bibliographic reference lists (lynguine `references` / `pmlr_references.v1`) are out of scope for this requirement; this is first-page title/author identity for redaction.

## References

- **Related Tenets**: document-centric-management, progressive-augmentation, pragmatic-automation, user-oriented-convenience
- **Related CIP**: [CIP-0025](../cip/cip0025.md)
- **Upstream infrastructure**: lynguine [CIP-0013](https://github.com/lawrennd/lynguine/blob/main/cip/cip0013.md) / [REQ-000D](https://github.com/lawrennd/lynguine/blob/main/requirements/req000D_document-structure-extraction.md)

## Progress Updates

### 2026-11-08
Requirement created with CIP-0025 (Proposed). Phase 1 focuses on title/author extraction parity with panel `extract_form_fields`.
