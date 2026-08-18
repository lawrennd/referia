---
author: "lawrennd"
created: "2026-08-18"
id: "000E"
last_updated: "2026-08-18"
status: "Implemented"
compressed: false
related_requirements: []
related_cips: ["000B", "000C"]
tags:
- cip
- security
- codeql
- web
- path-injection
- xss
- github-actions
title: "Web Layer Security Hardening for CodeQL Findings"
---

# CIP-000E: Web Layer Security Hardening for CodeQL Findings

## Status

- [x] Proposed — Initial documentation complete
- [x] Accepted — Plan reviewed and approved
- [x] In Progress — Implementation underway
- [x] Implemented — Code and workflow changes complete
- [ ] Closed — CodeQL alerts cleared, tests pass, policy documented
- [ ] Rejected
- [ ] Deferred

## Summary

Address **20 open CodeQL alerts** on `lawrennd/referia` (August 2026) affecting the referia web
display layer and GitHub Actions workflows. The fixes are coordinated security hygiene: explicit
workflow permissions, a shared path-safety helper, generic user-facing error messages with
server-side logging, and verification of one likely false-positive XSS alert.

This CIP documents **policy and mechanism** so future web routes follow the same patterns. Backlog
tasks 1–4 are implemented; task 5 (CodeQL closure on GitHub) remains after the changes reach `main`.

## Motivation

### CodeQL alert inventory (open as of 2026-08-18)

| Category | Rule | Count | Severity | Primary files |
|----------|------|------:|----------|---------------|
| Workflow permissions | `actions/missing-workflow-permissions` | 3 | warning | `.github/workflows/*.yml` |
| Path injection | `py/path-injection` | 9 | error | `referia/web/routes.py`, `referia/assess/web_review.py` |
| Exception exposure | `py/stack-trace-exposure` | 8 | error | `referia/web/routes.py` |
| Reflected XSS | `py/reflective-xss` | 1 | error | `referia/web/routes.py` |

All application findings are confined to the web review interface introduced in **CIP-000B** and
extended for root-based routing in **CIP-000C**. No alerts affect core assess/compute logic outside
the web layer.

### Why document in a CIP

- **Cross-cutting policy**: what error detail reviewers see vs what stays in logs
- **Shared mechanism**: one path-safety API used from routes and `WebReviewer`
- **Threat model**: treat request input as untrusted now, so a later authenticated
  deployment does not have to retrofit path and error hygiene
- **Traceability**: closing GitHub alerts with rationale, not ad hoc suppressions

Dependabot and LangChain migration (**CIP-000D**) are out of scope.

## Detailed Description

### Threat model

The referia web server (`referia/web/app.py`) serves HTML review interfaces via FastAPI. Two modes:

1. **Single-config** — one `_referia.yml` loaded at startup
2. **Root-server** — URL paths map to configs under a filesystem root (**CIP-000C**)

There is **no authentication** today. The intended deployment is still a **trusted local reviewer**
(single user on localhost or a private network). **CIP-000B** already contemplates a later path to
remote and multi-user hosting. This CIP does not implement that path, but it **does** set policy so
the web layer is not built on “nobody else can reach us.”

**Invariant (now and after auth):** every URL path, query string, and form field is untrusted input.
Authentication would identify *who* may use the server; it would not make `../` in a config path
safe, nor would it make exception strings safe to return to a browser. Those controls belong in
the request-handling layer regardless of who is logged in.

Assume for this CIP:

- Anyone who can reach the server may probe URL paths and form endpoints
- Exception messages and paths must not leak filesystem layout or library internals to the browser
- Operator-facing detail remains in server logs and the `/errors` page

**Out of scope here (future CIP if we expose the interface):**

| Control | Why it is not this CIP |
|---------|------------------------|
| Authentication / authorisation | Product and UX decision; who may review which configs |
| TLS / bind address | Deployment, not CodeQL hygiene |
| CSRF protection | Needed once the origin is untrusted; HTMX posts would be in scope then |
| Session isolation | Multi-user cache and `/errors` currently assume one operator |

When that CIP exists, it should **rely on** the helpers and error policy from this CIP, not
reimplement them. `/errors` in particular would need an access-control decision: it is operator
detail today and must not stay anonymously reachable on a public host.

### 1. GitHub Actions workflow permissions (alerts #1–#3)

**Issue:** Workflows lack an explicit `permissions:` block; `GITHUB_TOKEN` receives default broad
scope.

**Files:**

- `.github/workflows/python-tests.yml` (alert #2)
- `.github/workflows/docs.yml` (alerts #1, #3 — both jobs)

**Policy:** Least privilege per job:

| Job | Minimum permissions |
|-----|---------------------|
| `python-tests` / `test-coverage` | `contents: read` |
| `build-and-deploy` (gh-pages) | `contents: write` (`peaceiris/actions-gh-pages` pushes the `gh-pages` branch) |

Implemented 2026-08-18. `pages: write` / `id-token: write` are not required for this action.

### 2. Path injection (alerts #4–#11)

**Issue:** CodeQL tracks URL path segments (`config_path`) into `Path` operations and `os.chdir`.

**Existing mitigation** in `_resolve_config_path`:

```python
root_p = Path(root).resolve()
candidate = (root_p / clean).resolve()
config_dir.relative_to(root_p)  # rejects escape
```

CodeQL does not treat this as a sanitizer, so alerts remain. **Gaps:**

| Location | Concern |
|----------|---------|
| `_list_sub_configs` | `search_base = root_path / clean` without resolve + `relative_to` before `rglob` |
| `_get_cached_reviewer` | Uses resolved path from helper; alert is on `stat()` sink |
| `WebReviewer.__init__` | `chdir(directory)` where `directory` is parent of config file |

**Proposed mechanism:** add `referia/web/path_safety.py` (or module-level helpers in `routes.py` if
prefer minimal files):

```python
def safe_path_under_root(root: Path, *parts: str) -> Path:
    """Resolve *parts* under *root*; raise PathOutsideRootError if escape."""
    root = root.resolve()
    candidate = root.joinpath(*parts).resolve()
    candidate.relative_to(root)  # ValueError → our error type
    return candidate
```

Use consistently in:

- `_resolve_config_path`
- `_list_sub_configs` (validate `search_base` before `rglob`)
- Any future route that maps URL segments to filesystem paths

`WebReviewer` should receive only paths already validated by callers, or call the helper at init
with `root` + relative segments — document which layer owns validation (routes layer, not
`WebReviewer`).

**Symlinks:** `resolve()` + `relative_to` is the standard defence; add tests for `../` segments and
symlink escape attempts where the test environment allows.

### 3. Exception / stack-trace exposure (alerts #13–#20)

**Issue:** Handlers return `str(exc)` in HTML responses or `HTTPException.detail`, exposing internal
messages (paths, parse errors, library text) to whoever can use the web UI.

**Affected patterns** (single-config and root-mode duplicates):

| Route | Lines (approx.) |
|-------|-----------------|
| `update_field` / `root_update_field` | 335, 1034 |
| `save` / `root_save` | 369, 1058 |
| `reload` / `root_reload` | 382, 1071 |
| `populate` / `_run_populate_and_respond` | 980 |
| `_get_cached_reviewer` | 480, 499 |

Note: `_esc(str(exc))` prevents HTML injection but **does not** satisfy the spirit of
stack-trace-exposure — exception strings are still information disclosure.

**Policy:**

| Audience | What they see |
|----------|----------------|
| Browser (reviewer) | Short generic message: e.g. `"Save failed. See server log."` |
| Server log | Full exception with `log.exception(...)` |
| `/errors` page | Detailed load/parse failures (operator tool; unchanged) |
| `HTTPException` JSON/HTML detail | Generic text; no `{exc}` interpolation |

**Proposed helpers** in `referia/web/routes.py`:

```python
def _user_error_html(action: str) -> str:
    return f'<span class="status-error">&#10007; {_esc(action)} failed. See server log.</span>'

def _log_route_error(action: str, exc: Exception, **context) -> None:
    log.exception("%s failed %s", action, context)
```

Replace all user-facing `str(exc)` returns in HTMX handlers. Keep `_esc` for any dynamic text that
remains user-visible (titles, config metadata from YAML).

### 4. Reflected XSS (alert #12)

**Location:** `_render_directory_listing` return at ~line 925.

**Analysis:** `label` is built as `f"/{_esc(breadcrumb)}"` — content is HTML-escaped. CodeQL likely
does not model `_esc()` as a sanitizer.

**Plan:**

1. Confirm no unescaped user/query input reaches the HTML template
2. Prefer inline `html.escape(breadcrumb)` at the sink if needed for CodeQL
3. If still flagged after review, document suppression with comment citing escape at source
4. Review `href="{inh_url}"` (~831): URLs are filesystem-derived, not raw query input — low risk

### Alternatives considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **CIP + backlog tasks** | Policy documented; traceable closure | Requires acceptance step | **Preferred** |
| Backlog only | Faster start | Design drifts into task files | Reject |
| CodeQL suppressions only | Zero code change | Alerts stay open or dismissed without fix | Reject except XSS if proven FP |
| Add authentication in this CIP | Addresses future exposure | Mixes CodeQL hygiene with a product decision CIP-000B deferred | **Defer to a later CIP**; treat request input as untrusted now so that CIP has a solid base |

## Implementation Plan

Backlog tasks (phases 1–4 Completed 2026-08-18; phase 5 waits for GitHub CodeQL):

1. [`2026-08-18_cip000E-workflow-permissions`](../backlog/infrastructure/2026-08-18_cip000E-workflow-permissions.md) — alerts **#1–#3**
2. [`2026-08-18_cip000E-exception-exposure`](../backlog/infrastructure/2026-08-18_cip000E-exception-exposure.md) — alerts **#13–#20**
3. [`2026-08-18_cip000E-path-safety`](../backlog/infrastructure/2026-08-18_cip000E-path-safety.md) — alerts **#4–#11**
4. [`2026-08-18_cip000E-xss-verification`](../backlog/infrastructure/2026-08-18_cip000E-xss-verification.md) — alert **#12**
5. [`2026-08-18_cip000E-codeql-closure`](../backlog/infrastructure/2026-08-18_cip000E-codeql-closure.md) — confirm 20 → 0 on GitHub

See each task for acceptance criteria. Phase 5 depends on 1–4.

## Backward Compatibility

- **Reviewer UX**: Error messages become less specific in the browser; operators use logs and `/errors`
- **API shape**: No change to routes, HTMX contracts, or YAML configuration
- **Single-config vs root mode**: Both modes receive the same error and path policies
- **No breaking changes** to Python library APIs outside the web layer
- **Future authenticated hosting**: no API reserved for auth in this CIP; new routes must use the
  same path-safety helper and generic error responses so they do not reintroduce these CodeQL classes

## Testing Strategy

```bash
poetry run pytest tests/test_web_routes.py tests/test_web_app.py -v
poetry run pytest tests/ -q
```

**New/extended tests:**

- Path traversal rejected (`../`, absolute escape, encoded segments)
- Error handlers return generic HTML without exception text (mock failing `save_flows`, etc.)
- Workflow YAML valid (CI is the integration test for permissions)

**CodeQL:** Confirm alert closure on GitHub after merge to `main` (may lag one scan cycle).

## Related Requirements

None formally tracked. Aligns with document-centric reviewing (CIP-000B/000C) and pragmatic
automation tenet: security tooling should be satisfied without blocking local reviewer workflows.

## Implementation Status

- [x] Workflow permissions added (#1–#3)
- [x] User-facing exception policy implemented (#13–#20)
- [x] Path safety helper and refactors (#4–#11)
- [x] XSS alert resolved or documented (#12)
- [x] Web route tests extended
- [x] Full test suite passes
- [ ] All 20 CodeQL alerts closed on GitHub

## References

- [CIP-000B](./cip000B.md) — Web Display System
- [CIP-000C](./cip000C.md) — Multi-Config Web Server
- Code: `referia/web/routes.py`, `referia/web/app.py`, `referia/assess/web_review.py`
- Workflows: `.github/workflows/python-tests.yml`, `.github/workflows/docs.yml`
- GitHub Code scanning: https://github.com/lawrennd/referia/security/code-scanning
