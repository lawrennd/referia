"""FastAPI HTMX routes for the referia web review interface.

All routes share a ``WebReviewer`` instance stored in ``app.state.reviewer``.
The Jinja2 ``Templates`` object lives in ``app.state.templates``.

Route summary
-------------

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
"""

from __future__ import annotations

import logging
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
    """Return the current record's data as a plain dict for widget rendering."""
    idx = reviewer.get_index()
    data: dict = {}
    for spec in reviewer.get_widget_specs():
        col = spec.get("field")
        if col:
            try:
                data[col] = reviewer.get_value(col)
            except Exception:
                data[col] = None
    return data


def _find_spec(reviewer, column: str) -> dict | None:
    """Return the widget spec for *column*, or ``None`` if not found."""
    for spec in reviewer.get_widget_specs():
        if spec.get("field") == column:
            return spec
    return None


def _render_panel(reviewer, request: Request) -> str:
    """Render the full review panel as an HTML string."""
    templates = _templates(request)
    indices = reviewer.index_list()
    current_index = reviewer.get_index()
    data = _current_data(reviewer)

    viewer_blocks = [
        reviewer.render_viewer_html(spec)
        for spec in reviewer.get_viewer_specs()
    ]
    form_html = render_form(reviewer.get_review_specs(), data)
    index_selector = _render_index_selector(indices, current_index)

    response = templates.TemplateResponse(
        request,
        "review_panel.html",
        {
            "index_selector": index_selector,
            "viewer_blocks": viewer_blocks,
            "form_html": form_html,
            "current_index": current_index,
            "total": len(indices),
            "position": (indices.index(current_index) + 1) if current_index in indices else "?",
        },
    )
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
    templates = _templates(request)
    indices = reviewer.index_list()
    current_index = reviewer.get_index()
    data = _current_data(reviewer)

    viewer_blocks = [
        reviewer.render_viewer_html(spec)
        for spec in reviewer.get_viewer_specs()
    ]
    form_html = render_form(reviewer.get_review_specs(), data)
    index_selector = _render_index_selector(indices, current_index)

    return templates.TemplateResponse(
        request,
        "base.html",
        {
            "title": "Referia Review Interface",
            "config": request.app.state.user_file,
            "directory": request.app.state.directory,
            "index_selector": index_selector,
            "viewer_blocks": viewer_blocks,
            "form_html": form_html,
            "current_index": current_index,
            "total": len(indices),
            "position": (indices.index(current_index) + 1) if current_index in indices else "?",
        },
    )


@router.get("/record", response_class=HTMLResponse)
async def get_record(request: Request, index: str | None = None):
    """Return the review-panel HTML fragment for *index* (HTMX partial swap).

    Called by the index ``<select>`` via HTMX. The response replaces the
    ``#review-panel`` div's inner HTML.
    """
    reviewer = _reviewer(request)
    templates = _templates(request)

    if index is not None:
        reviewer.set_index(index)

    current_index = reviewer.get_index()
    indices = reviewer.index_list()
    data = _current_data(reviewer)

    viewer_blocks = [
        reviewer.render_viewer_html(spec)
        for spec in reviewer.get_viewer_specs()
    ]
    form_html = render_form(reviewer.get_review_specs(), data)
    index_selector = _render_index_selector(indices, current_index)

    return templates.TemplateResponse(
        request,
        "review_panel.html",
        {
            "index_selector": index_selector,
            "viewer_blocks": viewer_blocks,
            "form_html": form_html,
            "current_index": current_index,
            "total": len(indices),
            "position": (indices.index(current_index) + 1) if current_index in indices else "?",
        },
    )


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

    current_index = reviewer.get_index()
    indices = reviewer.index_list()
    data = _current_data(reviewer)

    viewer_blocks = [
        reviewer.render_viewer_html(spec)
        for spec in reviewer.get_viewer_specs()
    ]
    form_html = render_form(reviewer.get_review_specs(), data)
    index_selector = _render_index_selector(indices, current_index)

    return templates.TemplateResponse(
        request,
        "review_panel.html",
        {
            "index_selector": index_selector,
            "viewer_blocks": viewer_blocks,
            "form_html": form_html,
            "current_index": current_index,
            "total": len(indices),
            "position": (indices.index(current_index) + 1) if current_index in indices else "?",
        },
    )


@router.post("/populate/{field}", response_class=HTMLResponse)
async def populate_field(request: Request, field: str):
    """Run the compute attached to a PopulateButton and refresh the target widget.

    *field* is the PopulateButton's own field name (used in the URL).  The
    button spec's ``args.target`` names the field to update, and
    ``args.compute`` is the compute spec forwarded to the compute engine —
    exactly as the Jupyter ``PopulateButton.on_click`` does.
    """
    reviewer = _reviewer(request)
    btn_spec = _find_spec(reviewer, field)

    if btn_spec is None or btn_spec.get("type") != "PopulateButton":
        return HTMLResponse(
            f'<span class="status-warning">&#9888; No PopulateButton found for field {_esc(field)}</span>'
        )

    args = btn_spec.get("args", {})
    compute_spec = args.get("compute")
    target = args.get("target", field)

    if compute_spec is None:
        return HTMLResponse(
            '<span class="status-warning">&#9888; PopulateButton has no compute spec</span>'
        )

    try:
        reviewer.run_populate({"compute": compute_spec})
    except Exception as exc:
        log.warning("Populate failed for %r: %s", field, exc)
        return HTMLResponse(
            f'<span class="status-error">&#10007; Populate failed: {_esc(str(exc))}</span>'
        )

    # Re-render the target field widget so the user sees the new value.
    target_spec = _find_spec(reviewer, target)
    if target_spec is None:
        return HTMLResponse('<span class="status-ok">&#10003; Populated</span>')

    val = reviewer.get_value(target)
    data = _current_data(reviewer)
    widget_html = render_widget(target_spec, val, data)
    status = '<span class="status-ok">&#10003; Populated</span>'
    return HTMLResponse(status + "\n" + _make_oob(widget_html))
