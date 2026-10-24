---
author: Neil D. Lawrence
created: '2026-10-24'
id: 001B
last_updated: '2026-10-24'
status: Proposed
compressed: false
related_requirements:
- '0008'
- '0009'
- '000B'
- '0013'
related_cips:
- '000B'
- '000C'
- '000E'
- '0010'
tags:
- cip
- web
- architecture
- kernel
- process-isolation
- fastapi
title: Jupyter-like kernel/server process split for the web review runtime
---

# CIP-001B: Jupyter-like kernel/server process split for the web review runtime

## Status

- [x] Proposed - Initial idea documented
- [ ] Accepted - Approved, ready to start work
- [ ] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected
- [ ] Deferred

## Summary

Split the web review runtime into two process roles, in the same spirit as
Jupyter's notebook server versus kernel: an HTTP process that stays up, and a
killable Python **review kernel** that owns `WebReviewer`, data, and compute.

This CIP produces that architecture. It does **not** add a YAML `RestartButton`.
The button is a follow-on that becomes honest only after a kernel exists.
REQ-0013 is the outcome; this CIP is the how.

## Motivation

CIP-000B already separated *display* from *assess*: FastAPI+HTMX renders HTML;
`Interface` and `CustomDataFrame` stay in the assess layer. That split is still
in-process. `referia serve` runs uvicorn in one process. `create_app` stores
`WebReviewer` on `app.state.reviewer` / `app.state.reviewer_cache`. Every HTMX
route calls that object on the asyncio worker. Compute (including LLM and PDF
work) runs inside the request.

Consequences today:

1. **Reload is not restart.** `ReloadButton` and `POST /reload` call
   `load_flows(reload=True)`. That rebuilds the dataframe from disk. It does
   not reimport compute functions, and it cannot interrupt a hung call.
2. **Config mtime cache is not restart.** `_get_cached_reviewer` recreates
   `WebReviewer` when `_referia.yml` changes. Same interpreter, same imported
   modules.
3. **One hung populate blocks the server.** Uvicorn is a single worker. A
   stuck compute blocks other configs on a CIP-000C root server, and blocks
   any UI that would try to recover.
4. **In-process `importlib.reload` is a trap.** It cannot kill a hung
   C-extension, is unreliable for packages with native code, and still shares
   the HTTP process.

Jupyter solved this years ago: the browser talks to a server that does not
execute user code; user code lives in a kernel the server can terminate.
Reviewers already expect that. The web path should not be weaker, and it
should not drag Jupyter in to get it (REQ-0008).

A restart *button* specified in `_referia.yml` is the right eventual UX. Putting
the button first would either lie (data reload labelled as kernel restart) or
force an ad-hoc process model under the widget. Split the runtime first; then
the button is a thin trigger on a manager that already knows how to kill and
respawn.

## Detailed Description

### Process roles

```
Browser  --HTTP/HTMX-->  HTTP process (stays up)
                           |  FastAPI routes, Jinja2, static, CIP-000E path jail
                           |  KernelManager (one kernel per loaded config, lazy)
                           |
                           |  JSON-RPC over a pipe / local socket
                           v
                         Review kernel process (killable)
                           WebReviewer, Interface, CustomDataFrame,
                           Compute registry, LLM calls
```

**HTTP process owns:**

- Binding host/port, serving HTML/CSS/JS, HTMX endpoints
- CIP-000E path safety (untrusted URL path segments, generic browser errors)
- Document byte serving from disk (jail stays in HTTP; files are not kernel memory)
- `KernelManager`: spawn, RPC, heartbeat, restart (SIGTERM then SIGKILL)
- The reviewer *cache keying* already in CIP-000C (config path + mtime), but
  the value is a `KernelHandle`, not a live `WebReviewer`

**Kernel process owns:**

- Constructing `WebReviewer` from a config directory
- Index, filters, widget values, `load_flows`, populate/compute
- Anything that imports user or referia Python that authors iterate on

This matches CIP-000B's layering: display in the application HTTP layer;
session Python in an explicit runtime. Lynguine is unchanged
(progressive-augmentation).

### Not Jupyter

We copy the *process idea*, not the protocol:

- No `jupyter_client`, ZeroMQ, or ipykernel
- No notebook document
- One referia-owned worker per loaded `_referia.yml`, not a general-purpose
  kernel marketplace

Jupyter kernels would reintroduce the dependency REQ-0008 removed and would
not understand `WebReviewer`. A small JSON command protocol is enough.

### RPC grain: coarse, not chatty, not pickle

`routes.py` currently walks `WebReviewer` in-process. `_panel_response_context`
calls `get_widget_specs`, `set_index` in a loop for `inline_list`,
`get_row_data`, `render_viewer_html`, and so on. Fine-grained RPC for each of
those calls would be slow and would leak assess internals across the boundary.

**Do not pickle `WebReviewer` across the boundary.** Pickle ties the two
processes to identical class layouts and is a hostile surface even on
localhost.

**Do use coarse commands** whose results are JSON (and, where needed, HTML
strings the HTTP process already knows how to wrap):

| Command | Result (sketch) |
|---|---|
| `start(config_dir)` | ready / load error |
| `panel_snapshot(index, view_options, …)` | structured context `_panel_response_context` needs, or rendered panel HTML |
| `set_field(column, value)` | enough to rebuild the HTMX fragments |
| `save` / `reload_data` | status + snapshot |
| `populate(field)` | snapshot or error |
| `ping` | heartbeat |

Exact method names can follow the current route handlers. The invariant is:
one user action is one (or a few) round trips, not one per widget field.

HTML rendering may stay in the HTTP process if the kernel returns a snapshot
dict. That keeps Jinja2 and CIP-000E path encoding on the server side. If a
snapshot becomes too large or too coupled, the kernel may return panel HTML
instead. Choose one in implementation and keep it consistent; do not mix
per-route.

### Restart is an OS operation

A healthy kernel can be asked to exit and be replaced. A hung kernel will not
read the command queue (numpy, a stuck HTTP client, a deadlock).

**Restart must not require kernel cooperation.** `KernelManager.restart(key)`:

1. Close the RPC channel
2. SIGTERM the child; wait a short timeout
3. SIGKILL if still alive
4. Spawn a new kernel for the same config directory
5. In-memory session for that config is gone (same as Jupyter). Data on disk
   is unchanged. Other kernels are untouched.

The HTTP process remains the process that accepted the restart request. A hung
compute on config A must not prevent restart of A or serving of config B.

### Migration: in-process adapter first

Routes today take a `WebReviewer`. Switching every call site and the process
boundary in one step is high risk.

1. Introduce `KernelHandle` with the coarse API above.
2. Implement `InProcessKernelHandle` wrapping today's `WebReviewer`. Routes
   talk only to `KernelHandle`. Behaviour unchanged; tests pin the facade.
3. Implement `SubprocessKernelHandle` + `KernelManager`. Flip the manager
   default to subprocess.
4. Add manager-level restart (CLI or internal HTTP) before any YAML widget.

This is a strangler replacement of `app.state.reviewer` /
`app.state.reviewer_cache`, not a fork of lynguine.

### Caching and root server

CIP-000C's cache remains: one handle per config path, invalidated on
`_referia.yml` mtime. Mtime invalidation destroys the handle (and, in
subprocess mode, the child) and creates a new one. That is *config change*,
still distinct from explicit restart, but it may share the same spawn path.

Root-server isolation becomes real: config A's compute cannot freeze B's
kernel. The HTTP process is still shared — a bug in a route handler can still
stall everyone — but user Python and long compute are out of that process.

### macOS spawn

Python's default start method on macOS is `spawn`, not `fork`. The kernel
entry point must be a module-level function (for example
`referia.web.kernel.main`) importable in a fresh interpreter. Do not close
over `WebReviewer` or the FastAPI app when starting the child.

### Security (REQ-000B / CIP-000E)

The kernel is local, same user, same trust model as today: the reviewer who
launched `referia serve` already has filesystem access. No new network
listener for the kernel. RPC is a pipe or a Unix socket in a private
directory, not a TCP port. Path jail and generic 404s stay in the HTTP
process; the kernel must not be given raw URL path segments to open.

### What this CIP does not do

- YAML `RestartButton` / review-widget for restart (follow-on CIP)
- `referia serve --reload` for HTTP-layer Python (complementary; uvicorn
  reload restarts the *server*, not one session)
- Multi-user remote kernels, authentication, or sandboxing beyond CIP-000E
- Changes to the Jupyter notebook review path (`referia.assess.review`)
- Lynguine process architecture

## Implementation Plan

1. **Facade.** Define `KernelHandle` and `InProcessKernelHandle`. Route
   helpers (`_reviewer`, `_get_cached_reviewer`, `_root_reviewer`) return
   handles. `_panel_response_context` consumes the coarse snapshot API.
2. **Tests on the facade.** Index, save, reload-data, populate, inline_list
   snapshot, config-mtime recreation — all against in-process first.
3. **Kernel worker.** `referia.web.kernel` entry point: construct
   `WebReviewer`, serve the command loop, exit on closed channel.
4. **Manager.** Spawn, RPC, ping, terminate. One child per cache key. Lazy
   start on first request (same as today's cache).
5. **Restart primitive.** Manager `restart(key)` as above. Expose internally
   (and optionally `POST` for the hung-config case) without requiring YAML.
6. **Isolation tests.** Hung compute in A: B still serves; A's restart
   succeeds; A's compute modules reimport after restart.
7. **Docs.** Note in the web README that session Python is a child process;
   Reload remains data-only.

## Backward Compatibility

- CLI: `referia serve` keeps the same flags and URLs. No Jupyter required.
- `_referia.yml`: no new keys in this CIP. ReloadButton/SaveButton unchanged.
- Jupyter review notebooks: untouched.
- In-memory session across an *unrequested* kernel death: lost, same as a
  Jupyter kernel crash. Persist-on-save behaviour is unchanged; unsaved
  widget state dies with the kernel. Call that out in docs.
- First request per config may pay process startup cost. Acceptable; can
  later pre-warm.

Default after this CIP: subprocess kernels. Keep the in-process handle as a
test double and as an emergency fallback only if spawn fails in a documented
way — not as the silent production path, or REQ-0013 is unmet.

## Testing Strategy

- Unit: kernel protocol (serialise/deserialise commands; unknown command
  errors).
- Unit: `InProcessKernelHandle` matches current route behaviour for a fixture
  config.
- Integration: subprocess handle starts, answers `ping`, returns a panel
  snapshot, dies cleanly.
- Isolation: thread or child that ignores SIGTERM until SIGKILL; manager
  restarts within timeout; second config's handle still answers `ping` during
  the hang.
- Restart: kernel imports a temp module; file changes on disk; after restart
  the new source is used; after `reload_data` only (no restart) the old
  function object remains — documents the Reload vs Restart distinction.
- Regression: CIP-000E path tests still pass (jail is HTTP-side).
- macOS: at least one spawn-based integration test in CI, not fork-only.

## Related Requirements

- [REQ-0013](../requirements/req0013_restartable-review-runtime.md) — this CIP
- [REQ-0008](../requirements/req0008_web-review-without-jupyter.md) — web
  without Jupyter; this kernel is referia's, not ipykernel
- [REQ-0009](../requirements/req0009_multi-config-web-hosting.md) — root
  server isolation depends on per-config processes
- [REQ-000B](../requirements/req000B_web-security-untrusted-paths.md) —
  kernel must not weaken the HTTP path jail

## Implementation Status

- [ ] KernelHandle facade and in-process adapter
- [ ] Routes talk only to KernelHandle
- [ ] Subprocess kernel worker and manager
- [ ] OS-level restart primitive
- [ ] Isolation and reimport tests
- [ ] Web docs: Reload vs Restart vs server --reload

## References

- CIP-000B: web display without Jupyter
- CIP-000C: root-server reviewer cache (mtime; one object per config — to
  become one kernel per config)
- CIP-000E: web path safety
- Jupyter: notebook server vs kernel as the UX analog, not the implementation
