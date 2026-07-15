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
async def index(
    request: Request,
    after: str | None = None,
    before: str | None = None,
    current: str | None = None,
):
    """Render the full review page for the current record.

    In root-server mode (``app.state.root`` is set) there is no single
    reviewer, so instead we render a directory listing of all configs found
    under the root.  The ``after``, ``before`` and ``current`` query params
    filter the listing by date range or work-in-progress status.
    """
    if getattr(request.app.state, "root", None) is not None:
        current_only = current is not None
        configs = _list_sub_configs(request.app.state.root, "")
        configs = _filter_configs(configs, after=after, before=before, current_only=current_only)
        return _render_directory_listing("", configs, after=after, before=before, current_only=current_only)

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
            # Record in the in-memory error registry (if it exists on app_state).
            load_errors = getattr(app_state, "load_errors", None)
            if load_errors is not None:
                import time as _time
                load_errors.append({
                    "path": str(config_file),
                    "error": str(exc),
                    "type": type(exc).__name__,
                    "time": _time.strftime("%Y-%m-%d %H:%M:%S"),
                })
            raise HTTPException(status_code=503, detail=f"Could not load config: {exc}")
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
    ``inherit_abs`` via ``yaml.safe_load``.  Any parse error silently returns
    an empty dict so a bad yml never breaks the listing page.

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
        return {"_error": str(exc)}


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
    root_path = Path(root)
    clean = url_path.strip("/")
    search_base = root_path / clean if clean else root_path
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
            "error": meta.get("_error"),  # None if parse succeeded
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
        up_link = f'<p class="up"><a href="{parent}">&uarr; ..</a></p>'
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
    filter_form = f"""<form class="filters" method="get">
  <label>After&nbsp;<input type="date" name="after" value="{after_val}"></label>
  <label>Before&nbsp;<input type="date" name="before" value="{before_val}"></label>
  <label><input type="checkbox" name="current" value="1"{current_checked}> Current only</label>
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
                        f'inherits&nbsp;<a href="{inh_url}">{label_text}</a>'
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
                error_title = _esc(e["error"][:120])
                error_indicator = (
                    f' <a href="/errors" class="error-icon" title="{error_title}">'
                    f'&#x26A0;&#xFE0F;</a>'
                )

            items.append(
                f'<li style="{indent_style}">'
                f'{indent_marker}'
                f'<a href="{e["url"]}">{_esc(e["title"])}</a>'
                f'{error_indicator}{current_badge}{date_span}'
                f'{cross_inherit_html}'
                f'{desc_span}'
                f'</li>'
            )
        items_html = "\n".join(items)
        if gdata["name"]:
            heading = (
                f'<h2><a href="{gdata["url"]}">'
                f'{_esc(gdata["name"])}/</a></h2>'
            )
        else:
            heading = ""
        sections.append(f"<section>{heading}<ul>{items_html}</ul></section>")

    body = "\n".join(sections) if sections else "<p>No reviews found.</p>"
    label = f"/{_esc(breadcrumb)}" if breadcrumb else "root"
    html = f"""<!DOCTYPE html>
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
    return HTMLResponse(html)


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

@root_router.get("/errors", response_class=HTMLResponse)
async def list_errors(request: Request):
    """Show all configs that failed to parse (YAML) or load (WebReviewer)."""
    root = request.app.state.root
    all_configs = _list_sub_configs(root, "")

    # ── YAML parse errors found while scanning the tree ──────────────────────
    parse_errors = [c for c in all_configs if c.get("error")]

    # ── WebReviewer load errors recorded during lazy loading ─────────────────
    load_errors: list[dict] = getattr(request.app.state, "load_errors", [])

    rows_parse = "".join(
        f'<tr>'
        f'<td><code>{_esc(e["yml_path"])}</code></td>'
        f'<td class="err-msg">{_esc(e["error"])}</td>'
        f'</tr>'
        for e in parse_errors
    ) or "<tr><td colspan='2'>None</td></tr>"

    rows_load = "".join(
        f'<tr>'
        f'<td><code>{_esc(e["path"])}</code></td>'
        f'<td class="err-type">{_esc(e["type"])}</td>'
        f'<td class="err-msg">{_esc(e["error"])}</td>'
        f'<td class="err-time">{_esc(e["time"])}</td>'
        f'</tr>'
        for e in reversed(load_errors)
    ) or "<tr><td colspan='4'>None</td></tr>"

    html = f"""<!DOCTYPE html>
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
    return HTMLResponse(html)


@root_router.get("/{config_path:path}", response_class=HTMLResponse)
async def root_index(
    request: Request,
    config_path: str,
    after: str | None = None,
    before: str | None = None,
    current: str | None = None,
):
    """Render the full review page for a root-mode config path.

    Redirects to a trailing-slash URL when none is present so that relative
    hrefs in viewer HTML (e.g. ``../pdfpages``) resolve correctly in the
    browser.  Without the slash the browser treats the last path segment as a
    file, stripping it before resolving ``..``-relative links.

    When the path maps to a directory without a ``_referia.yml``, a listing of
    sub-configs is shown instead.  The ``after``, ``before`` and ``current``
    query params filter that listing.
    """
    from fastapi.responses import RedirectResponse

    # Ensure trailing slash so relative URLs in viewer HTML work correctly.
    if config_path and not config_path.endswith("/"):
        return RedirectResponse(
            url=request.url.path + "/",
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
                current_only = current is not None
                visible = _filter_configs(
                    all_configs, after=after, before=before, current_only=current_only
                )
                return _render_directory_listing(
                    config_path, visible,
                    after=after, before=before, current_only=current_only,
                )
        raise

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
