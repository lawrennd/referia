# Overview `inline_list` example (CIP-0010 / CIP-001C)

Minimal root `_referia.yml` that discovers nested configs with lynguine
`yaml_directory` (`recursive` + `include_start_directory: false` +
`exclude: [today/**, year/**]`) and shows them with referia
`display.layout: inline_list`. Schedule lives in tall scores (`due`,
`event`, `notes`); sibling `today/` and `year/` inherit that catalog.

## Layout

```
overview_inline_list/
├── _referia.yml          # seasonal overview (not listed as a row)
├── today/_referia.yml    # Today view (excluded from discovery)
├── year/_referia.yml     # Year view (excluded from discovery)
├── spring/_referia.yml   # discovered
├── autumn/_referia.yml   # discovered (leaf due: is a seed, not the store)
└── info/                 # tall scores (overview-scores.yml)
```

## Run

From the referia package root:

```bash
poetry install   # once
poetry run referia serve --directory examples/overview_inline_list
# Open the printed URL (default http://127.0.0.1:8000)
```

This directory is the review root (single-config mode). For a multi-config
host that discovers several `_referia.yml` trees, use
`poetry run referia serve --root <path>` instead.

Mark rows complete / set status, then **Save**. Scores land in
`info/overview-scores.yml` keyed by `sourceDirectory`.

## Notes

- The page uses a **directory-listing** layout: filter bar, then one row per
  discovered config with a leading **Complete** checkbox, title, date, and
  description (plus compact status/notes under the row).
- Viewer Liquid still receives `rows` for optional intro chrome.
- Filter/sort chrome replaces the record selector under `inline_list`.
- Child YAML files are stubs (title/description/date only) for discovery.
