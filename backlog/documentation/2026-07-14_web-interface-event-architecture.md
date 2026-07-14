---
id: "2026-07-14_web-interface-event-architecture"
title: "Document and review web interface event/compute architecture"
status: "In Progress"
priority: "High"
created: "2026-07-14"
last_updated: "2026-07-14"
tags: ["web", "htmx", "architecture", "compute", "documentation"]
---

# Architecture: Web Interface Event and Compute Flow

This document describes how the `referia serve` web interface handles user
input, triggers computes, and persists data — and where the known gaps are.

---

## Overview

The web interface uses **HTMX** for live server-driven updates without a
JavaScript framework.  A single `WebReviewer` instance lives in
`app.state.reviewer` (shared across all requests to the same server process).
All routes operate on this shared in-memory object.

---

## Route Map

| Route | Trigger | What it does |
|---|---|---|
| `GET /` | Page load | Full page render |
| `GET /record?index=X` | Index selector change | Partial panel swap |
| `POST /field/{column}` | Field `change` event | Update one field, run computes, refresh affected widgets |
| `POST /save` | Save button click | Apply all form values, persist to disk |
| `POST /reload` | Reload button click | Re-read source files, re-render panel |
| `POST /populate/{field}` | PopulateButton click | Run on-demand compute (STUB — not yet wired) |

---

## The Two-Path Event Model

### Path 1 — Per-field `change` event (primary path)

Every editable widget is rendered with:

```html
hx-post="/field/Score"
hx-trigger="change"
hx-target="#status-bar"
hx-swap="innerHTML"
```

When the user changes a field value, the browser fires a `change` event and
HTMX immediately POSTs just that field's value to `/field/{column}`.

The server route:
1. Reads the raw value from the form body.
2. Coerces it to the correct Python type (`_coerce_form_value`).
3. Calls `reviewer.set_value(column, value)`.
4. `set_value` → `_value_updated` → updates timestamps + runs combinator
   computes (any `combinator` section in `_referia.yml`).
5. Calls `reviewer.affected_widgets(column)` and re-renders each affected
   widget as an HTMX **out-of-band (OOB) swap**.
6. Returns the status banner + OOB widget HTML in a single response.

**Result:** The in-memory state is updated, computes run, and affected widgets
refresh in the browser — all triggered by the field change, before Save.

### Path 2 — Save button (belt-and-braces + persistence)

The Save button is rendered with:

```html
hx-post="/save"
hx-target="#status-bar"
hx-swap="innerHTML"
hx-include="#review-form"
```

`hx-include="#review-form"` tells HTMX to capture **all** current form values
and include them in the POST body.

The server route:
1. Reads all field values from the form body.
2. Coerces each to the correct type.
3. Calls `reviewer.set_value(col, value)` for each field (which also runs
   `_value_updated` and therefore computes).
4. Calls `reviewer.save_flows()` to write to disk.
5. Returns only a "Saved" status banner — **no OOB widget refreshes**.

**Why `hx-include` is necessary:** HTML range inputs (`<input type="range">`)
fire `change` on **mouseup** (when you release the slider), not continuously
during drag.  If the user drags a slider and clicks Save in one motion, the
`change` event may not have completed before the Save POST fires.
`hx-include` ensures the current DOM value is captured in the Save POST
regardless.

---

## Known Architectural Issues

### Issue 1 — Save does not refresh computed fields in the UI

When computes run via the Save path (because the per-field `change` POST had
not yet fired), the `/save` response only returns a status banner.  Computed
fields (combinators, timestamps) are updated in memory and persisted to disk,
but the **browser widgets are not refreshed**.  The user will see stale values
until they reload or navigate away and back.

**Fix:** The `/save` route should also return OOB swaps for all fields that
`set_value` reported as changed.  This requires `set_value` to report which
fields it modified, or `affected_widgets` to be called for each modified field.

**Workaround:** Click Reload after Save to see computed fields update.

### Issue 2 — `PopulateButton` is not wired to the compute engine

`POST /populate/{field}` currently returns:
```
⚠ Populate not yet wired to compute engine
```

In the Jupyter interface, `PopulateButton` triggers a Python compute function
(e.g. an LLM call) defined in the `compute` section of `_referia.yml`.  The
web interface has no equivalent — compute functions registered with the
`Compute` registry are not accessible from the web routes.

**Fix needed:** The `/populate/{field}` route needs to look up and call the
compute function registered for `field`, update the in-memory state, and
return an OOB refresh of the populated widget.

This is **the primary missing feature** for parity with the Jupyter interface.

### Issue 3 — Slider `change` timing during fast interactions

The per-field `change` event for `<input type="range">` only fires on mouseup.
If the user:
1. Moves the slider
2. Immediately clicks Save (without releasing the slider first)

…the `change` event fires *after* the Save POST, potentially with a stale
value (or not at all, depending on browser behaviour).

The `hx-include` fix mitigates this for Save, but if any **dependent computes**
were supposed to run on the intermediate slider value (e.g. to show a live
preview), they won't run until the full Save cycle.

**Alternative approach:** Use `hx-trigger="input"` instead of `"change"` for
sliders to fire on every movement.  Downside: many more server round-trips and
potential race conditions.  A middle ground is `hx-trigger="change, mouseup
from:input[type=range]"` to catch both the standard change and the slider
release.

### Issue 4 — No protection against concurrent rapid edits

All routes share a single `WebReviewer` instance with no locking.  Uvicorn
(single worker, asyncio) processes requests sequentially at `await` points, and
`set_value` is synchronous, so in practice requests don't interleave mid-update.

However, if the user edits two fields in rapid succession, two concurrent HTTP
requests will be in-flight.  The second may overwrite the first's update
depending on response order.

**Likely not a practical problem** (human typing speed is far slower than
request processing), but worth noting for correctness.

---

## What Triggers Computes

| Action | `set_value` called? | `_value_updated` runs? | Computes run? | UI refreshed? |
|---|---|---|---|---|
| Edit any field (change event) | Yes | Yes | Yes | Yes (OOB swaps) |
| Click Save (via hx-include) | Yes | Yes | Yes | **No** (status only) |
| Click PopulateButton | **No** (stub) | No | No | No |
| Navigate to new record | No (reload) | No | No | Yes (full re-render) |

---

## Relationship to Jupyter Interface

In the Jupyter interface (`Reviewer` class via `referia.interact`):

- Widget `observe()` callbacks call `set_value` immediately on every change.
- `PopulateButton` callbacks trigger registered compute functions synchronously.
- `save_flows()` is called when the user clicks Save.

The web interface replicates the change→compute→display cycle via HTMX but
is missing the compute-engine integration for `PopulateButton` (Issue 2 above).

---

## Priority Actions

1. **Wire `/populate/{field}` to the compute engine** — needed for LLM
   population and other on-demand computes.  High priority for feature parity.

2. **Return OOB widget refreshes from `/save`** — so computed fields update in
   the browser without requiring a manual Reload.  Medium priority.

3. **Improve slider `change` trigger** — low priority; the `hx-include` fix
   is sufficient for persistence correctness.

---

## Progress Updates

### 2026-07-14
Architecture documented following debugging session.  Issues 1-4 identified.
`hx-include` fix (Issue 3 mitigation) already in place.  Issues 1 and 2 are
open items for future work.
