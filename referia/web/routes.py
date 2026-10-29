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

``POST /field-bulk/{column}``
    Set *column* on every index in the current filtered working set
    (inline_list select-all); return a refreshed review panel.

``POST /save``
    Persist data; return a status fragment.

``POST /reload``
    Reload data from source files; return a refreshed review panel.

``GET /document/{path:path}`` / ``GET /record-document/{kind}/{n}``
    Serve a file or a current-record PDF (``localpdf`` / ``editpdf``).

``POST /populate/{field}``
    Trigger an on-demand compute function for *field*; return a status
    fragment plus the refreshed widget. Optional form ``index`` selects the
    listing row (inline_list). On ``inline_list`` the response is a refreshed
    review panel.

``POST /populate-all/{field}``
    Run that PopulateButton on a batch of unfilled working-set rows
    (``args.batch``, default 10); return a progress chip in ``#status-bar``.

``POST /populate-all/{field}/pause``
    Stop the rolling HTMX chain at a batch boundary; chip shows Resume.

``POST /generate-document/{n}`` / ``POST /generate-summary-document/{n}``
    Run ``documents:`` / ``summary_documents:`` generation; return status
    (and a download link when a file was written under the review directory).

``POST /edit-pdf/{n}``
    Ensure ``editpdf[n]`` is copied/extracted; return a download link.

Root-server mode (``app.state.root`` is a directory path)
----------------------------------------------------------
The ``root_router`` mirrors every single-config route but prefixed with a
``{config_path:path}`` segment that maps a URL path to a ``_referia.yml``
under the root directory.  Reviewers are lazily loaded and cached by
``_get_cached_reviewer``.

``GET /``
    When ``{root}/_referia.yml`` exists, the review page for that config
    (CIP-0010).  Otherwise the CIP-000C directory listing of configs under
    the root.  Unprefixed action routes (``/record``, ``/save``, …) serve
    the root config when present.

``GET /{config_path:path}``
    Full page for the named config (last in root_router to act as catch-all).
    ``?index=<value>`` selects that record so listing titles can deep-link
    into a mark sheet.

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

``POST /{config_path:path}/populate-all/{field}``
    On-demand compute for every filtered row.

``POST /{config_path:path}/generate-document/{n}`` (and summary / edit-pdf)
    Document generation actions.

Client-side URL rewriting
--------------------------
``base.html`` injects a ``CONFIG_PATH`` JS constant (empty string in
single-config mode, the config prefix in root mode).  An
``htmx:configRequest`` listener prepends it to all HTMX request paths, so
``render.py`` never needs to know about path prefixes.
"""

from __future__ import annotations

import html
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from referia.assess.web_review import (
    DEFAULT_LIST_PAGE_SIZE,
    WebReviewer,
    listing_window,
)
from referia.web.path_safety import PathOutsideRootError, safe_path_under_root, is_path_under_any_root
from referia.web.render import (
    render_widget,
    render_form,
    render_viewer,
    render_document_panel,
    render_document_actions,
    render_filter_bar,
    render_inline_listing,
    render_viewer_tree,
    iter_spec_leaves,
    populate_all_chrome_html,
    render_populate_progress_chip,
)
from referia.config.inherit_view import (
    inherited_readonly_fields,
    interface_has_parent,
    toggle_html,
    view_options_for_interface,
)

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
    if reviewer is not None:
        return reviewer
    # Root-server: unprefixed routes (``/record``, ``/save``, …) serve
    # ``{root}/_referia.yml`` when present (CIP-0010).
    root = getattr(request.app.state, "root", None)
    if root is not None and (Path(root) / "_referia.yml").exists():
        return _root_reviewer(request, "")
    from fastapi import HTTPException
    raise HTTPException(
        status_code=503,
        detail=(
            "Review session could not be initialised. "
            "Check the server log for startup errors — likely a missing or "
            "malformed _referia.yml, or a data file that could not be loaded."
        ),
    )


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
    try:
        detail = reviewer.get_display_detail_field()
    except Exception:
        detail = None
    if isinstance(detail, str) and detail:
        try:
            data[detail] = reviewer.get_value(detail)
        except Exception:
            pass
    return data


def _find_spec(reviewer, column: str) -> dict | None:
    """Return the first widget spec whose ``field`` matches *column*.

    Skips PopulateButton specs because they share ``field`` with their target
    widget; use :func:`_find_populate_spec` to locate buttons specifically.
    Also skips entries without a renderable widget ``type`` (e.g. compute
    specs that must not steal OOB refreshes from real widgets).
    """
    from referia.web.render import _RENDERERS

    for spec in reviewer.get_widget_specs():
        if spec.get("field") != column:
            continue
        wtype = spec.get("type")
        if wtype == "PopulateButton" or wtype not in _RENDERERS:
            continue
        return spec
    return None


def _populate_button_target(spec: dict) -> str:
    """Return the effective write-target field for a PopulateButton spec.

    Handles both formats:
    * Simple: top-level ``field`` key.
    * Complex: ``args.target`` or ``args.compute.field``.

    ``args.target`` takes priority because the top-level ``field`` may be a
    button identifier.  When ``compute.field`` is a list, never return the
    list — fall back to the button id / first column.
    """
    args = spec.get("args", {})
    target = args.get("target")
    if target:
        return str(target)
    compute_field = args.get("compute", {}).get("field")
    if isinstance(compute_field, list):
        return str(spec.get("field") or (compute_field[0] if compute_field else ""))
    if compute_field:
        return str(compute_field)
    return str(spec.get("field") or "")


def _populate_button_route_key(spec: dict) -> str:
    """Match POST /populate/{key} to a button (prefer unique button ``field``)."""
    own = spec.get("field")
    if own:
        return str(own)
    return _populate_button_target(spec)


def _find_populate_spec(reviewer, field: str) -> dict | None:
    """Return the PopulateButton for *field* (button id or write target).

    Prefer an exact match on the button's own ``field`` so Propose / Undo can
    share a multi-output write target.  Fall back to write-target match for
    simple YAML where ``field`` is the populate column.
    """
    key = str(field)
    by_id = None
    by_target = None
    for spec in reviewer.get_widget_specs():
        if spec.get("type") != "PopulateButton":
            continue
        if _populate_button_route_key(spec) == key:
            by_id = spec
            break
        if by_target is None and _populate_button_target(spec) == key:
            by_target = spec
    return by_id or by_target


def _find_oob_spec(reviewer, column: str) -> dict | None:
    """Return a renderable widget or PopulateButton whose ``field`` is *column*.

    Used for ``visible_if`` OOB refreshes: Confirm/Undo buttons are keyed by
    their own field (``_confirm_split``), not by ``args.target``.
    """
    spec = _find_spec(reviewer, column)
    if spec is not None:
        return spec
    for btn in reviewer.get_widget_specs():
        if btn.get("type") != "PopulateButton":
            continue
        if btn.get("field") == column:
            return btn
    return None


def _list_document_entries(reviewer, section: str) -> list:
    """Return document action specs, tolerating mocks without the method."""
    list_docs = getattr(reviewer, "list_document_entries", None)
    if not callable(list_docs):
        return []
    try:
        result = list_docs(section)
    except Exception as exc:
        log.debug("list_document_entries(%r) failed: %s", section, exc)
        return []
    return result if isinstance(result, list) else []


def _parse_list_query(request: Request | None) -> dict[str, Any]:
    """Read CIP-0020 ``list_offset`` / ``list_page`` / ``list_page_size``."""
    out: dict[str, Any] = {"offset": 0, "page": None, "page_size": None}
    if request is None:
        return out

    def _int(name: str) -> int | None:
        raw = request.query_params.get(name)
        if raw is None or raw == "":
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    page = _int("list_page")
    offset = _int("list_offset")
    size = _int("list_page_size")
    if offset is not None and offset < 0:
        offset = 0
    if size is not None and size < 0:
        size = None
    out["page"] = page
    out["offset"] = offset or 0
    out["page_size"] = size
    return out


def _window_for_reviewer(
    reviewer,
    request: Request | None = None,
    *,
    reset: bool = False,
) -> dict[str, Any]:
    """Return the CIP-0020 listing window for *reviewer*."""
    try:
        working = list(reviewer.working_indices())
    except Exception:
        working = list(reviewer.index_list())
    parsed = {"offset": 0, "page": None, "page_size": None}
    if reset and isinstance(reviewer, WebReviewer):
        reviewer.clear_list_window()
    elif request is not None:
        parsed = _parse_list_query(request)
        if isinstance(reviewer, WebReviewer):
            reviewer.remember_list_query(parsed)
    elif isinstance(reviewer, WebReviewer):
        parsed = reviewer.list_query()
    page_size = DEFAULT_LIST_PAGE_SIZE
    paging = "append"
    if isinstance(reviewer, WebReviewer):
        page_size = reviewer.get_list_page_size(parsed.get("page_size"))
        paging = reviewer.get_list_paging()
    else:
        if parsed.get("page_size") is not None:
            page_size = int(parsed["page_size"])
        get_paging = getattr(reviewer, "get_list_paging", None)
        if callable(get_paging):
            raw = get_paging()
            if raw in ("append", "page"):
                paging = raw
    return listing_window(
        working,
        page_size=page_size,
        offset=parsed.get("offset") or 0,
        page=parsed.get("page"),
        paging=paging,
    )


def _collect_listing_entries(reviewer, indices, prefix: str) -> list[dict]:
    """Walk *indices* (not the whole working set) into listing row dicts."""
    filter_state = reviewer.get_filter_state()
    group_by = _inline_list_group_by(filter_state)
    listing_entries: list[dict] = []
    saved = None
    try:
        saved = reviewer.get_index()
    except Exception:
        saved = None
    try:
        for idx in indices:
            reviewer.set_index(idx)
            data = _current_data(reviewer)
            listing_entries.append(
                {
                    "index": idx,
                    "data": data,
                    "href": _inline_list_href(reviewer, data, prefix),
                    "group": _inline_list_group(
                        reviewer, data, group_by=group_by
                    ),
                }
            )
    finally:
        if saved is not None:
            try:
                reviewer.set_index(saved)
            except Exception:
                pass
    return listing_entries


def _panel_response_context(
    reviewer, prefix: str = "", *, request: Request | None = None
) -> dict:
    """Build the shared template context dict for ``review_panel.html``.

    Used by single-config and root-mode routes so the panel-rendering logic
    lives in exactly one place.  *prefix* is prepended to PDF iframe URLs in
    root-server mode.
    """
    indices = reviewer.index_list()
    current_index = reviewer.get_index()
    try:
        layout = reviewer.get_display_layout()
    except ValueError as exc:
        log.error("Invalid display.layout: %s", exc)
        layout = "side_by_side"

    view_options = view_options_for_interface(getattr(reviewer, "_interface", None))
    viewer_specs = reviewer.get_viewer_specs(view_options=view_options)
    viewer_index = 0
    try:
        viewer_row = _current_data(reviewer)
    except Exception:
        viewer_row = {}

    def _viewer_leaf(spec: dict) -> str:
        nonlocal viewer_index
        html_block = reviewer.render_viewer_html(spec, viewer_index=viewer_index)
        viewer_index += 1
        return html_block

    viewer_blocks = render_viewer_tree(
        viewer_specs, _viewer_leaf, data=viewer_row
    )
    needs_plotly = any(
        (spec.get("type") if isinstance(spec, dict) else None) == "PlotlyFigure"
        for spec in iter_spec_leaves(viewer_specs)
    )
    inherit_view_toggle_html = ""
    if interface_has_parent(getattr(reviewer, "_interface", None)):
        inherit_view_toggle_html = toggle_html(
            view_options, index=current_index
        )

    row_forms: list[dict] = []
    listing_html = ""
    form_html = ""
    filter_bar_html = ""
    working = indices
    row_data: dict = {}
    if layout == "inline_list":
        window = _window_for_reviewer(reviewer, request)
        working_count = int(window.get("working_count") or 0)
        filter_state = reviewer.get_filter_state()
        group_by = _inline_list_group_by(filter_state)
        filter_bar_html = render_filter_bar(
            reviewer.get_filter_specs(),
            reviewer.get_sort_specs(),
            filter_state,
        )
        review_specs = reviewer.get_review_specs(view_options=view_options)
        listing_entries = _collect_listing_entries(
            reviewer, window["page_indices"], prefix
        )
        listing_html = render_inline_listing(
            listing_entries,
            review_specs,
            group_by=group_by,
            detail_field=reviewer.get_display_detail_field(),
            documents=_list_document_entries(reviewer, "documents"),
            working_count=working_count,
            window=window,
        )
        index_selector = ""
        document_html = ""
        position = working_count
        total = working_count
        try:
            row_data = _current_data(reviewer)
        except Exception:
            row_data = {}
        document_actions_html = render_document_actions(
            summary_documents=_list_document_entries(
                reviewer, "summary_documents"
            ),
            data=row_data,
        )
    else:
        row_data = _current_data(reviewer)
        review_specs = reviewer.get_review_specs(view_options=view_options)
        form_html = populate_all_chrome_html(
            review_specs, count=len(indices)
        ) + render_form(review_specs, row_data)
        index_selector = _render_index_selector(indices, current_index)
        document_html = render_document_panel(
            reviewer.list_pdf_entries(),
            reviewer.list_url_entries(),
            prefix,
            current_index=current_index,
            data=row_data,
        )
        position = (
            (indices.index(current_index) + 1) if current_index in indices else "?"
        )
        total = len(indices)
        document_actions_html = render_document_actions(
            documents=_list_document_entries(reviewer, "documents"),
            summary_documents=_list_document_entries(
                reviewer, "summary_documents"
            ),
            data=row_data,
        )

    return {
        "layout": layout,
        "index_selector": index_selector,
        "filter_bar_html": filter_bar_html,
        "viewer_blocks": viewer_blocks,
        "document_html": document_html,
        "document_actions_html": document_actions_html,
        "form_html": form_html,
        "row_forms": row_forms,
        "listing_html": listing_html,
        "current_index": current_index,
        "total": total,
        "position": position,
        "needs_plotly": needs_plotly,
        "inherit_view_toggle_html": inherit_view_toggle_html,
    }


def _inline_list_href(reviewer, data: dict, prefix: str = "") -> str | None:
    """Best-effort link into a discovered child review config.

    ``config_url`` / ``url`` on the row win, including query strings such as
    ``?index=<crsid>`` so a summary listing can open that student's mark sheet.
    """
    for key in ("config_url", "configUrl", "url"):
        raw = data.get(key)
        if raw:
            return str(raw)
    src = data.get("sourceDirectory")
    if not src:
        return None
    try:
        base = Path(getattr(reviewer, "_directory", ".")).resolve()
        rel = Path(src).expanduser().resolve().relative_to(base)
    except (OSError, ValueError):
        return None
    rel_url = str(rel).replace("\\", "/").strip("/")
    if not rel_url:
        return None
    # Root-server: prefix is the overview config path; child is a sibling URL.
    if prefix:
        parent = prefix.rstrip("/").rsplit("/", 1)[0] if "/" in prefix.rstrip("/") else ""
        root_prefix = f"{parent}/{rel_url}" if parent else f"/{rel_url}"
        if not root_prefix.startswith("/"):
            root_prefix = "/" + root_prefix
        return root_prefix.rstrip("/") + "/"
    return f"/{rel_url}/"


_INLINE_LIST_GROUP_BY = frozenset({"directory", "version", "month", "none"})


def _inline_list_group_by(filter_state: dict | None) -> str:
    """Return the active inline_list group-by mode (default ``directory``)."""
    raw = (filter_state or {}).get("_group") or "directory"
    key = str(raw).strip().lower()
    return key if key in _INLINE_LIST_GROUP_BY else "directory"


def _inline_list_group(
    reviewer, data: dict, *, group_by: str = "directory"
) -> str:
    """Group label for listing sections.

    ``directory`` (default): top-level path under the review root (CIP-000C).
    ``version``: ``referia_config_version`` as ``v1`` / ``v2`` / ``unknown``.
    ``month``: ``YYYY-MM`` from ``when`` (ISO or YYYYMMDD); empty if unparseable.
    ``none``: flat listing (empty group label).
    """
    mode = group_by if group_by in _INLINE_LIST_GROUP_BY else "directory"
    if mode == "none":
        return ""
    if mode == "month":
        return _month_group_from_when(data.get("when"))
    if mode == "version":
        raw = data.get("referia_config_version")
        if raw is None or raw == "":
            raw = data.get("version")
        if raw is None or raw == "":
            return "unknown"
        text = str(raw).strip()
        if text.lower().startswith("v") and text[1:].isdigit():
            return text.lower()
        if text.isdigit():
            return f"v{text}"
        return text

    src = data.get("sourceDirectory")
    if not src:
        return ""
    src_path = Path(str(src)).expanduser()
    try:
        base = Path(getattr(reviewer, "_directory", ".")).resolve()
        if src_path.is_absolute():
            abs_src = src_path.resolve()
        else:
            abs_src = (base / src_path).resolve()
        rel = abs_src.relative_to(base)
    except (OSError, ValueError):
        parts = [p for p in src_path.parts if p not in (".", "")]
        if len(parts) > 1:
            return str(parts[0])
        return ""
    parts = list(rel.parts)
    if len(parts) <= 1:
        return ""
    return str(parts[0])


def _month_group_from_when(value) -> str:
    """Return ``YYYY-MM`` from a catalog ``when`` cell, or ``""`` if unparseable.

    DatePicker stores ``YYYYMMDD``; compute ``today`` is ISO ``YYYY-MM-DD``.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return ""
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 6:
        year, month = digits[:4], digits[4:6]
        if year.isdigit() and month.isdigit() and 1 <= int(month) <= 12:
            return f"{year}-{month}"
    return ""


def _render_panel(reviewer, request: Request, prefix: str = "") -> str:
    """Render the full review panel as an HTML string."""
    ctx = _panel_response_context(reviewer, prefix, request=request)
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
        '        hx-swap="innerHTML focus-scroll:false">\n'
        f"{options}\n"
        "</select>"
    )


def _esc(value: Any) -> str:
    return html.escape(str(value) if value is not None else "")


def _inherited_field_is_readonly(reviewer, column: str) -> bool:
    """CIP-0018: stacked ancestor review is not writable via query or POST."""
    interface = getattr(reviewer, "_interface", None)
    options = view_options_for_interface(interface)
    return str(column) in inherited_readonly_fields(interface, options)


def _user_error_html(action: str) -> str:
    """Generic browser-facing error; details belong in the server log (CIP-000E)."""
    return (
        f'<span class="status-error">&#10007; {_esc(action)} failed. See server log.</span>'
    )


def _apply_field_bulk(reviewer, column: str, value: Any) -> None:
    """Write *column* once for parameters, else on every working-set row."""
    data = getattr(reviewer, "_data", None)
    isparameter = getattr(data, "isparameter", None)
    ismutable = getattr(data, "ismutable", None)
    if callable(isparameter) and callable(ismutable):
        try:
            if isparameter(column) is True and ismutable(column) is True:
                reviewer.set_value(column, value)
                return
        except Exception:
            pass
    saved = None
    try:
        saved = reviewer.get_index()
    except Exception:
        pass
    try:
        for idx in reviewer.working_indices():
            reviewer.set_index(idx)
            reviewer.set_value(column, value)
    finally:
        if saved is not None:
            try:
                reviewer.set_index(saved)
            except Exception:
                pass


def _panel_with_oob_status(templates, request, ctx: dict, status_html: str) -> HTMLResponse:
    """Review panel plus an OOB swap into ``#status-bar``."""
    panel = templates.TemplateResponse(request, "review_panel.html", ctx)
    body = panel.body
    if isinstance(body, (bytes, bytearray, memoryview)):
        text = bytes(body).decode("utf-8")
    else:
        text = str(body)
    oob = (
        f'<div id="status-bar" class="status-bar" hx-swap-oob="true">'
        f"{status_html}</div>"
    )
    return HTMLResponse(text + oob)


_BROWSER_ERROR_HINT = "See server log."
_PARSE_FAIL_TOOLTIP = "Failed to parse. See server log."

# Fixed catalog only (CIP-000E): never interpolate str(exc) or filesystem paths.
_LOAD_FAIL_GENERIC = "Could not load config. See server log and /errors."
_LOAD_FAIL_PATH_ESCAPE = (
    "Could not load config: a configured data path is outside the "
    "allowed serve roots. See server log and /errors."
)


def _load_failure_detail(exc: BaseException) -> str:
    """Browser-facing load-failure text keyed by exception type only.

    Must return fixed catalog strings — never ``str(exc)`` — so PathEscape
    path/root lists stay in the server log (CIP-000E).
    """
    if type(exc).__name__ == "PathEscapeError":
        return _LOAD_FAIL_PATH_ESCAPE
    return _LOAD_FAIL_GENERIC


def _load_failure_hint_for_type(exc_type_name: str) -> str:
    """Same catalog as :func:`_load_failure_detail`, keyed by type name."""
    if exc_type_name == "PathEscapeError":
        return _LOAD_FAIL_PATH_ESCAPE
    return _BROWSER_ERROR_HINT


def _log_route_error(action: str, exc: Exception, **context: Any) -> None:
    extra = " ".join(f"{k}={v!r}" for k, v in context.items())
    log.exception("%s failed %s", action, extra)


def _make_oob(widget_html: str) -> str:
    """Add ``hx-swap-oob="true"`` to the outermost widget container div."""
    return widget_html.replace(
        'class="widget-container"',
        'class="widget-container" hx-swap-oob="true"',
        1,
    )


def _make_viewer_oob(viewer_html: str) -> str:
    """Add ``hx-swap-oob="true"`` to an interactive viewer container.

    Matches ``viewer-plotly`` / ``viewer-image`` / ``viewer-chrome`` even when
    extra classes (e.g. ``viewer-plotly--fill``) are present.
    """
    import re

    def _inject(match: re.Match[str]) -> str:
        attrs = match.group(1)
        if "hx-swap-oob=" in attrs:
            return match.group(0)
        return f"<div{attrs} hx-swap-oob=\"true\">"

    updated, n = re.subn(
        r"<div(\s+[^>]*\bviewer-(?:plotly|image|chrome|markdown|html)\b[^>]*)>",
        _inject,
        viewer_html,
        count=1,
    )
    return updated if n else viewer_html


# Catalogue / intro liquid that must re-render when topic naming or splits land.
_LIQUID_VIEWER_WATCH = frozenset(
    {
        "topic_labels",
        "topic_keys",
        "topic_parent",
        "topic_tree",
        "pending_proposal",
        "focus_topic",
    }
)


def _liquid_viewer_watch_columns(spec: dict) -> set[str]:
    """Columns that should OOB-refresh this liquid / Markdown viewer.

    Config (on a ``viewer:`` entry)::

        watch: [units]
        field: units   # same meaning as a one-item watch list
    """
    cols: set[str] = set()
    field = spec.get("field")
    if field not in (None, "", "_"):
        cols.add(str(field))
    watch = spec.get("watch")
    if isinstance(watch, str) and watch:
        cols.add(watch)
    elif isinstance(watch, (list, tuple, set)):
        cols.update(str(item) for item in watch if item not in (None, "", "_"))
    return cols


def _viewer_highlight_oobs(reviewer, column: str) -> list[str]:
    """OOB fragments for viewers watching *column* (highlight or figure_source).

    PlotlyFigure updates swap only the JSON ``plotly-spec`` script so the
    live graph is restyled in place (avoids a full remount / size flash).
    Viewer-chrome widgets replace their container when field/options change.
    Liquid intro blocks re-render when topic catalogue columns change so
    named labels replace raw ``T0`` keys without a full page reload, and
    when the entry declares ``watch:`` / ``field:`` (e.g. Segment → units).
    ``visible_if`` dependents re-render the whole viewer container so
    ``display:none`` can toggle after a Present-flag write.
    """
    from referia.assess.viewer_bindings import (
        apply_highlight,
        apply_plotly_size,
        figure_source_binding,
        highlight_binding,
        is_liquid_viewer,
        is_viewer_chrome_type,
        parse_figure_spec,
        plotly_size_options,
        resolve_figure_payload,
        viewer_entry_type,
    )
    from referia.assess.web_review import _visible_if_depends_on
    from referia.web.render import render_plotly_spec_oob

    parts: list[str] = []
    for i, spec in enumerate(iter_spec_leaves(reviewer.get_viewer_specs())):
        if _visible_if_depends_on(spec.get("visible_if"), column):
            html = reviewer.render_viewer_html(spec, viewer_index=i)
            parts.append(_make_viewer_oob(html))
            continue
        if is_viewer_chrome_type(spec):
            field = spec.get("field")
            args = spec.get("args") or {}
            opts_field = args.get("options_field")
            labels_field = args.get("options_labels_field")
            if column not in (field, opts_field, labels_field):
                continue
            html = reviewer.render_viewer_html(spec, viewer_index=i)
            parts.append(_make_viewer_oob(html))
            continue
        if is_liquid_viewer(spec) and (
            column in _LIQUID_VIEWER_WATCH
            or column in _liquid_viewer_watch_columns(spec)
        ):
            html = reviewer.render_viewer_html(spec, viewer_index=i)
            parts.append(_make_viewer_oob(html))
            continue
        if viewer_entry_type(spec) != "PlotlyFigure":
            continue
        watch = False
        hl = highlight_binding(spec)
        if hl and hl["from_field"] == column:
            watch = True
        src = figure_source_binding(spec)
        if src and column in (src["key_field"], src["map_field"]):
            watch = True
        field = spec.get("field")
        if field and str(field) == column:
            watch = True
        if not watch:
            continue
        raw = resolve_figure_payload(reviewer.get_value, spec)
        try:
            selected = reviewer.get_value(hl["from_field"]) if hl else None
        except Exception:
            selected = None
        fig = apply_highlight(
            parse_figure_spec(raw),
            selected=selected,
            mode=(hl or {}).get("mode", "default"),
        )
        size_opts = plotly_size_options(spec)
        fig = apply_plotly_size(fig, mode=size_opts.get("mode", "figure"))
        parts.append(render_plotly_spec_oob(i, fig))
    return parts


def _field_update_oob_parts(
    reviewer,
    column: str,
    *,
    data: dict,
    record_index: Any = None,
    source: Any = None,
) -> list[str]:
    """OOB widget / viewer fragments after a field write."""
    parts: list[str] = []
    oob_index = record_index if record_index not in (None, "") else None
    for col in reviewer.affected_widgets(column):
        if col == column:
            continue
        affected_spec = _find_oob_spec(reviewer, col)
        if affected_spec:
            try:
                val = reviewer.get_value(col)
            except Exception:
                val = None
            widget_html = render_widget(
                affected_spec, val, data, record_index=oob_index
            )
            parts.append(_make_oob(widget_html))
    if source == "viewer":
        trigger_spec = _find_spec(reviewer, column)
        if trigger_spec:
            widget_html = render_widget(
                trigger_spec,
                reviewer.get_value(column),
                data,
                record_index=oob_index,
            )
            parts.append(_make_oob(widget_html))
    parts.extend(_viewer_highlight_oobs(reviewer, column))
    parts.append(_document_actions_oob(reviewer, data))
    return parts


def _document_actions_oob(reviewer, data: dict) -> str:
    """Render nav document buttons with OOB swap for visibility updates.

    On ``inline_list`` layouts, per-record documents live on listing rows, so
    the nav OOB target only carries ``summary_documents``.
    """
    try:
        layout = reviewer.get_display_layout()
    except Exception:
        layout = "side_by_side"
    if layout == "inline_list":
        html = render_document_actions(
            summary_documents=_list_document_entries(
                reviewer, "summary_documents"
            ),
            data=data,
        )
    else:
        html = render_document_actions(
            documents=_list_document_entries(reviewer, "documents"),
            summary_documents=_list_document_entries(
                reviewer, "summary_documents"
            ),
            data=data,
        )
    if not html:
        # Keep a stable target so buttons can reappear after becoming visible.
        html = '<div class="nav-document-actions" id="nav-document-actions"></div>'
    return html.replace(
        'id="nav-document-actions"',
        'id="nav-document-actions" hx-swap-oob="true"',
        1,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    after: str | None = None,
    before: str | None = None,
    current: str | None = None,
    index: str | None = None,
):
    """Render the full review page for the current record.

    In root-server mode (``app.state.root`` is set): when ``{root}/_referia.yml``
    exists, load it like any other config (CIP-0010).  Otherwise fall back to
    the CIP-000C directory listing.  Listing query params ``after``, ``before``
    and ``current`` apply only to that fallback; current-only is on by default
    (pass ``current=0`` to show all).

    ``?index=`` selects a record when a review page is served (not the
    directory listing).
    """
    if getattr(request.app.state, "root", None) is not None:
        from fastapi import HTTPException as _HTTPException

        try:
            reviewer = _root_reviewer(request, "")
        except _HTTPException as exc:
            if exc.status_code == 404:
                current_only = _current_only_from_param(current)
                configs = _list_sub_configs(request.app.state.root, "")
                configs = _filter_configs(
                    configs, after=after, before=before, current_only=current_only
                )
                return _render_directory_listing(
                    "", configs, after=after, before=before, current_only=current_only
                )
            raise

        _apply_index(reviewer, index)
        ctx = _panel_response_context(reviewer, "", request=request)
        return _templates(request).TemplateResponse(
            request,
            "base.html",
            {
                "title": "Referia",
                "config": "_referia.yml",
                "directory": (
                    reviewer._directory
                    if hasattr(reviewer, "_directory")
                    else request.app.state.root
                ),
                "cache_bust": request.app.state.start_time,
                "config_path_prefix": "",
                **ctx,
            },
        )

    reviewer = _reviewer(request)
    _apply_index(reviewer, index)
    ctx = _panel_response_context(reviewer, request=request)
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


def _apply_index(reviewer, index: str | None) -> None:
    """Set *index* on *reviewer*, mapping missing labels to HTTP 404."""
    if index is None:
        return
    from fastapi import HTTPException

    try:
        reviewer.set_index(index)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Index not found") from exc


@router.get("/record", response_class=HTMLResponse)
async def get_record(request: Request, index: str | None = None):
    """Return the review-panel HTML fragment for *index* (HTMX partial swap).

    Called by the index ``<select>`` via HTMX. The response replaces the
    ``#review-panel`` div's inner HTML.
    """
    reviewer = _reviewer(request)
    _apply_index(reviewer, index)
    ctx = _panel_response_context(reviewer, request=request)
    return _templates(request).TemplateResponse(request, "review_panel.html", ctx)


@router.get("/listing-page", response_class=HTMLResponse)
async def listing_page(request: Request):
    """CIP-0020 fragment: next append chunk or replacement paged rows."""
    reviewer = _reviewer(request)
    try:
        layout = reviewer.get_display_layout()
    except Exception:
        layout = "side_by_side"
    if layout != "inline_list":
        return HTMLResponse("")
    window = _window_for_reviewer(reviewer, request)
    view_options = view_options_for_interface(getattr(reviewer, "_interface", None))
    filter_state = reviewer.get_filter_state()
    html = render_inline_listing(
        _collect_listing_entries(reviewer, window["page_indices"], ""),
        reviewer.get_review_specs(view_options=view_options),
        group_by=_inline_list_group_by(filter_state),
        detail_field=reviewer.get_display_detail_field(),
        documents=_list_document_entries(reviewer, "documents"),
        working_count=int(window.get("working_count") or 0),
        window=window,
        fragment=True,
    )
    return HTMLResponse(html)


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

    The triggering *column* is never OOB-replaced: the browser already holds
    its value, and replacing it would destroy the control the user just
    focused after blur (CoE 2026-10-18).

    Optional form field ``index`` (from inline_list ``hx-vals``) selects the
    tall-table row to update before writing *column*.
    """
    reviewer = _reviewer(request)
    form = await request.form()
    raw_value = form.get(column)
    record_index = form.get("index")
    log.debug(
        "update_field: column=%r raw_value=%r index=%r form_keys=%s",
        column,
        raw_value,
        record_index,
        list(form.keys()),
    )

    if record_index is not None and str(record_index) != "":
        try:
            reviewer.set_index(record_index)
        except Exception as exc:
            _log_route_error("Update", exc, column=column, index=record_index)
            return HTMLResponse(_user_error_html("Update"))

    if _inherited_field_is_readonly(reviewer, column):
        log.warning("Refusing write to inherited read-only field")
        return HTMLResponse(_user_error_html("Update"))

    spec = _find_spec(reviewer, column)
    value: Any = _coerce_form_value(raw_value, spec)

    try:
        reviewer.set_value(column, value)
        status_html = '<span class="status-ok">&#10003; Updated</span>'
    except Exception as exc:
        _log_route_error("Update", exc, column=column)
        return HTMLResponse(_user_error_html("Update"))

    source = form.get("source")
    data = _current_data(reviewer)
    parts = [status_html]
    parts.extend(
        _field_update_oob_parts(
            reviewer,
            column,
            data=data,
            record_index=record_index,
            source=source,
        )
    )
    return HTMLResponse("\n".join(parts))


@router.post("/field-bulk/{column}", response_class=HTMLResponse)
async def update_field_bulk(request: Request, column: str):
    """Set *column* on all filtered working-set rows; return a refreshed panel."""
    reviewer = _reviewer(request)
    templates = _templates(request)
    form = await request.form()
    raw_value = form.get(column)
    if _inherited_field_is_readonly(reviewer, column):
        log.warning("Refusing bulk write to inherited read-only field")
        ctx = _panel_response_context(reviewer)
        return _panel_with_oob_status(
            templates, request, ctx, _user_error_html("Bulk update")
        )
    spec = _find_spec(reviewer, column)
    value: Any = _coerce_form_value(raw_value, spec)

    try:
        _apply_field_bulk(reviewer, column, value)
    except Exception as exc:
        _log_route_error("Bulk update", exc, column=column)
        ctx = _panel_response_context(reviewer)
        return _panel_with_oob_status(
            templates, request, ctx, _user_error_html("Bulk update")
        )

    ctx = _panel_response_context(reviewer)
    return templates.TemplateResponse(request, "review_panel.html", ctx)


def _parse_filter_form(form, reviewer) -> dict:
    """Build filter_state dict from an HTMX filter-bar form post."""
    state: dict = {}
    for spec in reviewer.get_filter_specs():
        if not isinstance(spec, dict):
            continue
        field = str(spec.get("field") or "")
        if not field:
            continue
        ftype = str(spec.get("type") or "categorical")
        if ftype == "boolean":
            raw = form.get(f"filter__{field}")
            if raw is not None:
                state[field] = str(raw)
        elif ftype == "date_range":
            after = form.get(f"filter__{field}__after") or ""
            before = form.get(f"filter__{field}__before") or ""
            state[field] = {"after": str(after), "before": str(before)}
        elif ftype == "contains":
            query = form.get(f"filter__{field}__query") or ""
            mode = str(form.get(f"filter__{field}__mode") or "words").lower()
            if mode not in ("words", "exact"):
                mode = "words"
            state[field] = {"query": str(query), "mode": mode}
        else:
            # Single-select (Any = empty) or legacy multi-select
            getlist = getattr(form, "getlist", None)
            if callable(getlist):
                vals = getlist(f"filter__{field}")
            else:
                raw = form.get(f"filter__{field}")
                vals = [raw] if raw is not None else []
            cleaned = [str(v) for v in vals if v is not None and str(v) != ""]
            state[field] = cleaned
    sort_val = form.get("sort")
    if sort_val:
        state["_sort"] = str(sort_val)
    group_val = form.get("group")
    if group_val:
        key = str(group_val).strip().lower()
        if key in _INLINE_LIST_GROUP_BY:
            state["_group"] = key
    return state


@router.post("/filters", response_class=HTMLResponse)
async def apply_filters(request: Request):
    """Apply filter/sort bar values and return a refreshed review panel."""
    reviewer = _reviewer(request)
    templates = _templates(request)
    form = await request.form()
    try:
        reviewer.set_filter_state(_parse_filter_form(form, reviewer))
    except Exception as exc:
        _log_route_error("Filters", exc)
        return HTMLResponse(_user_error_html("Filters"))
    _window_for_reviewer(reviewer, reset=True)
    ctx = _panel_response_context(reviewer)
    return templates.TemplateResponse(request, "review_panel.html", ctx)


@router.post("/filters/clear", response_class=HTMLResponse)
async def clear_filters(request: Request):
    """Clear filter/sort session state and return a refreshed review panel."""
    reviewer = _reviewer(request)
    templates = _templates(request)
    try:
        reviewer.clear_filters()
    except Exception as exc:
        _log_route_error("Filters", exc)
        return HTMLResponse(_user_error_html("Filters"))
    _window_for_reviewer(reviewer, reset=True)
    ctx = _panel_response_context(reviewer)
    return templates.TemplateResponse(request, "review_panel.html", ctx)


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
        _log_route_error("Save", exc)
        return HTMLResponse(_user_error_html("Save"))


@router.post("/reload", response_class=HTMLResponse)
async def reload_data(request: Request):
    """Reload data from source files and return a refreshed review panel."""
    reviewer = _reviewer(request)
    templates = _templates(request)

    try:
        reviewer.load_flows(reload=True)
    except Exception as exc:
        _log_route_error("Reload", exc)
        return HTMLResponse(_user_error_html("Reload"))

    ctx = _panel_response_context(reviewer)
    return _panel_with_oob_status(
        templates,
        request,
        ctx,
        '<span class="status-ok">&#10003; Reloaded</span>',
    )


def _apply_form_index(reviewer, form, *, action: str = "Generate document"):
    """Set the reviewer index from an HTMX ``index`` form field, if present."""
    record_index = form.get("index")
    if record_index is None or str(record_index) == "":
        return None
    try:
        reviewer.set_index(record_index)
    except Exception as exc:
        _log_route_error(action, exc, index=record_index)
        return HTMLResponse(_user_error_html(action))
    return None


@router.post("/generate-document/{n}", response_class=HTMLResponse)
async def generate_document(request: Request, n: int):
    """Generate ``documents[n]`` for the current (or form-selected) record."""
    reviewer = _reviewer(request)
    form = await request.form()
    err = _apply_form_index(reviewer, form)
    if err is not None:
        return err
    return _run_generate_document(reviewer, n, summary=False)


@router.post("/generate-summary-document/{n}", response_class=HTMLResponse)
async def generate_summary_document(request: Request, n: int):
    """Generate ``summary_documents[n]`` across all indices."""
    reviewer = _reviewer(request)
    return _run_generate_document(reviewer, n, summary=True)


@router.post("/edit-pdf/{n}", response_class=HTMLResponse)
async def edit_pdf(request: Request, n: int):
    """Ensure ``editpdf[n]`` exists (copy/extract) and return a download link."""
    reviewer = _reviewer(request)
    return _run_edit_pdf(reviewer, n)


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
    form = await request.form()
    err = _apply_form_index(reviewer, form, action="Populate")
    if err is not None:
        return err
    return _run_populate_and_respond(
        reviewer,
        field,
        btn_spec,
        request=request,
        templates=_templates(request),
    )


@router.post("/populate-all/{field}/pause", response_class=HTMLResponse)
async def pause_populate_all(request: Request, field: str):
    """CIP-0021: stop the rolling chain at a batch boundary."""
    reviewer = _reviewer(request)
    btn_spec = _find_populate_spec(reviewer, field)
    if btn_spec is None:
        return HTMLResponse(
            f'<span class="status-warning">&#9888; No PopulateButton found for field {_esc(field)}</span>'
        )
    return _run_populate_all_and_respond(
        reviewer,
        field,
        btn_spec,
        request=request,
        templates=_templates(request),
        paused=True,
    )


@router.post("/populate-all/{field}", response_class=HTMLResponse)
async def populate_all_field(request: Request, field: str):
    """Run a PopulateButton batch on the filtered working set; return a chip."""
    reviewer = _reviewer(request)
    btn_spec = _find_populate_spec(reviewer, field)
    if btn_spec is None:
        return HTMLResponse(
            f'<span class="status-warning">&#9888; No PopulateButton found for field {_esc(field)}</span>'
        )
    return _run_populate_all_and_respond(
        reviewer,
        field,
        btn_spec,
        request=request,
        templates=_templates(request),
    )


def _file_response(path: Path, *, as_attachment: bool = False):
    """Return a FileResponse with a PDF-aware media type.

    When *as_attachment* is true, set ``Content-Disposition: attachment`` so
    the browser downloads rather than navigating/previewing inline.
    """
    import mimetypes

    from fastapi.responses import FileResponse

    media, _ = mimetypes.guess_type(path.name)
    if path.suffix.lower() == ".pdf":
        media = "application/pdf"
    kwargs: dict = {
        "path": str(path),
        "media_type": media or "application/octet-stream",
    }
    if as_attachment:
        kwargs["filename"] = path.name
        kwargs["content_disposition_type"] = "attachment"
    return FileResponse(**kwargs)


def _serve_document_file(request: Request, reviewer, rel_path: str):
    """Serve a generated file from the review directory.

    ``document_download_href`` only exposes paths under the review directory,
    so resolution must use that directory — not the root-server ``--root``
    (which would 404 ``Shumailov_….docx`` at the tree root).
    """
    from fastapi import HTTPException

    root = reviewer._directory
    try:
        resolved = safe_path_under_root(root, rel_path)
    except PathOutsideRootError:
        raise HTTPException(status_code=403, detail="Path outside root rejected")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return _file_response(resolved, as_attachment=True)


def _serve_record_document(
    request: Request,
    reviewer,
    kind: str,
    n: int,
    index: str | None = None,
):
    """Serve the current record's localpdf/editpdf entry *n*.

    When *index* is supplied (from ``?index=`` on the iframe URL), switch to
    that record before resolving the file so each row has a distinct document
    resource identity.
    """
    from fastapi import HTTPException

    if kind not in {"localpdf", "editpdf"}:
        raise HTTPException(status_code=404, detail="Unknown document kind")
    _apply_index(reviewer, index)
    path = reviewer.get_record_document(kind, n)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    allowed = list(reviewer.allowed_roots_for_document(kind, n))
    extra_root = getattr(request.app.state, "root", None)
    if extra_root:
        allowed.append(extra_root)
    allowed.append(reviewer._directory)
    if not is_path_under_any_root(path, allowed):
        raise HTTPException(status_code=403, detail="Path outside root rejected")
    return _file_response(path)


@router.get("/record-document/{kind}/{n}")
async def get_record_document(
    request: Request, kind: str, n: int, index: str | None = None
):
    """Serve one PDF declared in ``localpdf`` / ``editpdf`` for the given record."""
    reviewer = _reviewer(request)
    return _serve_record_document(request, reviewer, kind, n, index)


@router.get("/document/{path:path}")
async def get_document(request: Request, path: str):
    """Serve a file from the review directory (single-config) or server root."""
    reviewer = _reviewer(request)
    return _serve_document_file(request, reviewer, path)


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

    try:
        if clean.endswith(".yml"):
            candidate = safe_path_under_root(root_p, clean)
            user_file = candidate.name
            config_dir = candidate.parent
        elif clean:
            config_dir = safe_path_under_root(root_p, clean)
            user_file = "_referia.yml"
            candidate = config_dir / user_file
        else:
            config_dir = root_p
            user_file = "_referia.yml"
            candidate = config_dir / user_file
    except PathOutsideRootError:
        raise HTTPException(status_code=400, detail="Path outside root rejected")

    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Config not found")

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
        log.exception("Config not accessible: %s", config_file)
        raise HTTPException(status_code=404, detail="Config not accessible") from exc

    cached = app_state.reviewer_cache.get(key)
    if cached is None or cached[0] != mtime:
        from referia.assess.web_review import WebReviewer
        try:
            # Widen the CIP-000A jail to the serve root (sibling data under
            # --root, e.g. theses/criteria/) without unbounded_paths.
            extra_roots = []
            root = getattr(app_state, "root", None)
            if root:
                extra_roots.append(str(root))
            reviewer = WebReviewer(
                user_file,
                str(config_file.parent),
                allowed_roots=extra_roots or None,
            )
        except Exception as exc:
            log.exception("Failed to load config %s", config_file)
            # Record in the in-memory error registry (if it exists on app_state).
            # Do not store str(exc): the registry feeds /errors HTML (CIP-000E / CodeQL #21).
            load_errors = getattr(app_state, "load_errors", None)
            if load_errors is not None:
                import time as _time
                load_errors.append({
                    "path": str(config_file),
                    "type": type(exc).__name__,
                    "time": _time.strftime("%Y-%m-%d %H:%M:%S"),
                })
            raise HTTPException(
                status_code=503, detail=_load_failure_detail(exc)
            ) from exc
        app_state.reviewer_cache[key] = (mtime, reviewer)

    return app_state.reviewer_cache[key][1]


def _root_reviewer(request: Request, config_path: str):
    """Resolve and return the ``WebReviewer`` for a root-mode request."""
    config_file, user_file = _resolve_config_path(
        request.app.state.root, config_path
    )
    return _get_cached_reviewer(request.app.state, config_file, user_file)


def _read_config_meta(yml_path: Path) -> dict:
    """Return display metadata from a ``_referia.yml`` without loading WebReviewer.

    Extracts ``title``, ``description``, ``date``, ``current``, and
    ``inherit_abs`` via ``yaml.safe_load``.  Any parse error logs the exception
    and returns ``{"_error": True}`` so a bad yml never breaks the listing page
    and exception text never reaches the browser (CIP-000E).

    ``date`` is normalised to an ISO-format string (``"YYYY-MM-DD"``).
    ``current`` is coerced to a plain Python ``bool``.
    ``inherit_abs`` is the resolved absolute ``Path`` of the inherited config
    directory, or ``None`` if no ``inherit`` section is present.
    """
    try:
        import yaml  # type: ignore[import]
        with open(yml_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            return {}
        raw_date = data.get("date")
        date_str: str | None = None
        if raw_date is not None:
            try:
                import datetime
                if isinstance(raw_date, (datetime.date, datetime.datetime)):
                    date_str = raw_date.strftime("%Y-%m-%d")
                else:
                    # Validate it looks like a date string.
                    datetime.date.fromisoformat(str(raw_date))
                    date_str = str(raw_date)
            except (ValueError, TypeError):
                pass

        inherit_abs: Path | None = None
        raw_inherit = data.get("inherit")
        if isinstance(raw_inherit, dict):
            rel_dir = raw_inherit.get("directory")
            if rel_dir:
                try:
                    inherit_abs = (yml_path.parent / str(rel_dir)).resolve()
                except Exception:
                    pass

        return {
            "title": data.get("title") or data.get("name"),
            "description": data.get("description"),
            "date": date_str,
            "current": bool(data.get("current", False)),
            "inherit_abs": inherit_abs,
        }
    except Exception as exc:
        log.warning("Failed to parse config %s: %s", yml_path, exc)
        return {"_error": True}


def _list_sub_configs(root: str, url_path: str) -> list[dict]:
    """Return all ``_referia.yml`` configs under *url_path* grouped for display.

    Each entry contains:

    * ``url``         — root-relative URL with trailing slash (links to the review)
    * ``label``       — display label (path relative to the immediate group dir)
    * ``title``       — human-readable title from ``_referia.yml``, or leaf name
    * ``description`` — short description, or ``None``
    * ``date``        — ISO date string from ``_referia.yml``, or ``None``
    * ``current``     — bool from ``_referia.yml`` ``current`` field
    * ``group``       — name of the immediate child of *search_base* (section key)
    * ``group_url``   — root-relative URL with trailing slash for the group dir
    """
    root_path = Path(root).resolve()
    clean = url_path.strip("/")
    try:
        search_base = safe_path_under_root(root_path, clean) if clean else root_path
    except PathOutsideRootError:
        return []
    if not search_base.is_dir():
        return []

    configs = []
    for yml in sorted(search_base.rglob("_referia.yml")):
        try:
            rel_from_root = yml.parent.relative_to(root_path)
            rel_from_base = yml.parent.relative_to(search_base)
        except ValueError:
            continue

        parts = rel_from_base.parts
        if parts:
            group_name = parts[0]
            group_abs = search_base / parts[0]
            label = str(Path(*parts[1:])) if len(parts) > 1 else parts[0]
        else:
            group_name = ""
            group_abs = search_base
            label = yml.parent.name

        try:
            group_rel_from_root = group_abs.relative_to(root_path)
            group_url = "/" + str(group_rel_from_root) + "/"
        except ValueError:
            group_url = "/"

        meta = _read_config_meta(yml)
        configs.append({
            "url": "/" + str(rel_from_root) + "/",
            "label": label,
            "title": meta.get("title") or yml.parent.name,
            "description": meta.get("description"),
            "date": meta.get("date"),
            "current": meta.get("current", False),
            "group": group_name,
            "group_url": group_url,
            "_inherit_abs": meta.get("inherit_abs"),  # resolved Path or None
            "error": bool(meta.get("_error")),
            "yml_path": str(yml),
        })

    # Resolve inherit_abs → root-relative URL and inherit_title.
    url_to_config = {c["url"]: c for c in configs}
    for c in configs:
        inherit_abs = c.pop("_inherit_abs", None)
        inherit_url: str | None = None
        inherit_title: str | None = None
        if inherit_abs is not None:
            try:
                inherit_rel = inherit_abs.relative_to(root_path)
                inherit_url = "/" + str(inherit_rel) + "/"
                parent_cfg = url_to_config.get(inherit_url)
                if parent_cfg:
                    inherit_title = parent_cfg.get("title")
            except ValueError:
                # Parent is outside the root tree — keep inherit_url as None
                # but record that it exists (so we can show a plain label).
                try:
                    inherit_title = inherit_abs.name
                except Exception:
                    pass
        c["inherit_url"] = inherit_url
        c["inherit_title"] = inherit_title

    return configs


def _topo_sort_group(entries: list[dict]) -> list[dict]:
    """Return *entries* with parents before their children (topological order).

    Entries that form no parent-child relationship keep their original order.
    Cycles (unlikely but possible with hand-edited YAMLs) are broken by
    skipping already-visited nodes.
    """
    url_set = {e["url"] for e in entries}
    url_to_entry = {e["url"]: e for e in entries}
    result: list[dict] = []
    visited: set[str] = set()

    def visit(url: str) -> None:
        if url in visited:
            return
        visited.add(url)
        e = url_to_entry.get(url)
        if e is None:
            return
        parent_url = e.get("inherit_url")
        if parent_url and parent_url in url_set:
            visit(parent_url)
        result.append(e)

    for e in entries:
        visit(e["url"])

    return result


def _inherit_depth(url: str, url_set: set, url_to_inherit: dict, _seen: set | None = None) -> int:
    """Return how many ancestors within *url_set* this entry has (chain depth)."""
    if _seen is None:
        _seen = set()
    if url in _seen:
        return 0  # cycle guard
    _seen.add(url)
    parent = url_to_inherit.get(url)
    if parent and parent in url_set:
        return 1 + _inherit_depth(parent, url_set, url_to_inherit, _seen)
    return 0


def _current_only_from_param(current: str | None) -> bool:
    """Resolve the Current-only listing filter from the ``current`` query param.

    Defaults to on when the param is absent so root listings focus on
    work-in-progress.  Pass ``current=0`` to show all configs.
    """
    return current != "0"


def _filter_configs(
    configs: list[dict],
    *,
    after: str | None = None,
    before: str | None = None,
    current_only: bool = False,
) -> list[dict]:
    """Return only those configs matching the supplied filter criteria.

    * ``after``        — include configs whose ``date`` >= this ISO string
    * ``before``       — include configs whose ``date`` <= this ISO string
    * ``current_only`` — if ``True``, include only configs where ``current`` is truthy

    Configs with no ``date`` field pass through date filters unchanged (we
    cannot exclude what we cannot measure).
    """
    import datetime

    result = []
    for c in configs:
        if current_only and not c.get("current"):
            continue
        cfg_date_str = c.get("date")
        if cfg_date_str:
            try:
                cfg_date = datetime.date.fromisoformat(cfg_date_str)
                if after:
                    if cfg_date < datetime.date.fromisoformat(after):
                        continue
                if before:
                    if cfg_date > datetime.date.fromisoformat(before):
                        continue
            except ValueError:
                pass  # malformed date — let it through
        result.append(c)
    return result


def _render_directory_listing(
    url_path: str,
    configs: list[dict],
    *,
    after: str | None = None,
    before: str | None = None,
    current_only: bool = False,
) -> HTMLResponse:
    """Return an HTML directory-listing page with sections grouped by subdirectory.

    Includes a ``..`` navigation link (except at the root), a filter form for
    date range and current-only filtering, and renders title, date, and
    description for each config.
    """
    breadcrumb = url_path.strip("/")
    page_title = breadcrumb or "Referia"

    # ── Parent (up-one) link ────────────────────────────────────────────────
    if breadcrumb:
        parts = breadcrumb.split("/")
        parent = "/" + "/".join(parts[:-1]) + "/" if len(parts) > 1 else "/"
        up_link = f'<p class="up"><a href="{html.escape(parent, quote=True)}">&uarr; ..</a></p>'
    else:
        up_link = ""

    # ── Error banner (shown only when there are parse failures) ─────────────
    error_count = sum(1 for c in configs if c.get("error"))
    if error_count:
        error_banner = (
            f'<p class="error-banner">'
            f'&#x26A0;&#xFE0F;&nbsp;{error_count} config(s) failed to parse. '
            f'<a href="/errors">View errors &rarr;</a>'
            f'</p>'
        )
    else:
        error_banner = ""

    # ── Filter form ─────────────────────────────────────────────────────────
    after_val = _esc(after or "")
    before_val = _esc(before or "")
    current_checked = ' checked' if current_only else ''
    # Checkbox before hidden so a checked submit sends current=1 first
    # (FastAPI takes the first value).  Unchecked sends only current=0.
    # Clear resets dates but leaves Current on (default when param absent).
    filter_form = f"""<form class="filters" method="get">
  <label>After&nbsp;<input type="date" name="after" value="{after_val}"></label>
  <label>Before&nbsp;<input type="date" name="before" value="{before_val}"></label>
  <label><input type="checkbox" name="current" value="1"{current_checked}> Current only</label>
  <input type="hidden" name="current" value="0">
  <button type="submit">Filter</button>
  <a class="clear" href="?">Clear</a>
</form>"""

    # ── Group and render entries ─────────────────────────────────────────────
    groups: dict[str, dict] = {}
    for c in configs:
        g = c["group"]
        if g not in groups:
            groups[g] = {"name": g, "url": c["group_url"], "entries": []}
        groups[g]["entries"].append(c)

    # All URLs in the full config list (for cross-group parent detection).
    all_urls = {c["url"] for c in configs}

    sections: list[str] = []
    for gdata in groups.values():
        entries = gdata["entries"]
        url_set = {e["url"] for e in entries}
        url_to_inherit = {e["url"]: e.get("inherit_url") for e in entries}

        sorted_entries = _topo_sort_group(entries)

        items: list[str] = []
        for e in sorted_entries:
            depth = _inherit_depth(e["url"], url_set, url_to_inherit)
            indent_style = f"margin-left:{depth * 1.4}rem;" if depth else ""
            indent_marker = "&#x21b3;&nbsp;" if depth else ""  # ↳

            date_span = (
                f'<span class="date">{_esc(e["date"])}</span>'
                if e.get("date") else ""
            )
            current_badge = (
                '<span class="badge-current">current</span>'
                if e.get("current") else ""
            )
            desc_span = (
                f'<span class="desc">{_esc(e["description"])}</span>'
                if e.get("description") else ""
            )

            # Cross-group inheritance annotation: parent is known but outside
            # this group (either in another group or entirely outside root).
            cross_inherit_html = ""
            inh_url = e.get("inherit_url")
            inh_title = e.get("inherit_title")
            if inh_url and inh_url not in url_set:
                # Parent is in a different group within root — link to it.
                label_text = _esc(inh_title or inh_url)
                if inh_url in all_urls:
                    cross_inherit_html = (
                        f'<span class="inherits-from">'
                        f'inherits&nbsp;<a href="{html.escape(inh_url, quote=True)}">{label_text}</a>'
                        f'</span>'
                    )
                else:
                    cross_inherit_html = (
                        f'<span class="inherits-from">'
                        f'inherits&nbsp;{label_text}'
                        f'</span>'
                    )
            elif inh_url is None and e.get("inherit_title"):
                # Parent resolved but is outside root tree.
                cross_inherit_html = (
                    f'<span class="inherits-from">'
                    f'inherits&nbsp;{_esc(e["inherit_title"])}'
                    f'</span>'
                )

            error_indicator = ""
            if e.get("error"):
                error_title = html.escape(_PARSE_FAIL_TOOLTIP, quote=True)
                error_indicator = (
                    f' <a href="/errors" class="error-icon" title="{error_title}">'
                    f'&#x26A0;&#xFE0F;</a>'
                )

            items.append(
                f'<li style="{indent_style}">'
                f'{indent_marker}'
                f'<a href="{html.escape(e["url"], quote=True)}">{_esc(e["title"])}</a>'
                f'{error_indicator}{current_badge}{date_span}'
                f'{cross_inherit_html}'
                f'{desc_span}'
                f'</li>'
            )
        items_html = "\n".join(items)
        if gdata["name"]:
            heading = (
                f'<h2><a href="{html.escape(gdata["url"], quote=True)}">'
                f'{_esc(gdata["name"])}/</a></h2>'
            )
        else:
            heading = ""
        sections.append(f"<section>{heading}<ul>{items_html}</ul></section>")

    body = "\n".join(sections) if sections else "<p>No reviews found.</p>"
    # Escape at the HTML sink so CodeQL sees html.escape (CIP-000E alert #12).
    label = f"/{html.escape(breadcrumb)}" if breadcrumb else "root"
    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{_esc(page_title)}</title>
<style>
  body{{font-family:system-ui,sans-serif;max-width:760px;margin:3rem auto;padding:0 1.5rem;}}
  h1{{font-size:1.4rem;margin-bottom:.5rem;}}
  .up{{margin:0 0 1rem;font-size:.9rem;}}
  .up a{{color:#555;text-decoration:none;}}
  .up a:hover{{text-decoration:underline;}}
  .filters{{display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;
            background:#f5f5f5;border:1px solid #ddd;border-radius:6px;
            padding:.6rem .8rem;margin-bottom:1.5rem;font-size:.875rem;}}
  .filters label{{display:flex;align-items:center;gap:.3rem;}}
  .filters input[type=date]{{font-size:.85rem;padding:.15rem .3rem;}}
  .filters button{{padding:.2rem .7rem;cursor:pointer;}}
  .filters a.clear{{color:#666;font-size:.85rem;text-decoration:none;}}
  .filters a.clear:hover{{text-decoration:underline;}}
  h2{{font-size:1.05rem;color:#555;margin:1.5rem 0 .4rem;
      border-bottom:1px solid #e0e0e0;padding-bottom:.3rem;}}
  h2 a{{color:#2e6da4;text-decoration:none;}}
  h2 a:hover{{text-decoration:underline;}}
  ul{{list-style:none;padding:0 0 0 1rem;margin:.2rem 0;}}
  li{{padding:.3rem 0;line-height:1.4;}}
  li a{{color:#1a4f7a;font-weight:500;text-decoration:none;}}
  li a:hover{{text-decoration:underline;}}
  .date{{margin-left:.6rem;font-size:.8rem;color:#777;font-variant-numeric:tabular-nums;}}
  .badge-current{{margin-left:.5rem;font-size:.7rem;font-weight:600;
                  background:#d4edda;color:#155724;border-radius:3px;
                  padding:.1rem .35rem;vertical-align:middle;}}
  .desc{{display:block;font-size:.85rem;color:#666;margin-top:.1rem;}}
  .inherits-from{{margin-left:.6rem;font-size:.78rem;color:#888;font-style:italic;}}
  .inherits-from a{{color:#888;text-decoration:none;}}
  .inherits-from a:hover{{text-decoration:underline;}}
  .error-banner{{background:#fff3cd;border:1px solid #ffc107;border-radius:6px;
                 padding:.5rem .9rem;font-size:.9rem;margin-bottom:1rem;}}
  .error-banner a{{color:#856404;font-weight:500;}}
  .error-icon{{text-decoration:none;margin-left:.3rem;}}
  section{{margin-bottom:.5rem;}}
</style>
</head>
<body>
<h1>Reviews under <code>{label}</code></h1>
{up_link}
{error_banner}
{filter_form}
{body}
</body>
</html>"""
    return HTMLResponse(page_html)


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


def _specs_with_options_field(reviewer, column: str) -> list[dict]:
    """Widget specs whose options or option-labels come from *column*."""
    out: list[dict] = []
    for spec in reviewer.get_widget_specs():
        if not isinstance(spec, dict):
            continue
        args = spec.get("args") or {}
        if args.get("options_field") == column or args.get("options_labels_field") == column:
            out.append(spec)
    return out


def _populate_status_html(
    reviewer, updated_cols: list[str], button_field: str = ""
) -> str:
    """Human-readable status after a multi-output populate (e.g. Propose split)."""
    key = str(button_field or "")
    if "reset" in key.lower():
        try:
            keys = reviewer.get_value("topic_keys")
        except Exception:
            keys = None
        n = len(keys) if isinstance(keys, (list, tuple)) else 1
        return (
            f'<span class="status-ok">&#10003; Reset to k={_esc(str(n))} seed.'
            f"</span>"
        )
    pending = None
    if "pending_proposal" in updated_cols:
        try:
            pending = reviewer.get_value("pending_proposal")
        except Exception:
            pending = None
    if isinstance(pending, dict) and pending.get("kind") == "split":
        k0 = pending.get("k_before")
        k1 = pending.get("k_after")
        focus = pending.get("focus") or "?"
        parent = pending.get("parent") or "?"
        # Propose always rewrites topic_keys; Name-only relabels while pending.
        # Propose+name (non-stub) also rewrites topic_labels in the same click.
        try:
            labels = reviewer.get_value("topic_labels") or {}
        except Exception:
            labels = {}
        children = list(pending.get("children") or [])
        named = [
            str(labels.get(str(c), c)) if isinstance(labels, dict) else str(c)
            for c in children
        ]
        from referia.assess.compute.topic_naming import _is_provisional_label

        all_named = bool(named) and not any(
            _is_provisional_label(lab, children[i] if i < len(children) else None)
            for i, lab in enumerate(named)
        )
        if all_named and "topic_labels" in updated_cols:
            preview = ", ".join(_esc(x) for x in named[:4])
            if len(named) > 4:
                preview += ", …"
            verb = (
                "Split proposed and named"
                if "topic_keys" in updated_cols
                else "Named pending children"
            )
            return (
                f'<span class="status-ok">&#10003; {verb}: '
                f"{preview}. Confirm to seal or Undo to reject.</span>"
            )
        return (
            f'<span class="status-ok">&#10003; Split proposed: '
            f"{_esc(str(parent))} → k={_esc(str(k0))}→{_esc(str(k1))}, "
            f"focus={_esc(str(focus))}. Confirm to seal or Undo to reject.</span>"
        )
    if "pending_proposal" in updated_cols:
        try:
            still = reviewer.get_value("pending_proposal")
        except Exception:
            still = "x"
        if still in (None, "", {}):
            try:
                keys = reviewer.get_value("topic_keys")
            except Exception:
                keys = None
            n = len(keys) if isinstance(keys, (list, tuple)) else "?"
            # Undo restores catalogue columns; Confirm only swaps planes and
            # clears pending/undo. Both update uq_spec — do not key off that.
            if "topic_keys" in updated_cols or "responsibilities" in updated_cols:
                return (
                    f'<span class="status-ok">&#10003; Split rejected '
                    f"— restored (k={_esc(str(n))}).</span>"
                )
            return (
                f'<span class="status-ok">&#10003; Split sealed '
                f"(k={_esc(str(n))}).</span>"
            )
    return '<span class="status-ok">&#10003; Populated</span>'


def _populate_batch_size(spec: dict) -> int:
    """Return ``args.batch`` (default 10). ``0`` is unbounded this request."""
    raw = (spec.get("args") or {}).get("batch")
    if raw is None or raw == "":
        return 10
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 10
    return n if n >= 0 else 10


def _value_is_filled(value: Any) -> bool:
    """True when a populate target already has a usable value (CIP-001D skip)."""
    if value is None:
        return False
    if isinstance(value, float) and value != value:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    if isinstance(value, (list, dict, tuple)) and len(value) == 0:
        return False
    return True


def _populate_paused_fields(reviewer) -> set:
    paused = getattr(reviewer, "_populate_paused_fields", None)
    if paused is None:
        paused = set()
        try:
            reviewer._populate_paused_fields = paused
        except Exception:
            pass
    return paused if isinstance(paused, set) else set()


def _set_populate_paused(reviewer, field: str, paused: bool) -> None:
    fields = _populate_paused_fields(reviewer)
    key = str(field)
    if paused:
        fields.add(key)
    else:
        fields.discard(key)
    try:
        reviewer._populate_paused_fields = fields
    except Exception:
        pass


def _populate_progress(reviewer) -> dict:
    store = getattr(reviewer, "_populate_progress", None)
    if store is None:
        store = {}
        try:
            reviewer._populate_progress = store
        except Exception:
            return {}
    return store if isinstance(store, dict) else {}


def _remember_populate_progress(reviewer, field: str, counts: dict) -> None:
    store = _populate_progress(reviewer)
    store[str(field)] = dict(counts)
    try:
        reviewer._populate_progress = store
    except Exception:
        pass


def _flush_after_populate_batch(reviewer) -> None:
    """Best-effort CIP-001D flush so a batch is on disk before the next POST."""
    flush = getattr(reviewer, "save_flows", None)
    if not callable(flush):
        return
    try:
        flush()
    except Exception as exc:
        log.debug("populate-all batch flush failed: %s", exc)


def _run_populate_all_and_respond(
    reviewer,
    field: str,
    btn_spec: dict,
    request: Request,
    templates,
    path_prefix: str = "",
    *,
    paused: bool = False,
) -> HTMLResponse:
    """Run at most ``args.batch`` unfilled rows; return a progress chip."""
    compute_spec = _build_populate_compute_spec(btn_spec, field)
    if compute_spec is None:
        return HTMLResponse(
            '<span class="status-warning">&#9888; PopulateButton has no compute spec</span>'
        )

    label = str((btn_spec.get("args") or {}).get("description") or "Populate")
    target = _populate_button_target(btn_spec)
    batch = _populate_batch_size(btn_spec)
    if paused:
        _set_populate_paused(reviewer, field, True)
    else:
        _set_populate_paused(reviewer, field, False)

    saved = None
    try:
        saved = reviewer.get_index()
    except Exception:
        pass

    try:
        working = list(reviewer.working_indices())
    except Exception:
        working = list(reviewer.index_list())
    n_total = len(working)
    n_ok = 0
    n_fail = 0
    n_skipped = 0
    n_attempted = 0
    try:
        if not paused:
            for idx in working:
                try:
                    reviewer.set_index(idx)
                    current = reviewer.get_value(target)
                except Exception:
                    current = None
                if _value_is_filled(current):
                    n_skipped += 1
                    continue
                if batch and n_attempted >= batch:
                    break
                try:
                    reviewer.run_populate({"compute": compute_spec})
                    n_ok += 1
                except Exception as exc:
                    n_fail += 1
                    _log_route_error("Populate all", exc, field=field, index=idx)
                n_attempted += 1
            if n_ok or n_skipped:
                _flush_after_populate_batch(reviewer)
        else:
            remembered = _populate_progress(reviewer).get(str(field)) or {}
            n_ok = int(remembered.get("n_ok", 0) or 0)
            n_fail = int(remembered.get("n_fail", 0) or 0)
            n_skipped = int(remembered.get("n_skipped", 0) or 0)
            n_total = int(remembered.get("n_total", n_total) or n_total)
    finally:
        if saved is not None:
            try:
                reviewer.set_index(saved)
            except Exception:
                pass

    if n_ok == 0 and n_fail > 0 and n_skipped == 0:
        return HTMLResponse(_user_error_html("Populate all"))

    n_done = n_skipped + n_ok
    remaining = n_total - n_done
    chain = (not paused) and remaining > 0 and not (n_ok == 0 and n_fail > 0)
    _remember_populate_progress(
        reviewer,
        field,
        {
            "n_ok": n_ok,
            "n_fail": n_fail,
            "n_skipped": n_skipped,
            "n_total": n_total,
        },
    )
    # Escape at the HTML sink so CodeQL sees html.escape (CIP-000E).
    return HTMLResponse(
        render_populate_progress_chip(
            label=html.escape(str(label)),
            field=html.escape(str(field), quote=True),
            n_done=n_done,
            n_total=n_total,
            n_fail=n_fail,
            n_skipped=n_skipped,
            paused=paused,
            chain=chain,
        )
    )


def _run_populate_and_respond(
    reviewer,
    field: str,
    btn_spec: dict,
    *,
    request: Request | None = None,
    templates=None,
    path_prefix: str = "",
) -> HTMLResponse:
    """Shared populate logic for both single-config and root-mode routes."""
    compute_spec = _build_populate_compute_spec(btn_spec, field)

    if compute_spec is None:
        return HTMLResponse(
            '<span class="status-warning">&#9888; PopulateButton has no compute spec</span>'
        )

    target = btn_spec.get("args", {}).get("target", field)
    compute_fields = compute_spec.get("field", target)
    if isinstance(compute_fields, list):
        updated_cols = [str(c) for c in compute_fields if c and c != "_"]
    else:
        updated_cols = [str(compute_fields)] if compute_fields else [str(target)]

    try:
        reviewer.run_populate({"compute": compute_spec})
    except Exception as exc:
        _log_route_error("Populate", exc, field=field)
        return HTMLResponse(_user_error_html("Populate"))

    try:
        layout = reviewer.get_display_layout()
    except Exception:
        layout = ""
    if (
        layout == "inline_list"
        and request is not None
        and templates is not None
    ):
        ctx = _panel_response_context(reviewer, path_prefix)
        return templates.TemplateResponse(request, "review_panel.html", ctx)

    data = _current_data(reviewer)
    # Refresh current values into *data* so options_field dropdowns see new keys.
    for col in updated_cols:
        try:
            data[col] = reviewer.get_value(col)
        except Exception:
            pass

    parts = [_populate_status_html(reviewer, updated_cols, button_field=field)]
    # Dedupe OOB fragments by DOM id so multiple updated_cols watching the
    # same Plotly pane / chrome dropdown do not fight HTMX.
    oob_by_id: dict[str, str] = {}

    def _stash(fragment: str) -> None:
        import re

        m = re.search(r'\bid="([^"]+)"', fragment)
        key = m.group(1) if m else fragment[:80]
        oob_by_id[key] = fragment

    refreshed_fields: set[str] = set()
    for col in updated_cols:
        if col in refreshed_fields:
            continue
        refreshed_fields.add(col)
        target_spec = _find_spec(reviewer, col)
        if target_spec is not None:
            widget_html = render_widget(
                target_spec, reviewer.get_value(col), data
            )
            _stash(_make_oob(widget_html))
        for opt_spec in _specs_with_options_field(reviewer, col):
            # Review dropdowns whose options come from this column.
            from referia.assess.viewer_bindings import is_viewer_chrome_type

            if is_viewer_chrome_type(opt_spec):
                continue  # handled via viewer OOB below
            f = opt_spec.get("field")
            if not f:
                continue
            widget_html = render_widget(
                opt_spec, reviewer.get_value(f), data
            )
            _stash(_make_oob(widget_html))
        for frag in _viewer_highlight_oobs(reviewer, col):
            _stash(frag)
        # visible_if dependents (e.g. Confirm/Undo gated on pending_proposal)
        for dep in reviewer.affected_widgets(col):
            if dep in refreshed_fields:
                continue
            dep_spec = _find_oob_spec(reviewer, dep)
            if dep_spec is None:
                continue
            refreshed_fields.add(dep)
            try:
                dep_val = reviewer.get_value(dep)
            except Exception:
                dep_val = None
            _stash(_make_oob(render_widget(dep_spec, dep_val, data)))

    parts.extend(oob_by_id.values())
    return HTMLResponse("\n".join(parts))


def _prefix_href(href: str | None, path_prefix: str = "") -> str | None:
    """Prefix a site-absolute href with the root-mode config path if needed."""
    if not href:
        return None
    prefix = (path_prefix or "").rstrip("/")
    if not prefix or not href.startswith("/") or href.startswith(prefix + "/"):
        return href
    return prefix + href


def _generation_status_html(result: dict, *, path_prefix: str = "") -> str:
    """Build a status-bar fragment for a successful document generation.

    Includes ``data-auto-download`` so ``base.html`` starts the download
    after HTMX swaps the status bar (plain ``<a>`` clicks still work too).
    """
    doctype = _esc(str(result.get("type") or "document"))
    status = result.get("status") or "created"
    href = _prefix_href(result.get("href"), path_prefix)
    if status == "drafted":
        return (
            f'<span class="status-ok">&#10003; Drafted {doctype} email.</span>'
        )
    if href:
        esc_href = _esc(href)
        return (
            f'<span class="status-ok" data-auto-download="{esc_href}">'
            f"&#10003; Created {doctype}. "
            f'<a href="{esc_href}" download>'
            f"Download</a></span>"
        )
    return f'<span class="status-ok">&#10003; Created {doctype}.</span>'


def _run_generate_document(
    reviewer, n: int, *, summary: bool = False, path_prefix: str = ""
) -> HTMLResponse:
    """Shared generate-document logic for single-config and root-mode routes."""
    action = "Generate summary document" if summary else "Generate document"
    try:
        result = reviewer.generate_document(n, summary=summary)
    except IndexError:
        return HTMLResponse(
            f'<span class="status-warning">&#9888; No document at index {int(n)}</span>'
        )
    except Exception as exc:
        _log_route_error(action, exc, n=n, summary=summary)
        return HTMLResponse(_user_error_html(action))
    return HTMLResponse(
        _generation_status_html(result or {}, path_prefix=path_prefix)
    )


def _run_edit_pdf(
    reviewer, n: int, *, path_prefix: str = ""
) -> HTMLResponse:
    """Shared edit-pdf logic for single-config and root-mode routes."""
    try:
        path = reviewer.ensure_edit_pdf(n)
    except IndexError:
        return HTMLResponse(
            f'<span class="status-warning">&#9888; No editpdf at index {int(n)}</span>'
        )
    except Exception as exc:
        _log_route_error("Prepare PDF", exc, n=n)
        return HTMLResponse(_user_error_html("Prepare PDF"))

    href = None
    if hasattr(reviewer, "document_download_href"):
        href = reviewer.document_download_href(path)
    if href is None:
        # Fall back to the record-document route (works after ensure).
        href = f"/record-document/editpdf/{int(n)}"
    href = _prefix_href(href, path_prefix)
    esc_href = _esc(href)
    return HTMLResponse(
        f'<span class="status-ok" data-auto-download="{esc_href}">'
        f"&#10003; PDF ready. "
        f'<a href="{esc_href}" download>Download</a></span>'
    )


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
    _apply_index(reviewer, index)
    prefix = _config_path_prefix(config_path)
    ctx = _panel_response_context(reviewer, prefix, request=request)
    return _templates(request).TemplateResponse(request, "review_panel.html", ctx)


@root_router.get("/{config_path:path}/listing-page", response_class=HTMLResponse)
async def root_listing_page(request: Request, config_path: str):
    """CIP-0020 fragment for a root-mode config path."""
    reviewer = _root_reviewer(request, config_path)
    try:
        layout = reviewer.get_display_layout()
    except Exception:
        layout = "side_by_side"
    if layout != "inline_list":
        return HTMLResponse("")
    prefix = _config_path_prefix(config_path)
    window = _window_for_reviewer(reviewer, request)
    view_options = view_options_for_interface(getattr(reviewer, "_interface", None))
    filter_state = reviewer.get_filter_state()
    html = render_inline_listing(
        _collect_listing_entries(reviewer, window["page_indices"], prefix),
        reviewer.get_review_specs(view_options=view_options),
        group_by=_inline_list_group_by(filter_state),
        detail_field=reviewer.get_display_detail_field(),
        documents=_list_document_entries(reviewer, "documents"),
        working_count=int(window.get("working_count") or 0),
        window=window,
        fragment=True,
    )
    return HTMLResponse(html)


@root_router.get("/{config_path:path}/indices", response_class=HTMLResponse)
async def root_get_indices(request: Request, config_path: str):
    reviewer = _root_reviewer(request, config_path)
    return HTMLResponse(_render_index_selector(reviewer.index_list(), reviewer.get_index()))


@root_router.post("/{config_path:path}/field/{column}", response_class=HTMLResponse)
async def root_update_field(request: Request, config_path: str, column: str):
    reviewer = _root_reviewer(request, config_path)
    form = await request.form()
    raw_value = form.get(column)
    record_index = form.get("index")

    if record_index is not None and str(record_index) != "":
        try:
            reviewer.set_index(record_index)
        except Exception as exc:
            _log_route_error("Update", exc, column=column, index=record_index)
            return HTMLResponse(_user_error_html("Update"))

    if _inherited_field_is_readonly(reviewer, column):
        log.warning("Refusing write to inherited read-only field")
        return HTMLResponse(_user_error_html("Update"))

    spec = _find_spec(reviewer, column)
    value: Any = _coerce_form_value(raw_value, spec)

    try:
        reviewer.set_value(column, value)
        status_html = '<span class="status-ok">&#10003; Updated</span>'
    except Exception as exc:
        _log_route_error("Update", exc, column=column)
        return HTMLResponse(_user_error_html("Update"))

    source = form.get("source")
    data = _current_data(reviewer)
    parts = [status_html]
    parts.extend(
        _field_update_oob_parts(
            reviewer,
            column,
            data=data,
            record_index=record_index,
            source=source,
        )
    )
    return HTMLResponse("\n".join(parts))


@root_router.post("/{config_path:path}/field-bulk/{column}", response_class=HTMLResponse)
async def root_update_field_bulk(request: Request, config_path: str, column: str):
    reviewer = _root_reviewer(request, config_path)
    templates = _templates(request)
    form = await request.form()
    raw_value = form.get(column)
    if _inherited_field_is_readonly(reviewer, column):
        log.warning("Refusing bulk write to inherited read-only field")
        ctx = _panel_response_context(reviewer, _config_path_prefix(config_path))
        return _panel_with_oob_status(
            templates, request, ctx, _user_error_html("Bulk update")
        )
    spec = _find_spec(reviewer, column)
    value: Any = _coerce_form_value(raw_value, spec)

    try:
        _apply_field_bulk(reviewer, column, value)
    except Exception as exc:
        _log_route_error("Bulk update", exc, column=column)
        ctx = _panel_response_context(reviewer, _config_path_prefix(config_path))
        return _panel_with_oob_status(
            templates, request, ctx, _user_error_html("Bulk update")
        )

    ctx = _panel_response_context(reviewer, _config_path_prefix(config_path))
    return templates.TemplateResponse(request, "review_panel.html", ctx)


@root_router.post("/{config_path:path}/filters", response_class=HTMLResponse)
async def root_apply_filters(request: Request, config_path: str):
    reviewer = _root_reviewer(request, config_path)
    templates = _templates(request)
    form = await request.form()
    try:
        reviewer.set_filter_state(_parse_filter_form(form, reviewer))
    except Exception as exc:
        _log_route_error("Filters", exc)
        return HTMLResponse(_user_error_html("Filters"))
    _window_for_reviewer(reviewer, reset=True)
    ctx = _panel_response_context(reviewer, _config_path_prefix(config_path))
    return templates.TemplateResponse(request, "review_panel.html", ctx)


@root_router.post("/{config_path:path}/filters/clear", response_class=HTMLResponse)
async def root_clear_filters(request: Request, config_path: str):
    reviewer = _root_reviewer(request, config_path)
    templates = _templates(request)
    try:
        reviewer.clear_filters()
    except Exception as exc:
        _log_route_error("Filters", exc)
        return HTMLResponse(_user_error_html("Filters"))
    _window_for_reviewer(reviewer, reset=True)
    ctx = _panel_response_context(reviewer, _config_path_prefix(config_path))
    return templates.TemplateResponse(request, "review_panel.html", ctx)


@root_router.post("/{config_path:path}/save", response_class=HTMLResponse)
async def root_save(request: Request, config_path: str):
    reviewer = _root_reviewer(request, config_path)
    try:
        reviewer.save_flows()
        return HTMLResponse('<span class="status-ok">&#10003; Saved</span>')
    except Exception as exc:
        _log_route_error("Save", exc)
        return HTMLResponse(_user_error_html("Save"))


@root_router.post("/{config_path:path}/reload", response_class=HTMLResponse)
async def root_reload(request: Request, config_path: str):
    reviewer = _root_reviewer(request, config_path)
    templates = _templates(request)
    try:
        reviewer.load_flows(reload=True)
    except Exception as exc:
        _log_route_error("Reload", exc)
        return HTMLResponse(_user_error_html("Reload"))
    ctx = _panel_response_context(reviewer, _config_path_prefix(config_path))
    return _panel_with_oob_status(
        templates,
        request,
        ctx,
        '<span class="status-ok">&#10003; Reloaded</span>',
    )


@root_router.post("/{config_path:path}/generate-document/{n}", response_class=HTMLResponse)
async def root_generate_document(request: Request, config_path: str, n: int):
    reviewer = _root_reviewer(request, config_path)
    form = await request.form()
    err = _apply_form_index(reviewer, form)
    if err is not None:
        return err
    return _run_generate_document(
        reviewer, n, summary=False, path_prefix=_config_path_prefix(config_path)
    )


@root_router.post(
    "/{config_path:path}/generate-summary-document/{n}", response_class=HTMLResponse
)
async def root_generate_summary_document(request: Request, config_path: str, n: int):
    reviewer = _root_reviewer(request, config_path)
    return _run_generate_document(
        reviewer, n, summary=True, path_prefix=_config_path_prefix(config_path)
    )


@root_router.post("/{config_path:path}/edit-pdf/{n}", response_class=HTMLResponse)
async def root_edit_pdf(request: Request, config_path: str, n: int):
    reviewer = _root_reviewer(request, config_path)
    return _run_edit_pdf(
        reviewer, n, path_prefix=_config_path_prefix(config_path)
    )


@root_router.post("/{config_path:path}/populate/{field}", response_class=HTMLResponse)
async def root_populate(request: Request, config_path: str, field: str):
    reviewer = _root_reviewer(request, config_path)
    btn_spec = _find_populate_spec(reviewer, field)
    if btn_spec is None:
        return HTMLResponse(
            f'<span class="status-warning">&#9888; No PopulateButton for {_esc(field)}</span>'
        )
    form = await request.form()
    err = _apply_form_index(reviewer, form, action="Populate")
    if err is not None:
        return err
    return _run_populate_and_respond(
        reviewer,
        field,
        btn_spec,
        request=request,
        templates=_templates(request),
        path_prefix=_config_path_prefix(config_path),
    )


@root_router.post(
    "/{config_path:path}/populate-all/{field}/pause", response_class=HTMLResponse
)
async def root_pause_populate_all(request: Request, config_path: str, field: str):
    reviewer = _root_reviewer(request, config_path)
    btn_spec = _find_populate_spec(reviewer, field)
    if btn_spec is None:
        return HTMLResponse(
            f'<span class="status-warning">&#9888; No PopulateButton for {_esc(field)}</span>'
        )
    return _run_populate_all_and_respond(
        reviewer,
        field,
        btn_spec,
        request=request,
        templates=_templates(request),
        path_prefix=_config_path_prefix(config_path),
        paused=True,
    )


@root_router.post("/{config_path:path}/populate-all/{field}", response_class=HTMLResponse)
async def root_populate_all(request: Request, config_path: str, field: str):
    reviewer = _root_reviewer(request, config_path)
    btn_spec = _find_populate_spec(reviewer, field)
    if btn_spec is None:
        return HTMLResponse(
            f'<span class="status-warning">&#9888; No PopulateButton for {_esc(field)}</span>'
        )
    return _run_populate_all_and_respond(
        reviewer,
        field,
        btn_spec,
        request=request,
        templates=_templates(request),
        path_prefix=_config_path_prefix(config_path),
    )


@root_router.get("/{config_path:path}/record-document/{kind}/{n}")
async def root_get_record_document(
    request: Request,
    config_path: str,
    kind: str,
    n: int,
    index: str | None = None,
):
    reviewer = _root_reviewer(request, config_path)
    return _serve_record_document(request, reviewer, kind, n, index)


@root_router.get("/{config_path:path}/document/{path:path}")
async def root_get_document(request: Request, config_path: str, path: str):
    reviewer = _root_reviewer(request, config_path)
    return _serve_document_file(request, reviewer, path)


# ── Catch-all full page — MUST be registered last ────────────────────────────

@root_router.get("/errors", response_class=HTMLResponse)
async def list_errors(request: Request):
    """Show all configs that failed to parse (YAML) or load (WebReviewer)."""
    root = request.app.state.root
    all_configs = _list_sub_configs(root, "")

    # ── YAML parse errors found while scanning the tree ──────────────────────
    parse_errors = [c for c in all_configs if c.get("error")]

    # ── WebReviewer load errors recorded during lazy loading ─────────────────
    load_errors: list[dict] = getattr(request.app.state, "load_errors", [])

    generic_msg = _esc(_BROWSER_ERROR_HINT)

    rows_parse = "".join(
        f'<tr>'
        f'<td><code>{_esc(e["yml_path"])}</code></td>'
        f'<td class="err-msg">{generic_msg}</td>'
        f'</tr>'
        for e in parse_errors
    ) or "<tr><td colspan='2'>None</td></tr>"

    rows_load = "".join(
        f'<tr>'
        f'<td><code>{_esc(e["path"])}</code></td>'
        f'<td class="err-type">{_esc(e["type"])}</td>'
        f'<td class="err-msg">'
        f'{_esc(_load_failure_hint_for_type(str(e.get("type") or "")))}'
        f'</td>'
        f'<td class="err-time">{_esc(e["time"])}</td>'
        f'</tr>'
        for e in reversed(load_errors)
    ) or "<tr><td colspan='4'>None</td></tr>"

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Config Errors</title>
<style>
  body{{font-family:system-ui,sans-serif;max-width:1000px;margin:3rem auto;padding:0 1.5rem;}}
  h1{{font-size:1.4rem;}}
  h2{{font-size:1.1rem;margin-top:2rem;border-bottom:1px solid #ddd;padding-bottom:.3rem;}}
  .back{{font-size:.9rem;margin-bottom:1.5rem;}}
  .back a{{color:#2e6da4;}}
  table{{width:100%;border-collapse:collapse;font-size:.85rem;margin-top:.5rem;}}
  th{{text-align:left;background:#f5f5f5;padding:.4rem .6rem;border-bottom:2px solid #ddd;}}
  td{{padding:.35rem .6rem;border-bottom:1px solid #eee;vertical-align:top;word-break:break-word;}}
  .err-msg{{color:#c0392b;font-family:monospace;}}
  .err-type{{color:#777;white-space:nowrap;}}
  .err-time{{color:#999;white-space:nowrap;font-size:.8rem;}}
  .ok{{color:#27ae60;font-weight:500;}}
</style>
</head>
<body>
<h1>&#x26A0;&#xFE0F; Config Errors</h1>
<p class="back"><a href="/">&larr; Back to listings</a></p>

<h2>YAML parse failures ({len(parse_errors)})</h2>
<p style="font-size:.85rem;color:#666;">These <code>_referia.yml</code> files could not be read at all.</p>
<table>
<thead><tr><th>File</th><th>Error</th></tr></thead>
<tbody>{rows_parse}</tbody>
</table>

<h2>Reviewer load failures ({len(load_errors)})</h2>
<p style="font-size:.85rem;color:#666;">These configs parsed OK but failed when a reviewer tried to open them.</p>
<table>
<thead><tr><th>Config file</th><th>Type</th><th>Error</th><th>When</th></tr></thead>
<tbody>{rows_load}</tbody>
</table>

<p style="font-size:.8rem;color:#999;margin-top:2rem;">
  Errors are also written to <code>{_esc(root)}/referia-server.log</code>.
  Load failures accumulate until the server restarts.
</p>
</body>
</html>"""
    return HTMLResponse(page_html)


@root_router.get("/{config_path:path}", response_class=HTMLResponse)
async def root_index(
    request: Request,
    config_path: str,
    after: str | None = None,
    before: str | None = None,
    current: str | None = None,
    index: str | None = None,
):
    """Render the full review page for a root-mode config path.

    Redirects to a trailing-slash URL when none is present so that relative
    hrefs in viewer HTML (e.g. ``../pdfpages``) resolve correctly in the
    browser.  Without the slash the browser treats the last path segment as a
    file, stripping it before resolving ``..``-relative links.  Query strings
    (including ``?index=``) are preserved on that redirect.

    ``?index=<value>`` selects that record before render so a summary listing
    can deep-link to a student's mark sheet.

    When the path maps to a directory without a ``_referia.yml``, a listing of
    sub-configs is shown instead.  The ``after``, ``before`` and ``current``
    query params filter that listing.  Current-only is on by default;
    pass ``current=0`` to show all.
    """
    from fastapi.responses import RedirectResponse

    # Ensure trailing slash so relative URLs in viewer HTML work correctly.
    if config_path and not config_path.endswith("/"):
        dest = request.url.path + "/"
        query = request.url.query
        if query:
            dest = f"{dest}?{query}"
        return RedirectResponse(
            url=dest,
            status_code=301,
        )

    from fastapi import HTTPException as _HTTPException

    try:
        reviewer = _root_reviewer(request, config_path)
    except _HTTPException as exc:
        if exc.status_code == 404:
            # No _referia.yml here — show a filtered listing of sub-configs.
            all_configs = _list_sub_configs(request.app.state.root, config_path)
            if all_configs:
                current_only = _current_only_from_param(current)
                visible = _filter_configs(
                    all_configs, after=after, before=before, current_only=current_only
                )
                return _render_directory_listing(
                    config_path, visible,
                    after=after, before=before, current_only=current_only,
                )
        raise

    _apply_index(reviewer, index)
    prefix = _config_path_prefix(config_path)
    ctx = _panel_response_context(reviewer, prefix, request=request)

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
