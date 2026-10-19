# Topic scatter click (CIP-0011)

Minimal **interactive viewer** demo: a synthetic Plotly scatter under `viewer:`
shares fields with `review:` widgets. No multilogue / MPPCA compute — figure
JSON is pre-baked in `info/records.yml`.

## Layout

```
topic_scatter_click/
├── README.md
├── _referia.yml          # PlotlyFigure + Dropdown / Text bindings
└── info/
    ├── records.yml       # two rows with topic_scatter_spec
    └── scores.yml        # created on Save (gitignored locally if you prefer)
```

## Run

From the referia package environment:

```bash
referia serve --directory examples/topic_scatter_click
# or: referia-web examples/topic_scatter_click
```

Open the printed URL (default `http://127.0.0.1:8000`).

## What to verify

1. **Click → review:** click a marker; **Selected topic** and **Selected phrase** update.
2. **Review → figure:** change the topic dropdown; marker opacities follow
   `customdata.responsibilities` (`highlight.mode: responsibility_ink`).
3. **Index change:** switch to `second-view` in the record selector; both panes refresh.

## Notes

- Web path uses Plotly.js from the CDN (no Python `plotly` install required).
- Jupyter (`Reviewer` + `display()`) needs `plotly` for `FigureWidget`; without it the viewer shows an install hint.
- A real soft-geometry workflow would replace `topic_scatter_spec` with compute / `multilogue.viz` output; referia only hosts chrome and field sync.
