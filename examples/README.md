# Package examples

Learn referia from these directories. The primary surface is the web
reviewer:

```bash
uv sync --group dev   # once, from the referia package root
uv run referia serve --directory examples/<name>
# Open the printed URL (default http://127.0.0.1:8000)
```

For a multi-config host, use `uv run referia serve --root <path>`.

## Serveable demos

| Directory | Purpose |
|-----------|---------|
| `overview_inline_list/` | Catalog / `inline_list` with Today and Year siblings |
| `topic_scatter_click/` | Plotly click ↔ review field sync |
| `subject_grain_uq/` | Soft MPPCA subject grain (bake scores first — see its README) |
| `numeric_scoring/` | Offline `multiply` / `add` / `gte` scoring (no LLM) |
| `pdf_term_redaction/` | Soft-fill authors → `redactpdf` auto-prepare (CIP-0025) |

Each directory has its own README with layout and smoke checks. Sphinx
lists the same map in `docs/examples/index.rst`.

## LLM / thesis snippets (not serveable as-is)

These files illustrate declarative LLM compute and the Python API.
They are **not** drop-in `--directory` demos (no self-contained
`_referia.yml` + sample data tree). Copy patterns into a real review
directory, then serve that directory.

| File | Role |
|------|------|
| `llm_integration_example.yml` | YAML compute snippets (`llm_summarise`, …) |
| `llm_usage_example.py` | Optional programmatic LLM manager API |
| `thesis_llm_review_example.yml` | Thesis chapter review with `llm_pdf_review` PopulateButtons |
| `thesis_llm_review_example.py` | Optional programmatic thesis review sketch |
| `env_template.txt` | Copy to package-root `.env` for API keys |

```bash
uv sync --extra llm --group dev
cp examples/env_template.txt .env   # then edit keys
```

Guides: `docs/llm_integration.md`, `docs/llm_pdf_review.md`.
