---
id: "document-centric-management"
title: "Document-Centric Review Management"
created: "2025-12-23"
last_updated: "2025-12-23"
version: "1.0"
tags:
- tenet
- documents
- pdf
- workflow
- assessment
---

# Document-Centric Review Management

## Tenet

**Description**: Referia is designed around managing and reviewing documents (PDFs, Word files, URLs, emails) alongside structured assessment data. The system provides document operations including copying and editing PDFs with specified page ranges, opening URLs in browsers, generating Word documents from review templates, creating emails with attachments, and packaging deliverables. Document references use templated paths (e.g., `{Name}_masters_thesis.pdf`) that resolve against review data at runtime. The reviewing interface enables side-by-side viewing of documents and assessment forms, supporting natural read-and-annotate workflows. Document generation produces summaries, feedback letters, and reports from review data using Liquid templates, completing the full review lifecycle from document input to assessment output.

**Quote**: *"Documents in, assessments out"*

**Examples**:
- `editpdf` field specifies PDFs to copy and edit with page range extraction
- Page ranges from data: `pages: {first: ColumnName1, last: ColumnName2}`
- `urls` field opens web pages for reviewers in browsers
- `documents` section generates Word files from Liquid templates
- Email generation with `Message` class and Outlook integration
- PDF path templating: `{Name}_thesis_%pdf_name%.pdf` resolves at runtime
- Zip file creation for packaging deliverables
- LLM PDF review extracts and analyzes document content
- Document viewing alongside assessment widgets in Jupyter

**Counter-examples**:
- Reviews disconnected from their source documents
- No way to view documents while assessing
- Manual copying and organizing of PDFs and documents
- Hardcoded file paths without data-driven templating
- No document generation from review results
- Separate tools required for document management

**Conflicts**:
- **vs Platform Independence**: Document operations (Outlook, Chrome) are OS-specific
- Resolution: Graceful degradation on non-macOS platforms; provide cross-platform alternatives where possible
- **vs Security**: Document access requires careful permission handling
- Resolution: Validate paths, prevent directory traversal, sandbox file operations

