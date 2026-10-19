# Subject grain — local $U_q$ (Assess)

Referia hosting of the **interactive Assess** loop from multilogue notebook
[`03_cluster.ipynb`](https://github.com/mlatcl/multilogue/blob/main/notebooks/03_cluster.ipynb)
(Bishop–Tipping local plane / subject grain). Soft geometry comes from
`referia.assess.compute.mppca` (CIP-0017); click / responsibility-ink /
`figure_source` chrome is CIP-0011.

## Layout

```
subject_grain_uq/
├── README.md
├── _referia.yml          # viewer: focus + Plotly + Propose split; review: EM + label prompt
├── build_records.py      # fit MPPCA → records.yml + scores.yml
└── info/
    ├── records.yml       # phrases + embeddings (input; committed seed)
    └── scores.yml        # focus / R / planes / EM / prompt (output; gitignored)
```

`scores.yml` is **not** committed — recreate it with `build_records.py` (and
overwrite again via Save while reviewing).

## Run

From the referia repo root:

```bash
poetry install --with llm          # OpenAI embeddings + naming
# Put OPENAI_API_KEY in referia/.env (repo root) or ~/.env
poetry run python examples/subject_grain_uq/build_records.py   # writes info/scores.yml
poetry run referia serve --directory examples/subject_grain_uq
```

**`.env` location:** `referia/.env` (package root — same directory as
`pyproject.toml`) or `~/.env`. Both `build_records.py` and
`referia.util.llm` load these; do not put the key only under
`examples/subject_grain_uq/`.

Default bake loads **CIMT Bonn cycling** (German dialogue + survey), embeds
with OpenAI, PCA-reduces for the YAML store, then fits soft MPPCA at **k=1**
(Assess entry, matching multilogue 03). Offline / CI: `--synthetic` keeps the
planted English bank.

Open the printed URL (default `http://127.0.0.1:8000`).

## What to verify

1. **First view (k=1):** every phrase marker should be visible on the single
   local $U_q$ plane (mass ≈ 1 on `T0`). Topic list shows `T0 — Topic 0`
   until you name it.
2. **Propose split (viewer):** click **Propose split** — the figure shows the
   **parent ellipse** (combined original, solid) plus **two dashed child
   ellipses** in the parent $U_q$ plane; `topic_keys` grows to `T0`/`T1`;
   focus moves to the first child; status reports `k=1→2`. Pending.
3. **Focus topic (viewer, after Confirm):** change the Focus dropdown — the
   local $U_q$ **plane** swaps via `figure_source`
   (`uq_by_topic[focus_topic]`), not just marker ink.
4. **Confirm / Undo (viewer):** **Confirm split** seals the proposal (swaps
   to each child's own local plane, clears pending); **Undo split** restores
   catalogue geometry from `split_undo` and redraws at the *current* σ².
5. **EM parameters (review, collapsible):** open **EM parameters** — σ² mode,
   σ², EM accept / preview. These are *controls*: Propose reads them; Confirm
   / Undo never write them back (changing σ² then Undo keeps your σ²).
6. **LLM naming (review, collapsible):** open **LLM topic naming** — edit
   `label_prompt` (must keep `<<PHRASES>>`), choose a model (bake defaults to
   `gpt-4.1-mini` when `OPENAI_API_KEY` is present), click **Name focus
   topic**. Names are on-demand, not auto-loaded. `stub` is offline (exemplar
   heuristic). Writes `topic_labels` only; the liquid topic list refreshes
   after Save / page reload.
7. **Click → review:** click a marker; Selected phrase / topic update;
   Selected topic re-inks via `responsibility_ink`.
8. **Save:** write mutable Assess state into `info/scores.yml`.

## Notes

- Quote `"on":` under PlotlyFigure (YAML 1.1 maps bare `on:` to boolean `True`).
- Web path uses Plotly.js from the CDN (no Python `plotly` install required).
- Full split/merge `SubjectGrainShell` (undo, dendrogram, auto name-after-split)
  stays in the multilogue notebook; this demo ports focus swap, Propose /
  Confirm / Undo, EM controls, and on-demand LLM naming into referia.
