# Subject grain — local \(U_q\) Assess

Interactive review of a soft mixture of probabilistic PCA (MPPCA) over phrase
embeddings. You explore one local Bishop–Tipping plane at a time, propose
splitting a focus topic when the grain looks mixed, then confirm or undo.

## What this example does

1. Load a corpus of phrases and embeddings (`info/records.yml`).
2. Fit or restore soft topic responsibilities and local \(U_q\) figure specs
   (`info/scores.yml`).
3. In the viewer: change **Focus topic** (owns the local plane), click a
   phrase to pin it in review, **Propose split**, then **Confirm** or **Undo**.
4. In review: adjust EM controls (σ², EM accept) and the label model / prompt.
   With a non-`stub` model, **Propose split** names the new children in the
   same click. The k=1 seed is titled on open (and at bake when an API key
   is present). Use **Name topics** only to re-name.

Assess state is question-agnostic geometry (soft mass and planes). Naming is
labelling on top of that geometry (auto on Propose when the model is live).

## Layout

```
subject_grain_uq/
├── README.md
├── _referia.yml          # viewer + review wiring; default label_prompt lives here
├── build_records.py      # bake Access + k=1 Assess seed (temporary helper)
└── info/
    ├── records.yml       # phrases + embeddings (input; committed seed)
    └── scores.yml        # focus / R / planes / controls (output; gitignored)
```

Regenerate `scores.yml` before first serve:

```bash
poetry install --with llm
poetry run python examples/subject_grain_uq/build_records.py
# Offline: add --synthetic
poetry run referia serve --directory examples/subject_grain_uq
```

Put `OPENAI_API_KEY` in the referia package-root `.env` (or `~/.env`) only if
you want live embeddings / naming. The bake defaults `label_model` to `stub`
when no key is present.

## Controls vs catalogue

| Field | Role |
|-------|------|
| `sigma2`, `em_accept`, `em_preview`, `label_prompt`, `label_model` | Controls — Propose / Name read them; Confirm / Undo never rewrite them |
| `responsibilities`, `uq_by_topic`, `uq_spec`, `topic_keys`, `topic_labels`, `topic_parent`, `topic_tree`, `pending_proposal`, `split_undo` | Catalogue / UI state written by split and naming actions |

`topic_parent` is the living genealogy map (topic key → parent label), remapped on Propose and restored on Undo — the same role as multilogue’s `parent_of`, held as referia catalogue state rather than an append-only list. `topic_tree` is a derived Markdown view: a soft-association table (phrases with `R > τ`, plus soft mass `Σ R`) and the genealogy tree; rewritten whenever topology, labels, or responsibilities change.

The default topic-naming prompt (must keep `<<PHRASES>>`) is set on the
`label_prompt` field in `_referia.yml`.

**Seed naming on open.** A review `precompute` runs
`subject_grain_ensure_seed_names` when the row loads: if labels are still
provisional (`Topic 0`, …) and `label_model` is not `stub`, the LLM titles
them from cluster phrases before you start. Already-named labels are left
alone (no re-LLM). Bake does the same when `OPENAI_API_KEY` is set.

**Propose names children when `label_model` is not `stub`** (needs
`OPENAI_API_KEY`). Offline / `stub` keeps temporary
`«Parent» → (unnamed t)` placeholders. **Name topics (focus + provisional)**
re-titles on demand. After a soft split the parent topic is replaced by its
children — seed parents like `Topic 0` are cleared from `topic_parent` so the
UI does not keep showing a ghost `← Topic 0`.
