# Subject grain — local \(U_q\) Assess

Interactive review of a soft mixture of probabilistic PCA (MPPCA) over phrase
embeddings. You explore one local Bishop–Tipping plane at a time, propose
splitting a focus topic when the grain looks mixed, then confirm or undo.

## What this example does

1. Load a corpus of phrases and embeddings (`info/records.yml`).
2. Fit or restore soft topic responsibilities and local \(U_q\) figure specs
   (`info/scores.yml`).
3. In the viewer: change **Focus topic**, click phrases, **Propose split**,
   then **Confirm** or **Undo**.
4. In review: adjust EM controls (σ², EM accept) and optionally **Name focus
   topic** with a prompt you edit in the config.

Assess state is question-agnostic geometry (soft mass and planes). Naming is
optional labelling on top of that geometry.

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
| `responsibilities`, `uq_by_topic`, `uq_spec`, `topic_keys`, `topic_labels`, `pending_proposal`, `split_undo` | Catalogue / UI state written by split and naming actions |

The default topic-naming prompt (must keep `<<PHRASES>>`) is set on the
`label_prompt` field in `_referia.yml`.
