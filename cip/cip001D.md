---
author: "Neil D. Lawrence"
created: "2026-10-29"
id: "001D"
last_updated: "2026-10-29"
status: "Proposed"
compressed: false
related_requirements: ["0010", "0008", "0009", "000E", "0013"]
related_cips: ["0010", "0015", "0017", "000B", "000C", "001B", "0020", "0021"]
tags:
- cip
- web
- populate
- cache
- htmx
- llm
- inline_list
title: "Populate-all as a resumable store write, not a long-lived page request"
---

# CIP-001D: Populate-all as a resumable store write, not a long-lived page request

> **Note**: CIPs describe HOW to achieve requirements (WHAT).
> Use `related_requirements` to link to the requirements this CIP implements.

## Status

- [x] Proposed - Initial idea documented
- [ ] Accepted - Approved, ready to start work
- [ ] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

## Summary

`POST …/populate-all/{field}` must treat a batch PopulateButton (Extract all, Embed all, Segment all) as a **resumable write into the named cache store**, with an HTTP lifetime the browser can survive.

Today it is one in-process loop over `working_indices()`, results held only in the `WebReviewer` RAM, then a full `review_panel.html` rebuild — including, under `display.layout: inline_list`, a widget strip for every row. A thousand-row LLM extract therefore lasts an hour, the browser drops the socket, HTMX shows “Request failed,” and Save never runs. The named cache file is empty. The uvicorn worker stays blocked on the API.

This CIP is the populate-all contract. It does not introduce a job queue. It does not change what CIP-0010 means by `inline_list`. It does not replace CIP-001B (kernel split); a killable kernel still needs this write/resume protocol or an hour of work dies with the process.

Addresses [REQ-0010](../requirements/req0010_dialogue-pipeline-in-referia.md) (extract/embed as columns on declared stores, not RAM), [REQ-0008](../requirements/req0008_web-review-without-jupyter.md), [REQ-0009](../requirements/req0009_multi-config-web-hosting.md) (one populate must not freeze the root server’s only worker for an hour), [REQ-000E](../requirements/req000E_named-layout-compositions.md) (layout is composition, not a licence to return 2013 forms as one HTMX swap), and [REQ-0013](../requirements/req0013_restartable-review-runtime.md) insofar as disconnect and restart must not imply lost compute.

## Motivation

On 2026-10-29 a dialogue `02_embed` review (`inline_list` over 2013 `unit_id` rows) loaded, then **Extract all** ran for about an hour and the browser showed an error.

What actually happened:

1. `populate-all/_extract` is a single POST. Uvicorn logs it only when it finishes. That line never appeared.
2. The browser connection to port 8003 closed. HTMX `htmx:sendError` / failed XHR paints “Request failed.” / “Request failed. See server log.” There was no extract traceback.
3. The worker was still in `SSL_read` on `api.openai.com`. Process RSS ~444 MB (phrases in RAM). CPU mostly idle, waiting on the network.
4. `_extract_cache.yml.gz` and `phrases.yml` were absent. CIP-0015 puts payload and phrase text on the **named cache**; CIP-0017 displays that store. Neither file is written until **Save**. Extract all never reaches Save.
5. After the loop, `_run_populate_all_and_respond` rebuilds the panel via `_panel_response_context`. Under `inline_list` that walks every working index, calls `_current_data` (~59 widget fields per row, including extract-prompt textareas), and renders a form per row. Timed locally: ~4 s to construct `WebReviewer`, ~6 s for 50 rows, **~4 minutes** estimated for 2013 rows, **before** HTML size. The response cannot stream. A closed client never sees it.

`01_chunk` Segment all on the same corpus returned 200 because local segment is fast enough that the request finished while the tab was still open, then Save wrote `chunks.yml`. Extract all is API-bound, so the same shape of request crosses every browser, proxy, and human patience limit.

The failure is therefore not “the LLM errored after an hour.” It is three stacked mistakes:

| Layer | Mistake |
|-------|---------|
| Layout | `inline_list` used as a 2013-row extract workbench. CIP-0010 defines that composition for **discovery catalogs** (mark-in-place on a short list of configs), not per-unit Extract/Embed chrome. |
| Persist | Populate writes the in-memory frame only. The named cache is not a checkpoint until Save. Client disconnect ⇒ hour of paid calls gone if the process dies. |
| HTTP | One request owns the whole working set **and** must return the whole page. Single uvicorn worker: the rest of the CIP-000C root is frozen. |

REQ-0010 already forbids sidecar checkpoint directories and “if the notebook was already run, skip.” The named cache **is** the checkpoint. Populate-all does not use it that way.

## Detailed Description

### Current code path

```
POST /{config}/populate-all/_extract
  _run_populate_all_and_respond
    for idx in working_indices():
        set_index(idx)
        run_populate(compute_spec)   # RAM only
    TemplateResponse review_panel.html   # full listing if inline_list
```

Populate-all does not skip rows whose target field is already filled. A retry after a partial run re-calls the model unless `refresh: false` and the compute itself no-ops — the route does not consult field presence.

`render_populate_all_button` posts with `hx-target="#review-panel"`. There is no `hx-timeout`. `base.html` labels the wait “Updating all…” and, on XHR failure, “Request failed. See server log.”

### Target contract

Populate-all is a **store writer** that happens to be triggered from the web:

1. **Resume.** Before calling compute on a row, skip if the PopulateButton target (and any listed `compute.field` outputs) are already present, unless the spec has `refresh: true` *and* the user asked for Refresh cache. Extract all on a half-written cache continues from the first empty row. Refresh cache is the explicit redo.
2. **Flush the named cache.** After each successful row, or every *N* rows with *N* small (default 1 for LLM, larger for local segment), write the config’s `cache:` store the same way Save writes cache columns — not output explode, not pack. CIP-0015’s `omit_nested_keys` still applies (no embeddings in YAML). LLMManager diskcache remains API-cost only (CIP-0017).
3. **Short HTTP.** The browser must not hold one POST for the corpus.
   - **Minimum (this CIP):** the server may keep looping after client disconnect *because the cache is already on disk*. Reload then shows CIP-0017 status and filled rows. The in-flight request still blocks the worker (CIP-001B’s problem).
   - **Rolling interaction:** batch size, HTMX re-POST, progress bar, and pause are [CIP-0021](./cip0021.md). This CIP does not specify that UI.
4. **Do not rebuild the listing as the success body.** Populate-all swaps `#status-bar` (and, under `side_by_side`, the current row’s widgets if they changed). It does not call `_panel_response_context`’s full `inline_list` walk. A later Reload or filter POST refreshes the list if the author needs it.

### Layout (config, not a new named composition)

REQ-000E / CIP-0010 already distinguish:

| Layout | Intent |
|--------|--------|
| `inline_list` | Discovery overview: identity + a thin mark-in-place strip |
| `side_by_side` | Document / unit review: viewer + form, index selector |

Dialogue `01_chunk` / `02_embed` with Extract, Embed, parameter textareas, and `detail_field: extraction_phrases` are **unit review**. They belong on `side_by_side`. Catalog `_referia.yml` files that list studies stay `inline_list`.

This CIP does **not** add a third layout. It does **not** forbid populate-all on `inline_list` (Segment all on a 20-row catalog is fine). It forbids using the listing renderer as the populate-all **response**, which is what made 2013 extract forms unreturnable.

Application YAML (template, draghi, l172, ai-dialogue-formats `02_embed`) should drop `display.layout: inline_list` on extract/embed stages when this CIP is accepted. That is config, not package, but the example and template must not teach the anti-pattern.

### Progress and failure

- Per-row compute exceptions stay logged (`_log_route_error`). They increment `n_fail` and **do not** abort the batch (today’s loop already continues).
- If a batch has `n_ok == 0` and `n_fail > 0`, return the existing generic “Populate all failed. See server log.” plus counts, still 200 HTML for HTMX, not a 503 that looks like WebReviewer load failure.
- Status text is a fixed catalog plus integers (`Extracted 1840/2013 (12 failed, 0 skipped).`). No paths, no phrase text, no `str(exc)` (CIP-000E).

### Relation to CIP-001B

CIP-001B splits HTTP process from a killable review kernel so a hung populate can be interrupted. That is necessary and not sufficient:

- Without cache flush, killing the kernel discards the hour.
- Without short HTTP or continue-after-flush, the browser still paints “Request failed” while the kernel works.
- Without skipping filled rows, restart re-bills the API.

Ship this contract first if 001B is not ready. 001B then restarts a kernel that reloads cache.

### Alternatives rejected

| Alternative | Why not |
|-------------|---------|
| Job queue (Celery, RQ, a `jobs/` YAML dialect) | Second runtime and a new store. Named cache already exists. |
| Sidecar `checkpoints/*.jsonl` | REQ-0010 / CIP-0015 forbid undeclared checkpoint directories. |
| SSE / streaming the listing | Still one long worker task. Progress + pause are rolling POSTs in [CIP-0021](./cip0021.md). |
| Raise gunicorn workers | Masks freeze of *a* worker; does not persist; duplicate `WebReviewer` state. |
| `hx-timeout` only | The browser would fail faster; the worker would still run and still not flush. |
| New layout name for “paged extract” | `side_by_side` already is unit review. Do not expand REQ-000E’s set. |

### Non-goals

- Auto-Save of `output:` explode (`phrases.yml`) or `pack:` parquet on every row. Those are still the Save button (CIP-0015: Save after extract must not abort pack). Cache flush is the durability for extract/embed intermediates.
- Changing PopulateButton compute functions (`llm_extract_phrases`, …). Stateless field-in / field-out stays CIP-0015.
- Jupyter Populate-all. Web path only unless the Jupyter button shares the same skip/flush helpers.
- Pagination of `inline_list` GET. That is [CIP-0020](./cip0020.md) (page size + append). This CIP remains the populate-all POST.
- Rolling batches, progress bar, and pause. That is [CIP-0021](./cip0021.md). This CIP is skip + flush + no listing rebuild.

## Implementation Plan

1. **Helpers on `WebReviewer` / data** (not in `routes.py` HTML):
   - Detect whether a populate spec’s target fields are already filled for the current index.
   - Flush named `cache:` columns to disk (same omit rules as Save’s cache write).
2. **`_run_populate_all_and_respond`**:
   - Skip filled rows unless this invocation is Refresh (`refresh: true` from that button).
   - Flush on the LLM cadence above.
   - Respond with status-bar OOB (and current-row widgets under `side_by_side`), never a full `inline_list` listing.
   - Batch cap, HTMX chain, progress, pause: [CIP-0021](./cip0021.md).
3. **Guidance**:
   - Dialogue template `02_embed` / `01_chunk`: `side_by_side`.
   - Note in CIP-0010 examples that populate-all on a large `inline_list` is a catalog anti-pattern.
4. **Tests**:
   - Populate-all skip + flush: after a fake extract of 3/10 rows and a new `WebReviewer`, the next populate-all only computes 7.
   - Populate-all response HTML has no per-row Extract textarea copies equal to working-set size.
   - Disconnect: flush happened; cache file row count matches `n_ok`.

## Backward Compatibility

- Single-row `POST /populate/{field}` unchanged.
- Save / Reload / explode / pack unchanged.
- Configs that relied on populate-all returning a rebuilt listing will see a status chip instead; Reload restores the list. That is the point.
- `refresh: true` on Extract (current dialogue YAML) still means “compute this row even if filled” for **one-row** Extract. Extract all must not inherit that as “re-extract the corpus every time.” Refresh cache remains the corpus redo. Implementation must distinguish the listing “Extract all” button from “Refresh cache” even if they share a YAML anchor today (`*extract_compute` with `refresh: true`).

## Testing Strategy

- Unit: skip/flush helpers with a temp `cache:` YAML (no LLM).
- Route: TestClient populate-all with a stub `run_populate` that records indices; assert skipped indices, assert cache file, assert response is a status fragment.
- Regression: `inline_list` catalog of ~20 rows still lists on GET; populate-all does not include 20 copies of a prompt textarea.
- Manual: dialogue `02_embed` Extract all on a handful of units, close the tab, reload, confirm cache rows and CIP-0017 status.

## Related Requirements

- [REQ-0010](../requirements/req0010_dialogue-pipeline-in-referia.md) — extract/embed results are columns on declared stores; RAM-only populate-all violates this until Save
- [REQ-0008](../requirements/req0008_web-review-without-jupyter.md) — web review must be usable without Jupyter; an hour-long XHR is not usable
- [REQ-0009](../requirements/req0009_multi-config-web-hosting.md) — one config’s populate must not monopolise the root server
- [REQ-000E](../requirements/req000E_named-layout-compositions.md) — `inline_list` is a named composition for catalogs, not a batch-job UI
- [REQ-0013](../requirements/req0013_restartable-review-runtime.md) — disconnect/restart must not imply lost compute (cache is the resume image)

## Implementation Status

- [ ] Skip filled populate targets unless Refresh cache
- [ ] Flush named cache during populate-all
- [ ] Survive disconnect; status fragment instead of full panel
- [ ] HTMX chain / progress / pause: CIP-0021
- [ ] Dialogue template layout: `side_by_side` on extract/embed stages
- [ ] Tests as above

## References

- `referia/web/routes.py` — `_run_populate_all_and_respond`, `_panel_response_context`
- `referia/web/render.py` — `render_populate_all_button`
- `referia/web/templates/base.html` — long-op bar, `htmx:sendError`
- [CIP-0010](./cip0010.md) — `inline_list` vs `side_by_side`
- [CIP-0015](./cip0015.md) — cache vs output vs pack; no sidecar checkpoints
- [CIP-0017](./cip0017.md) — named-store status; LLM diskcache is not analysis state
- [CIP-001B](./cip001B.md) — kernel/server split (complementary)
- [CIP-0020](./cip0020.md) — windowed `inline_list` GET (listing, not populate-all)
- [CIP-0021](./cip0021.md) — rolling batches, progress bar, pause
- Incident: dialogue-analysis `ai-dialogue-formats/02_embed` Extract all, 2013 units, 2026-10-29
