# Numeric scoring (CIP-0026)

Offline scoring demo for YAML numeric compute primitives (`multiply`,
`add`, `gte`). No LLM. These helpers are **referia assessment compute**
pending vongole (lynguine CIP-0007).

## Layout

```
numeric_scoring/
├── README.md
├── _referia.yml          # viewer + PopulateButton compute chain
└── info/
    ├── records.yml       # quality / impact / feasibility / weight (input)
    └── scores.yml        # weighted_* / total / passes / notes (output)
```

## Run

From the referia package root:

```bash
poetry install   # once
poetry run referia serve --directory examples/numeric_scoring
# Open the printed URL (default http://127.0.0.1:8000)
```

## What to verify

1. Open **alice** — raw scores in the viewer; empty derived fields in review.
2. Click **Compute scores** — expect `quality_weighted=8`, `impact_weighted=7`,
   `feasibility_weighted=6`, `total=21`, **Passes** checked (`21 ≥ 20`).
3. Switch to **cara** — Compute → `total=10`, **Passes** unchecked.
4. **bob** (weight `1.2`) — Compute → weighted sum `16.8`, fails the threshold.
5. Edit **Notes**, **Save**, reload the page — totals and notes persist.

## Notes

- Input columns are immutable; derived fields live in `scores.yml`.
- The PopulateButton runs a short chain: three `multiply`s, two `add`s, one `gte`.
- Each step uses `refresh: true` so a Checkbox-default `passes: false` does not
  skip the `gte` rewrite (lynguine treats `False` as already filled).
- Registry docstrings mark these ops as interim until vongole.
