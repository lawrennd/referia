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
    ├── records.yml       # two rows with topic_scatter_spec (input / immutable)
    └── scores.yml        # selected_* / notes (output / mutable; Save updates)
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

- Review fields must live in **output** (`scores.yml`), not input — input columns are immutable.
- Quote `"on":` under PlotlyFigure (YAML 1.1 maps bare `on:` to boolean `True`).
- `size.mode: container` grows the viewer pane with the plot (width ×
  `aspect_ratio`, default `4/3`) as the splitter moves;
  `size.mode: figure` (default) keeps fixed `layout.height` / `width` from the figure JSON.
  Set `size.observe: false` to disable pane `ResizeObserver` updates.
- Web path uses Plotly.js from the CDN (no Python `plotly` install required).
- Jupyter (`Reviewer` + `display()`) needs `plotly` for `FigureWidget`; without it the viewer shows an install hint.
- A real soft-geometry workflow would replace `topic_scatter_spec` with compute / `multilogue.viz` output; referia only hosts chrome and field sync.
