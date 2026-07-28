# referia


![Tests](https://github.com/lawrennd/referia/actions/workflows/python-tests.yml/badge.svg)

[![codecov](https://codecov.io/gh/lawrennd/referia/branch/main/graph/badge.svg?token=YOUR_CODECOV_TOKEN)](https://codecov.io/gh/lawrennd/referia)


The referia library provides tools for assisting with assessment, originally written as an aide for 2021 REF Assessment. The library builds on functionality provided in the [`lynguine`](https://github.com/lawrennd/lynguine/) data oriented architecture library. The main difference between the two is that functionality that is general for the flow-based model the code follows sits in `lynguine`. The `referia` code provides convenience functionality for ease of creation of reviewing software.

## Installation

```bash
pip install referia
```

Or, when working from source:

```bash
poetry install
```

## Quick start

All review configuration lives in a YAML file, conventionally named `_referia.yml`, placed alongside your data files. Once that file exists you have two ways to run a review session.

### Web interface (recommended)

```bash
referia serve --directory path/to/review --config _referia.yml
```

Open the printed URL (default `http://127.0.0.1:8000`) in any browser. The interface shows a two-column layout: a viewer panel on the left (document content, instructions, templates) and a review form on the right. Navigating between records, editing fields, and saving are all live — no page reloads.

Options:

| Flag | Default | Description |
|---|---|---|
| `--config FILE` | `_referia.yml` | Config filename inside `--directory`. |
| `--directory DIR` | `.` (cwd) | Directory containing the config and data files. |
| `--host HOST` | `127.0.0.1` | Network interface to bind. |
| `--port PORT` | `8000` | TCP port to listen on. |

To serve every `_referia.yml` found under a root directory at once, use root-server mode:

```bash
referia serve --root ~/OneDrive/referia/
```

Each config is then reachable at its relative path (e.g. `http://127.0.0.1:8000/theses/examined/`).

### Jupyter notebook interface

The original notebook interface is still supported. Add a notebook to your review directory and instantiate a `Reviewer`:

```python
from referia import Reviewer
r = Reviewer("_referia.yml", ".")
r.display()
```

### Linting configs

```bash
referia check --root path/to/reviews
```

Scans all `_referia.yml` files under the root and reports YAML parse errors. Use `--format json` for machine-readable output.

## Configuration reference

All behaviour is controlled by `_referia.yml`. The top-level keys are:

### `input`

Source data for the items being assessed (Excel, CSV, etc.). Passed directly to the lynguine data layer.

### `viewer`

Content rendered in the left-hand panel of the web interface (or above the form in the notebook). Supports Liquid templates evaluated against the current record.

```yaml
viewer:
  - liquid: "## {{ Name }}: {{ Title }}"
  - display: "**Submitted:** {{ SubmissionDate }}"
```

### `review`

Widget specifications for the review form. Supports sliders, text areas, dropdowns, checkboxes, and more.

```yaml
review:
  - field: Score
    type: IntSlider
    args:
      min: 1
      max: 10
      step: 1
    description: "Overall score"
  - field: Comments
    type: Textarea
    description: "Reviewer comments"
```

### `compute`

Fields filled in automatically. Supports LLM calls, date/timestamp generation, and arbitrary Python functions evaluated against the current record.

### `output`

How annotation data is persisted (Excel, CSV, etc.).

### `editpdf`

PDFs to copy and open for annotation. Supports page-range extraction driven by data columns.

```yaml
editpdf:
  field: ThesisFilename
  sourcedirectory: ./submissions
  storedirectory: ./annotated
  pages:
    first: StartPage
    last: EndPage
```

### `urls`

URLs to open in a browser alongside the review form.

### `documents`

Word documents (or emails) generated from the review data using Liquid templates — useful for feedback letters and reports.

### `summary_documents`

Like `documents`, but generated across all records rather than per-record. Useful for summary reports across a full review round.

### `scored`

Specification for counting completed reviews (used to display progress).

### `series`

Annotation data with a sub-index (e.g. time series of assessments for the same item).

