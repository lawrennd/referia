"""FastAPI HTMX routes for the referia web review interface.

Single-config mode (``app.state.root is None``)
------------------------------------------------
All routes share a ``WebReviewer`` instance stored in ``app.state.reviewer``.

``GET /``
    Full page for the current record.

``GET /record``
    Review-panel fragment for ``?index=<value>`` (HTMX partial swap).

``GET /indices``
    Index-selector ``<select>`` fragment.

``POST /field/{column}``
    Accept a form value, call ``WebReviewer.set_value()``, return a status
    fragment plus OOB widget refreshes for all affected columns.

``POST /save``
    Persist data; return a status fragment.

``POST /reload``
    Reload data from source files; return a refreshed review panel.

``POST /populate/{field}``
    Trigger an on-demand compute function for *field*; return a status
    fragment plus the refreshed widget.

Root-server mode (``app.state.root`` is a directory path)
----------------------------------------------------------
The ``root_router`` mirrors every single-config route but prefixed with a
``{config_path:path}`` segment that maps a URL path to a ``_referia.yml``
under the root directory.  Reviewers are lazily loaded and cached by
``_get_cached_reviewer``.

``GET /{config_path:path}``
    Full page for the named config (last in root_router to act as catch-all).

``GET /{config_path:path}/record``
    Panel fragment.

``GET /{config_path:path}/indices``
    Index selector.

``POST /{config_path:path}/field/{column}``
    Field update.

``POST /{config_path:path}/save`` / ``POST /{config_path:path}/reload``
    Persist / reload.

``POST /{config_path:path}/populate/{field}``
    On-demand compute.

Client-side URL rewriting
--------------------------
``base.html`` injects a ``CONFIG_PATH`` JS constant (empty string in
single-config mode, the config prefix in root mode).  An
``htmx:configRequest`` listener prepends it to all HTMX request paths, so
``render.py`` never needs to know about path prefixes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from referia.web.render import render_widget, render_form, render_viewer

log = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_form_value(raw: Any, spec: dict | None) -> Any:
    """Convert a raw form string to the appropriate Python type for *spec*.

    HTML form submissions are always strings.  This function applies the
    minimal coercion needed so that ``set_value`` receives a value of the
    expected type for the widget.
    """
    if spec is None:
        return raw
    widget_type = spec.get("type", "")
    if widget_type in {"Checkbox", "Flag"}:
        return bool(raw and raw not in {"false", "off", "0", ""})
    if widget_type in {"IntSlider", "BoundedIntText", "IntText"}:
        try:
            return int(raw)
        except (TypeError, ValueError):
            return raw
    if widget_type in {"FloatSlider", "BoundedFloatText", "FloatText"}:
        try:
            return float(raw)
        except (TypeError, ValueError):
            return raw
    return raw


def _reviewer(request: Request):
    reviewer = request.app.state.reviewer
    if reviewer is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=(
                "Review session could not be initialised. "
                "Check the server log for startup errors — likely a missing or "
                "malformed _referia.yml, or a data file that could not be loaded."
            ),
        )
    return reviewer


def _templates(request: Request):
    return request.app.state.templates


def _current_data(reviewer) -> dict:
    """Return the current record's data as a plain dict for widget rendering.

    Starts from the full row so that columns referenced in ``visible_if``
    conditions (which may not have a corresponding widget) are available.
    Widget-field values are then refreshed via :meth:`get_value` to pick up
    any in-flight changes that haven't been persisted yet.
    """
    data: dict = reviewer.get_row_data()
    for spec in reviewer.get_widget_specs():
        col = spec.get("field")
        if col:
            try:
                data[col] = reviewer.get_value(col)
            except Exception:
                data[col] = None
    return data


def _find_spec(reviewer, column: str) -> dict | None:
    """Return the first widget spec whose ``field`` matches *column*.

    Skips PopulateButton specs because they share ``field`` with their target
    widget; use :func:`_find_populate_spec` to locate buttons specifically.
    """
    for spec in reviewer.get_widget_specs():
        if spec.get("field") == column and spec.get("type") != "PopulateButton":
            return spec
    return None


def _populate_button_target(spec: dict) -> str:
    """Return the effective target field for a PopulateButton spec.

    Handles both formats:
    * Simple: top-level ``field`` key.
    * Complex: ``args.target`` or ``args.compute.field``.

    ``args.target`` / ``args.compute.field`` take priority because the
    top-level ``field`` may be a button identifier, not the populate target.
    """
    args = spec.get("args", {})
    return (
        args.get("target")
        or args.get("compute", {}).get("field")
        or spec.get("field")
        or ""
    )


def _find_populate_spec(reviewer, field: str) -> dict | None:
    """Return the PopulateButton spec whose effective target field matches *field*."""
    for spec in reviewer.get_widget_specs():
        if spec.get("type") == "PopulateButton" and _populate_button_target(spec) == field:
            return spec
    return None


def _panel_response_context(reviewer) -> dict:
    """Build the shared template context dict for ``review_panel.html``.

    Used by single-config and root-mode routes so the panel-rendering logic
    lives in exactly one place.
    """
    indices = reviewer.index_list()
    current_index = reviewer.get_index()
    data = _current_data(reviewer)

    viewer_blocks = [
        reviewer.render_viewer_html(spec)
        for spec in reviewer.get_viewer_specs()
    ]
    form_html = render_form(reviewer.get_review_specs(), data)
    index_selector = _render_index_selector(indices, current_index)

    return {
        "index_selector": index_selector,
        "viewer_blocks": viewer_blocks,
        "form_html": form_html,
        "current_index": current_index,
        "total": len(indices),
        "position": (indices.index(current_index) + 1) if current_index in indices else "?",
    }


def _render_panel(reviewer, request: Request) -> str:
    """Render the full review panel as an HTML string."""
    ctx = _panel_response_context(reviewer)
    response = _templates(request).TemplateResponse(request, "review_panel.html", ctx)
    return response.body.decode()


def _render_index_selector(indices: list, current_index: Any) -> str:
    """Render the index ``<select>`` widget as an HTML string."""
    options = "\n".join(
        f'  <option value="{_esc(idx)}"'
        f'{" selected" if idx == current_index else ""}>'
        f"{_esc(idx)}</option>"
        for idx in indices
    )
    return (
        '<select id="index-select" name="index" class="index-select"\n'
        '        hx-get="/record"\n'
        '        hx-trigger="change"\n'
        '        hx-target="#review-panel"\n'
        '        hx-swap="innerHTML">\n'
        f"{options}\n"
        "</select>"
    )


def _esc(value: Any) -> str:
    import html
    return html.escape(str(value) if value is not None else "")


def _make_oob(widget_html: str) -> str:
    """Add ``hx-swap-oob="true"`` to the outermost widget container div."""
    return widget_html.replace(
        'class="widget-container"',
        'class="widget-container" hx-swap-oob="true"',
        1,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the full review page for the current record."""
    reviewer = _reviewer(request)
    ctx = _panel_response_context(reviewer)
    return _templates(request).TemplateResponse(
        request,
        "base.html",
        {
            "title": "Referia Review Interface",
            "config": request.app.state.user_file,
            "directory": request.app.state.directory,
            "cache_bust": request.app.state.start_time,
            "config_path_prefix": "",
            **ctx,
        },
    )


@router.get("/record", response_class=HTMLResponse)
async def get_record(request: Request, index: str | None = None):
    """Return the review-panel HTML fragment for *index* (HTMX partial swap).

    Called by the index ``<select>`` via HTMX. The response replaces the
    ``#review-panel`` div's inner HTML.
    """
    reviewer = _reviewer(request)
    if index is not None:
        reviewer.set_index(index)
    ctx = _panel_response_context(reviewer)
    return _templates(request).TemplateResponse(request, "review_panel.html", ctx)


@router.get("/indices", response_class=HTMLResponse)
async def get_indices(request: Request):
    """Return the index-selector ``<select>`` fragment."""
    reviewer = _reviewer(request)
    return HTMLResponse(_render_index_selector(reviewer.index_list(), reviewer.get_index()))


@router.post("/field/{column}", response_class=HTMLResponse)
async def update_field(request: Request, column: str):
    """Accept a form value, update the data, return status + OOB widget refreshes.

    The primary response target is ``#status-bar`` (set by the HTMX attributes
    on every field control in ``render.py``).  Affected widget divs are returned
    as HTMX OOB swaps so the page reflects computed side-effects.
    """
    reviewer = _reviewer(request)
    form = await request.form()
    raw_value = form.get(column)
    log.debug("update_field: column=%r raw_value=%r form_keys=%s", column, raw_value, list(form.keys()))

    spec = _find_spec(reviewer, column)
    value: Any = _coerce_form_value(raw_value, spec)

    try:
        reviewer.set_value(column, value)
        status_html = '<span class="status-ok">&#10003; Updated</span>'
    except Exception as exc:
        log.warning("Failed to update field %r: %s", column, exc)
        status_html = f'<span class="status-error">&#10007; Error: {_esc(str(exc))}</span>'
        return HTMLResponse(status_html)

    # Build OOB refreshes for all affected widgets
    data = _current_data(reviewer)
    parts = [status_html]
    for col in reviewer.affected_widgets(column):
        affected_spec = _find_spec(reviewer, col)
        if affected_spec:
            val = reviewer.get_value(col)
            widget_html = render_widget(affected_spec, val, data)
            parts.append(_make_oob(widget_html))

    return HTMLResponse("\n".join(parts))


@router.post("/save", response_class=HTMLResponse)
async def save(request: Request):
    """Persist the current in-memory reviewer state to output files.

    Each field already posted its own value to ``/field/{column}`` when the
    user edited it (via change, blur, or mouseup HTMX triggers), so the
    reviewer's in-memory state is already up-to-date by the time Save is
    clicked.  This route only needs to flush that state to disk.

    Calling ``set_value`` here would re-run compute functions with potentially
    stale or unintended values, so we deliberately avoid it.
    """
    reviewer = _reviewer(request)
    try:
        reviewer.save_flows()
        return HTMLResponse('<span class="status-ok">&#10003; Saved</span>')
    except Exception as exc:
        log.warning("Save failed: %s", exc)
        return HTMLResponse(f'<span class="status-error">&#10007; Save failed: {_esc(str(exc))}</span>')


@router.post("/reload", response_class=HTMLResponse)
async def reload_data(request: Request):
    """Reload data from source files and return a refreshed review panel."""
    reviewer = _reviewer(request)
    templates = _templates(request)

    try:
        reviewer.load_flows(reload=True)
    except Exception as exc:
        log.warning("Reload failed: %s", exc)
        return HTMLResponse(f'<span class="status-error">&#10007; Reload failed: {_esc(str(exc))}</span>')

    ctx = _panel_response_context(reviewer)
    return templates.TemplateResponse(request, "review_panel.html", ctx)


@router.post("/populate/{field}", response_class=HTMLResponse)
async def populate_field(request: Request, field: str):
    """Run the compute attached to a PopulateButton and refresh the target widget.

    *field* is the PopulateButton's effective target field name (used in the URL).
    The button spec's ``args.target`` / ``args.compute.field`` names the field to
    update, and ``args.compute`` is forwarded to the compute engine — exactly as
    the Jupyter ``PopulateButton.on_click`` does.

    Supports two YAML formats:

    Format A (complex — ``args.compute``):

    .. code-block:: yaml

       - type: PopulateButton
         args:
           target: summary
           compute: {field: summary, function: llm_summarise, ...}

    Format B (simple — top-level ``function``):

    .. code-block:: yaml

       - type: PopulateButton
         field: summary
         function: llm_summarise
         args: {text: "{description}"}
    """
    reviewer = _reviewer(request)
    btn_spec = _find_populate_spec(reviewer, field)
    if btn_spec is None:
        return HTMLResponse(
            f'<span class="status-warning">&#9888; No PopulateButton found for field {_esc(field)}</span>'
        )
    return _run_populate_and_respond(reviewer, field, btn_spec)


# ===========================================================================
# Root-server helpers
# ===========================================================================


def _resolve_config_path(root: str, url_path: str) -> tuple[Path, str]:
    """Map a URL path to ``(config_file, user_file)`` under *root*.

    Handles:
    - ``"theses/examined/introduction"``              → …/introduction/_referia.yml
    - ``"theses/examined/introduction/"``              → same (trailing slash stripped)
    - ``"theses/examined/introduction/_referia_v2.yml"`` → explicit yml file

    Raises ``HTTPException`` 400 for path traversal, 404 if the config is missing.
    """
    from fastapi import HTTPException

    root_p = Path(root).resolve()
    clean = url_path.strip("/")

    if clean.endswith(".yml"):
        candidate = (root_p / clean).resolve()
        user_file = candidate.name
        config_dir = candidate.parent
    else:
        config_dir = (root_p / clean).resolve() if clean else root_p
        user_file = "_referia.yml"
        candidate = config_dir / user_file

    # Security: reject paths that escape the root
    try:
        config_dir.relative_to(root_p)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path outside root rejected")

    if not candidate.exists():
        raise HTTPException(status_code=404, detail=f"Config not found: /{clean}")

    return candidate, user_file


def _get_cached_reviewer(app_state, config_file: Path, user_file: str):
    """Return the ``WebReviewer`` for *config_file*, loading or refreshing from cache.

    Cache entries are keyed by absolute config file path and invalidated when
    the file's ``mtime`` changes, so editing a ``_referia.yml`` on disk takes
    effect on the next request without restarting the server.
    """
    from fastapi import HTTPException

    key = str(config_file)
    try:
        mtime = config_file.stat().st_mtime
    except OSError as exc:
        raise HTTPException(status_code=404, detail=f"Config not accessible: {exc}")

    cached = app_state.reviewer_cache.get(key)
    if cached is None or cached[0] != mtime:
        from referia.assess.web_review import WebReviewer
        try:
            reviewer = WebReviewer(user_file, str(config_file.parent))
        except Exception as exc:
            log.error("Failed to load config %s: %s", config_file, exc)
            raise HTTPException(status_code=503, detail=f"Could not load config: {exc}")
        app_state.reviewer_cache[key] = (mtime, reviewer)

    return app_state.reviewer_cache[key][1]


def _root_reviewer(request: Request, config_path: str):
    """Resolve and return the ``WebReviewer`` for a root-mode request."""
    config_file, user_file = _resolve_config_path(
        request.app.state.root, config_path
    )
    return _get_cached_reviewer(request.app.state, config_file, user_file)


def _config_path_prefix(config_path: str) -> str:
    """Normalise a URL config path to an absolute prefix string for JS injection.

    ``"theses/examined/introduction"`` → ``"/theses/examined/introduction"``
    """
    clean = config_path.strip("/")
    return f"/{clean}" if clean else ""


def _build_populate_compute_spec(btn_spec: dict, field: str) -> dict | None:
    """Extract or construct a compute spec from a PopulateButton widget spec.

    Supports both YAML formats (see populate_field docstring).
    Returns ``None`` if neither format provides enough information.
    """
    args = btn_spec.get("args", {})
    compute_spec = args.get("compute")
    target = args.get("target", field)

    if compute_spec is None:
        top_fn = btn_spec.get("function")
        if top_fn:
            view_args = {
                k: ({"display": v} if isinstance(v, str) else v)
                for k, v in args.items()
            }
            compute_spec = {
                "field": target,
                "function": top_fn,
                "view_args": view_args,
                "refresh": True,
            }

    return compute_spec


def _run_populate_and_respond(reviewer, field: str, btn_spec: dict) -> HTMLResponse:
    """Shared populate logic for both single-config and root-mode routes."""
    compute_spec = _build_populate_compute_spec(btn_spec, field)

    if compute_spec is None:
        return HTMLResponse(
            '<span class="status-warning">&#9888; PopulateButton has no compute spec</span>'
        )

    target = btn_spec.get("args", {}).get("target", field)

    try:
        reviewer.run_populate({"compute": compute_spec})
    except Exception as exc:
        log.warning("Populate failed for %r: %s", field, exc)
        return HTMLResponse(
            f'<span class="status-error">&#10007; Populate failed: {_esc(str(exc))}</span>'
        )

    target_spec = _find_spec(reviewer, target)
    if target_spec is None:
        return HTMLResponse('<span class="status-ok">&#10003; Populated</span>')

    val = reviewer.get_value(target)
    data = _current_data(reviewer)
    widget_html = render_widget(target_spec, val, data)
    return HTMLResponse('<span class="status-ok">&#10003; Populated</span>\n' + _make_oob(widget_html))


# ===========================================================================
# Root-server router
#
# Routes are ordered most-specific → least-specific.  The catch-all
# ``GET /{config_path:path}`` MUST be last so it doesn't swallow the action
# suffixes (/record, /field/…, etc.).
# ===========================================================================

root_router = APIRouter()


@root_router.get("/{config_path:path}/record", response_class=HTMLResponse)
async def root_get_record(request: Request, config_path: str, index: str | None = None):
    reviewer = _root_reviewer(request, config_path)
    if index is not None:
        reviewer.set_index(index)
    ctx = _panel_response_context(reviewer)
    return _templates(request).TemplateResponse(request, "review_panel.html", ctx)


@root_router.get("/{config_path:path}/indices", response_class=HTMLResponse)
async def root_get_indices(request: Request, config_path: str):
    reviewer = _root_reviewer(request, config_path)
    return HTMLResponse(_render_index_selector(reviewer.index_list(), reviewer.get_index()))


@root_router.post("/{config_path:path}/field/{column}", response_class=HTMLResponse)
async def root_update_field(request: Request, config_path: str, column: str):
    reviewer = _root_reviewer(request, config_path)
    form = await request.form()
    raw_value = form.get(column)

    spec = _find_spec(reviewer, column)
    value: Any = _coerce_form_value(raw_value, spec)

    try:
        reviewer.set_value(column, value)
        status_html = '<span class="status-ok">&#10003; Updated</span>'
    except Exception as exc:
        log.warning("root_update_field %r: %s", column, exc)
        return HTMLResponse(
            f'<span class="status-error">&#10007; Error: {_esc(str(exc))}</span>'
        )

    data = _current_data(reviewer)
    parts = [status_html]
    for col in reviewer.affected_widgets(column):
        affected_spec = _find_spec(reviewer, col)
        if affected_spec:
            val = reviewer.get_value(col)
            widget_html = render_widget(affected_spec, val, data)
            parts.append(_make_oob(widget_html))

    return HTMLResponse("\n".join(parts))


@root_router.post("/{config_path:path}/save", response_class=HTMLResponse)
async def root_save(request: Request, config_path: str):
    reviewer = _root_reviewer(request, config_path)
    try:
        reviewer.save_flows()
        return HTMLResponse('<span class="status-ok">&#10003; Saved</span>')
    except Exception as exc:
        log.warning("root_save: %s", exc)
        return HTMLResponse(
            f'<span class="status-error">&#10007; Save failed: {_esc(str(exc))}</span>'
        )


@root_router.post("/{config_path:path}/reload", response_class=HTMLResponse)
async def root_reload(request: Request, config_path: str):
    reviewer = _root_reviewer(request, config_path)
    templates = _templates(request)
    try:
        reviewer.load_flows(reload=True)
    except Exception as exc:
        log.warning("root_reload: %s", exc)
        return HTMLResponse(
            f'<span class="status-error">&#10007; Reload failed: {_esc(str(exc))}</span>'
        )
    ctx = _panel_response_context(reviewer)
    return templates.TemplateResponse(request, "review_panel.html", ctx)


@root_router.post("/{config_path:path}/populate/{field}", response_class=HTMLResponse)
async def root_populate(request: Request, config_path: str, field: str):
    reviewer = _root_reviewer(request, config_path)
    btn_spec = _find_populate_spec(reviewer, field)
    if btn_spec is None:
        return HTMLResponse(
            f'<span class="status-warning">&#9888; No PopulateButton for {_esc(field)}</span>'
        )
    return _run_populate_and_respond(reviewer, field, btn_spec)


# ── Catch-all full page — MUST be registered last ────────────────────────────

@root_router.get("/{config_path:path}", response_class=HTMLResponse)
async def root_index(request: Request, config_path: str):
    """Render the full review page for a root-mode config path."""
    reviewer = _root_reviewer(request, config_path)
    ctx = _panel_response_context(reviewer)
    prefix = _config_path_prefix(config_path)

    # Derive a display title: use the last path component as a readable label
    display_title = config_path.strip("/").split("/")[-1] if config_path.strip("/") else "Referia"

    return _templates(request).TemplateResponse(
        request,
        "base.html",
        {
            "title": display_title,
            "config": f"{config_path.strip('/')}/_referia.yml",
            "directory": reviewer._directory if hasattr(reviewer, "_directory") else config_path,
            "cache_bust": request.app.state.start_time,
            "config_path_prefix": prefix,
            **ctx,
        },
    )
