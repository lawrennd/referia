# PDF term redaction (CIP-0025 Phase B)

Soft-fills `RedactTerms` from `extract_paper_frontmatter`, then builds a
redacted view under `pdfs/` on resolve (`redactpdf:` with `auto: true`).

## Setup

1. Put a sample PDF in `files/` and list it in `info/allocation.csv`.
2. From this directory (with referia + lynguine that include CIP-0025 / CIP-001A):

```bash
referia serve
```

Source PDFs under `files/` are never modified.
