"""Widget-to-HTML renderer for the referia web display backend.

Translates widget specification dicts (keyed on ``type``, ``field``, ``args``,
``visible_if``) into HTML strings with HTMX attributes for live field updates.
This is the web-backend equivalent of ``WidgetCluster.display()``.

Public API
----------
render_widget(spec, value, data) -> str
    Render a single widget spec to an HTML string.

render_viewer(view_spec, content) -> str
    Render a pre-evaluated viewer entry (Markdown / HTML) to an HTML string.

render_form(specs, data) -> str
    Render all widget specs for a record into a ``<form>`` fragment.
"""

import html as _html
import logging
import re
from typing import Any
from urllib.parse import quote

from lynguine.util.misc import markdown2html

log = logging.getLogger(__name__)

# Field names already warned about (avoid flooding logs on every re-render).
_warned_dom_ids: set[str] = set()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _escape(value: Any) -> str:
    """HTML-escape a value for safe use in attributes or text."""
    return _html.escape(str(value) if value is not None else "")


def _widget_dom_id(field: str) -> str:
    """Return a CSS/HTML-safe id fragment for a field name.

    Field names may contain spaces (e.g. ``Importance Fairness``).  Spaces are
    invalid in HTML ids and break ``querySelector('#…')`` / HTMX OOB swaps,
    which treat the space as a descendant combinator.  Replace runs of
    characters outside ``[A-Za-z0-9_-]`` with a single underscore.

    Logs a one-shot warning per distinct field name when sanitisation changes
    the identifier, so authors notice that ``widget-{field}`` is rewritten.
    """
    raw = str(field)
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", raw).strip("_")
    if not s:
        s = "field"
    elif s[0].isdigit():
        s = f"f_{s}"
    if s != raw and raw not in _warned_dom_ids:
        _warned_dom_ids.add(raw)
        log.warning(
            "Field name %r is not a valid HTML/CSS id; widget DOM id rewritten "
            "to %r. Prefer field names using only letters, digits, underscore, "
            "and hyphen so ids match the column name.",
            raw,
            s,
        )
    return s


def _url_path_segment(field: str) -> str:
    """Percent-encode a field name for use in a URL path segment."""
    return quote(str(field), safe="")


def _htmx_field_attrs(column: str, trigger: str = "change") -> str:
    """Standard HTMX attributes for a form control that posts on the given trigger.

    ``trigger`` should be a valid HTMX event string.  Defaults to ``"change"``.
    Use ``"change, blur"`` for text-like inputs so that typing then immediately
    clicking Save is captured.  Use ``"change, mouseup"`` for range sliders so
    that a drag-and-release is captured even when the browser doesn't fire
    ``change`` until focus leaves the element.
    """
    col = _escape(column)
    col_url = _url_path_segment(column)
    return (
        f'name="{col}" '
        f'hx-post="/field/{col_url}" '
        f'hx-trigger="{trigger}" '
        f'hx-target="#status-bar" '
        f'hx-swap="innerHTML"'
    )


def _visibility_style(spec: dict, data: dict) -> str:
    """Return ``style="display:none"`` when a ``visible_if`` condition is false."""
    condition = spec.get("visible_if")
    if condition is None:
        return ""
    if isinstance(condition, str):
        hidden = not bool(data.get(condition))
    elif isinstance(condition, dict):
        field_name = condition.get("field", "")
        expected = condition.get("value")
        current = data.get(field_name)
        hidden = str(current) != str(expected) if expected is not None else not bool(current)
    else:
        hidden = False
    return ' style="display:none"' if hidden else ""


def _label_html(description: str) -> str:
    if not description:
        return ""
    return f'<span class="widget-description">{_escape(description)}</span>'


def _wrap_widget(inner: str, spec: dict, data: dict) -> str:
    """Wrap rendered HTML in a container div with id and visibility.

    PopulateButtons use ``_populate_button_target()`` to resolve the target
    field from either format (top-level ``field`` or ``args.target``/
    ``args.compute.field``), and get a ``btn-widget-{field}`` id to avoid
    duplicate-id collisions with their target widget.
    """
    widget_type = spec.get("type", "")
    if widget_type == "PopulateButton":
        col = _populate_button_target(spec)
        css_id = f' id="btn-widget-{_widget_dom_id(col)}"' if col else ""
    else:
        col = spec.get("field", "")
        css_id = f' id="widget-{_widget_dom_id(col)}"' if col else ""
    vis = _visibility_style(spec, data)
    return f'<div class="widget-container"{css_id}{vis}>\n{inner}\n</div>'


# ---------------------------------------------------------------------------
# Per-type renderers — each returns the *inner* HTML (no wrapper div)
# ---------------------------------------------------------------------------

def _render_textarea(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", {})
    rows = int(args.get("rows", 5))
    label = _label_html(args.get("description", ""))
    return (
        label
        + f'<textarea class="widget-textarea" {_htmx_field_attrs(column, "change, blur")} rows="{rows}">'
        + f"{_escape(value)}</textarea>"
    )


def _render_text(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", {})
    label = _label_html(args.get("description", ""))
    return (
        label
        + f'<input type="text" class="widget-text" {_htmx_field_attrs(column, "change, blur")} '
        + f'value="{_escape(value)}">'
    )


def _render_int_slider(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", spec)  # fall back to top-level spec keys
    min_v = args.get("min", 0)
    max_v = args.get("max", 100)
    step = args.get("step", 1)
    try:
        val = int(value) if value not in (None, "", "None") else 0
    except (ValueError, TypeError):
        val = 0
    out_id = f"out-{_escape(column)}"
    label = _label_html(spec.get("description", args.get("description", "")))
    return (
        label
        + f'<input type="range" class="widget-slider" {_htmx_field_attrs(column, "change, mouseup")} '
        + f'min="{min_v}" max="{max_v}" step="{step}" value="{val}" '
        + f'oninput="document.getElementById(\'{out_id}\').value=this.value">'
        + f'<output id="{out_id}" class="slider-output">{val}</output>'
    )


def _render_float_slider(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", spec)  # fall back to top-level spec keys
    min_v = args.get("min", 0.0)
    max_v = args.get("max", 1.0)
    step = args.get("step", 0.1)
    try:
        val = float(value) if value not in (None, "", "None") else 0.0
    except (ValueError, TypeError):
        val = 0.0
    out_id = f"out-{_escape(column)}"
    label = _label_html(spec.get("description", args.get("description", "")))
    return (
        label
        + f'<input type="range" class="widget-slider" {_htmx_field_attrs(column, "change, mouseup")} '
        + f'min="{min_v}" max="{max_v}" step="{step}" value="{val}" '
        + f'oninput="document.getElementById(\'{out_id}\').value=this.value">'
        + f'<output id="{out_id}" class="slider-output">{val}</output>'
    )


def _render_int_text(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", {})
    label = _label_html(args.get("description", ""))
    min_attr = f' min="{args["min"]}"' if "min" in args else ""
    max_attr = f' max="{args["max"]}"' if "max" in args else ""
    val = int(value) if value is not None and value == value else 0  # value==value is False for NaN
    return (
        label
        + f'<input type="number" class="widget-number" {_htmx_field_attrs(column)} '
        + f'value="{val}"{min_attr}{max_attr} step="1">'
    )


def _render_float_text(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", {})
    label = _label_html(args.get("description", ""))
    min_attr = f' min="{args["min"]}"' if "min" in args else ""
    max_attr = f' max="{args["max"]}"' if "max" in args else ""
    step = args.get("step", 0.1)
    val = float(value) if value is not None and value == value else 0.0
    return (
        label
        + f'<input type="number" class="widget-number" {_htmx_field_attrs(column)} '
        + f'value="{val}"{min_attr}{max_attr} step="{step}">'
    )


def _render_dropdown(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", {})
    options = args.get("options", [])
    label = _label_html(args.get("description", ""))
    opts_html = "".join(
        f'<option value="{_escape(o)}"{"  selected" if str(o) == str(value) else ""}>'
        f"{_escape(o)}</option>"
        for o in options
    )
    return (
        label
        + f'<select class="widget-select" {_htmx_field_attrs(column)}>'
        + opts_html
        + "</select>"
    )


def _render_select_multiple(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", {})
    options = args.get("options", [])
    selected = {str(v) for v in (value if isinstance(value, (list, tuple)) else ([value] if value else []))}
    label = _label_html(args.get("description", ""))
    opts_html = "".join(
        f'<option value="{_escape(o)}"{"  selected" if str(o) in selected else ""}>'
        f"{_escape(o)}</option>"
        for o in options
    )
    return (
        label
        + f'<select class="widget-select-multiple" {_htmx_field_attrs(column)} multiple>'
        + opts_html
        + "</select>"
    )


def _render_radio(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", {})
    options = args.get("options", [])
    label = _label_html(args.get("description", ""))
    radios = "".join(
        f'<label class="radio-option">'
        f'<input type="radio" {_htmx_field_attrs(column)} '
        f'value="{_escape(o)}"{"  checked" if str(o) == str(value) else ""}>'
        f"{_escape(o)}</label>"
        for o in options
    )
    return label + f'<fieldset class="widget-radio">{radios}</fieldset>'


def _render_checkbox(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", {})
    description = args.get("description", "") or column
    checked = " checked" if bool(value) else ""
    return (
        f'<label class="widget-checkbox">'
        f'<input type="checkbox" {_htmx_field_attrs(column)} value="true"{checked}>'
        f"{_escape(description)}</label>"
    )


def _render_combobox(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", {})
    options = args.get("options", [])
    list_id = f"list-{_escape(column)}"
    label = _label_html(args.get("description", ""))
    datalist = (
        f'<datalist id="{list_id}">'
        + "".join(f'<option value="{_escape(o)}">' for o in options)
        + "</datalist>"
    )
    return (
        label
        + f'<input type="text" class="widget-combobox" {_htmx_field_attrs(column)} '
        + f'list="{list_id}" value="{_escape(value)}">'
        + datalist
    )


def _render_date_picker(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", {})
    label = _label_html(args.get("description", ""))
    # Stored dates are YYYYMMDD; HTML date inputs need YYYY-MM-DD.
    date_val = ""
    if value:
        s = str(value)
        if len(s) == 8 and s.isdigit():
            date_val = f"{s[:4]}-{s[4:6]}-{s[6:]}"
        else:
            date_val = s
    return (
        label
        + f'<input type="date" class="widget-date" {_htmx_field_attrs(column)} '
        + f'value="{_escape(date_val)}">'
    )


def _render_label(spec: dict, value: Any) -> str:
    args = spec.get("args", {})
    text = args.get("value", args.get("description", ""))
    return f'<div class="widget-label-display">{_escape(text)}</div>'


def _render_html(spec: dict, value: Any) -> str:
    args = spec.get("args", {})
    # Prefer explicit value/description; fall back to the data value as plain text.
    content = args.get("value", args.get("description", str(value) if value else ""))
    return f'<div class="widget-html">{content}</div>'


def _evaluate_liquid(template: str, data: dict) -> str:
    """Substitute ``{{key}}`` Liquid-style references with values from *data*.

    Only handles simple column references (``{{columnName}}``).  More complex
    Liquid constructs are left as-is so they do not silently break.
    """
    def _sub(match: re.Match) -> str:
        key = match.group(1).strip()
        val = data.get(key)
        return str(val) if val is not None else ""

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", _sub, template)


def _markdown_widget_content(
    spec: dict, value: Any = None, data: dict | None = None
) -> str:
    """Resolve Markdown widget display text (liquid / args / field value).

    Content priority:
      1. top-level liquid: — interview widgets and %param% headings
      2. args.liquid — CriterionComment expansion
      3. args.value / args.description — static configured content
      4. the field's data value
    """
    args = spec.get("args", {}) or {}
    top_liquid = spec.get("liquid")
    if top_liquid and data is not None:
        top_liquid = _evaluate_liquid(top_liquid, data)
    args_liquid = args.get("liquid")
    if args_liquid and data is not None:
        args_liquid = _evaluate_liquid(args_liquid, data)
    return (
        top_liquid
        or args_liquid
        or args.get("value")
        or args.get("description")
        or (str(value) if value else "")
        or ""
    )


def _resolve_section_title(spec: dict, data: dict | None) -> str:
    """Resolve a Section node's title (optional ``{{liquid}}`` against *data*)."""
    args = spec.get("args", {}) or {}
    title = str(
        spec.get("title")
        or spec.get("liquid")
        or args.get("title")
        or args.get("description")
        or ""
    ).strip()
    if not title:
        return ""
    if data is not None and "{{" in title:
        title = _evaluate_liquid(title, data).strip()
    return title


def _section_key(title: str, index: int) -> str:
    """Stable key for open/closed persistence across HTMX swaps."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return f"{index}/{slug or 'section'}"


def _render_markdown_widget(spec: dict, value: Any, data: dict | None = None) -> str:
    content = _markdown_widget_content(spec, value, data)
    return f'<div class="widget-markdown">{markdown2html(content) if content else ""}</div>'


def _render_criterion(spec: dict, value: Any, data: dict | None = None) -> str:
    """Render a Criterion widget — the read-only criterion text shown above a comment box.

    The criterion text lives in the top-level ``liquid:`` key and may contain
    ``{{columnName}}`` Liquid references that are resolved against the current
    row data.  The result is rendered as Markdown.
    """
    template = spec.get("liquid", "") or ""
    if data is not None and template:
        template = _evaluate_liquid(template, data)
    return f'<div class="widget-criterion">{markdown2html(template) if template else ""}</div>'


def _render_save_button(spec: dict, value: Any) -> str:
    args = spec.get("args", {})
    label = args.get("description", "Save")
    # Each field posts its own value when the user edits it (change/blur/mouseup).
    # Save's job is only to flush the in-memory reviewer state to disk; it does
    # not need to re-collect form values via hx-include.
    return (
        f'<button class="widget-button save-button" '
        f'hx-post="/save" hx-target="#status-bar" hx-swap="innerHTML">'
        f"{_escape(label)}</button>"
    )


def _render_reload_button(spec: dict, value: Any) -> str:
    args = spec.get("args", {})
    label = args.get("description", "Reload")
    return (
        f'<button class="widget-button reload-button" '
        f'hx-post="/reload" hx-target="#status-bar" hx-swap="innerHTML">'
        f"{_escape(label)}</button>"
    )


def _populate_button_target(spec: dict) -> str:
    """Return the target field name for a PopulateButton spec.

    Supports two YAML formats:

    * Simple (top-level ``field``): ``{type: PopulateButton, field: summary, ...}``
    * Complex (``args.target`` or ``args.compute.field``):
      ``{type: PopulateButton, args: {target: introSummary, compute: {field: introSummary}}}``

    ``args.target`` / ``args.compute.field`` take priority when present because
    the top-level ``field`` may be a button identifier, not the populate target.
    """
    args = spec.get("args", {})
    return (
        args.get("target")
        or args.get("compute", {}).get("field")
        or spec.get("field")
        or ""
    )


def _render_populate_button(spec: dict, value: Any) -> str:
    args = spec.get("args", {})
    label = args.get("description", "Populate")
    target = _populate_button_target(spec)
    col_url = _url_path_segment(target)
    indicator = f"widget-{_widget_dom_id(target)}"
    return (
        f'<button class="widget-button populate-button" '
        f'hx-post="/populate/{col_url}" hx-target="#status-bar" hx-swap="innerHTML" '
        f'hx-indicator="#{indicator}" hx-disabled-elt="this">'
        f"{_escape(label)}</button>"
    )


# ---------------------------------------------------------------------------
# Dispatch table — maps _referia.yml type strings → renderer functions
# ---------------------------------------------------------------------------

# Renderers in this set receive (spec, value, data) instead of (spec, value).
_DATA_AWARE_RENDERERS: frozenset[str] = frozenset({"Criterion", "Markdown"})

_RENDERERS: dict[str, Any] = {
    "Textarea": _render_textarea,
    "Text": _render_text,
    "IntSlider": _render_int_slider,
    "FloatSlider": _render_float_slider,
    "IntText": _render_int_text,
    "BoundedIntText": _render_int_text,
    "BoundedFloatText": _render_float_text,
    "Dropdown": _render_dropdown,
    "Select": _render_dropdown,
    "SelectMultiple": _render_select_multiple,
    "RadioButtons": _render_radio,
    "Checkbox": _render_checkbox,
    "Flag": _render_checkbox,
    "Combobox": _render_combobox,
    "DatePicker": _render_date_picker,
    "Label": _render_label,
    "HTML": _render_html,
    "HTMLMath": _render_html,
    "Markdown": _render_markdown_widget,
    "SaveButton": _render_save_button,
    "ReloadButton": _render_reload_button,
    "PopulateButton": _render_populate_button,
    "Criterion": _render_criterion,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_widget(spec: dict, value: Any = None, data: dict | None = None) -> str:
    """Render a single widget specification dict to an HTML string.

    Args:
        spec: Widget spec dict with keys ``type``, ``field``, ``args``, and
            optionally ``visible_if``.
        value: Current data value for the widget's field.
        data: Full record data dict used to evaluate ``visible_if`` conditions.

    Returns:
        HTML string wrapped in ``<div class="widget-container">``.
    """
    if data is None:
        data = {}
    widget_type = spec.get("type", "")
    renderer = _RENDERERS.get(widget_type)
    if renderer is None:
        return f'<!-- unsupported widget type: {_escape(widget_type)} -->'
    # Criterion renderers need the full row data to evaluate Liquid expressions.
    if widget_type in _DATA_AWARE_RENDERERS:
        inner = renderer(spec, value, data)
    else:
        inner = renderer(spec, value)
    return _wrap_widget(inner, spec, data)


def render_viewer(view_spec: dict, content: str) -> str:
    """Render a pre-evaluated viewer entry to an HTML string.

    Liquid / display templates are resolved by ``WebReviewer`` before calling
    this function; ``content`` is the resulting plain string.

    Args:
        view_spec: Viewer spec dict (keys: ``type``, optionally ``liquid``,
            ``display``).
        content: Pre-rendered string content to display.

    Returns:
        HTML string for the viewer block.
    """
    view_type = view_spec.get("type", "Markdown")
    if view_type in {"Markdown", "HTMLMath"}:
        rendered = markdown2html(content) if content else ""
        return f'<div class="viewer viewer-markdown">{rendered}</div>'
    return f'<div class="viewer viewer-html">{content}</div>'


def render_form(specs: list[dict], data: dict) -> str:
    """Render all widget specs for a record into a complete HTML form fragment.

    Args:
        specs: Ordered list of widget / Section-cluster specs from
            ``WebReviewer.get_review_specs()``.  Nested
            ``type: Section`` nodes carry ``title`` and ``entries``.
        data: Current record data dict mapping field names to values.

    Returns:
        HTML string containing the full review form wrapped in a ``<form>``
        element.  Each ``type: Section`` with ``entries:`` becomes a
        collapsible ``<details class="review-section">`` (closed by default).
        Sibling widgets outside a Section stay in the open flow.
    """
    section_index = 0

    def _render_list(items: list[dict]) -> list[str]:
        nonlocal section_index
        parts: list[str] = []
        for spec in items:
            if not isinstance(spec, dict):
                continue
            if spec.get("type") == "Section":
                title = _resolve_section_title(spec, data) or "Section"
                key = _escape(_section_key(title, section_index))
                section_index += 1
                children = spec.get("entries") or spec.get("children") or []
                if not isinstance(children, list):
                    children = []
                body = "\n".join(_render_list(children))
                parts.append(
                    f'<details class="review-section" data-section-key="{key}">\n'
                    f"<summary>{_escape(title)}</summary>\n"
                    f"{body}\n"
                    f"</details>"
                )
                continue
            field = spec.get("field", "")
            value = data.get(field) if field else None
            parts.append(render_widget(spec, value, data))
        return parts

    inner = "\n".join(_render_list(specs))
    return f'<form id="review-form" hx-boost="false">\n{inner}\n</form>'


def render_document_panel(
    pdfs: list[dict],
    urls: list[dict],
    prefix: str = "",
    current_index: Any = None,
    documents: list[dict] | None = None,
    summary_documents: list[dict] | None = None,
) -> str:
    """HTML for PDFs, URL links, and document-generation actions.

    *prefix* is the root-server config path (e.g. ``/theses/examined/introduction``)
    or empty in single-config mode.  Iframe ``src`` values must include it;
    HTMX prefix rewriting does not apply to ``<iframe>`` requests.

    *current_index* is appended as ``?index=`` so each record has a distinct
    document URL (see backlog ``2026-10-07_web-record-document-index-in-url``).

    *documents* / *summary_documents* are button specs from
    ``WebReviewer.list_document_entries``; HTMX posts use unprefixed paths
    (``base.html`` rewrites them in root-server mode).
    """
    from urllib.parse import quote

    documents = documents or []
    summary_documents = summary_documents or []
    if not pdfs and not urls and not documents and not summary_documents:
        return ""
    index_q = ""
    if current_index is not None:
        index_q = f"?index={quote(str(current_index), safe='')}"
    parts = ['<div class="document-panel">', "<h2>Documents</h2>"]
    action_entries = list(documents) + list(summary_documents)
    if action_entries:
        parts.append('<div class="document-actions">')
        for entry in action_entries:
            n = int(entry.get("n") or 0)
            label = _escape(str(entry.get("label") or "Create document"))
            if entry.get("summary"):
                action = f"/generate-summary-document/{n}"
            else:
                action = f"/generate-document/{n}"
            parts.append(
                f'<button type="button" class="widget-button document-button" '
                f'hx-post="{_escape(action)}" hx-target="#status-bar" '
                f'hx-swap="innerHTML" hx-disabled-elt="this">'
                f"{label}</button>"
            )
        parts.append("</div>")
    if urls:
        parts.append('<ul class="document-url-list">')
        for entry in urls:
            href = _escape(entry.get("href") or "")
            label = _escape(entry.get("label") or href)
            if href:
                parts.append(
                    f'<li><a href="{href}" target="_blank" rel="noopener noreferrer">'
                    f"{label}</a></li>"
                )
        parts.append("</ul>")
    for entry in pdfs:
        kind = _escape(str(entry.get("kind") or "localpdf"))
        n = int(entry.get("n") or 0)
        label = _escape(str(entry.get("label") or kind))
        src = _escape(f"{prefix}/record-document/{kind}/{n}{index_q}")
        # Stable key so open/closed state can survive HTMX index swaps.
        doc_key = _escape(f"{kind}/{n}")
        parts.append(f'<details class="pdf-entry" data-doc-key="{doc_key}">')
        parts.append(f"<summary>{label}</summary>")
        if entry.get("exists"):
            parts.append(
                f'<iframe class="pdf-frame" src="{src}" title="{label}" '
                f'loading="lazy"></iframe>'
                f'<p class="pdf-open"><a href="{src}" target="_blank" '
                f'rel="noopener noreferrer">Open in a new tab</a></p>'
            )
        else:
            parts.append(f'<p class="pdf-missing">PDF not found for {label}.</p>')
        if kind == "editpdf":
            parts.append(
                f'<button type="button" class="widget-button edit-pdf-button" '
                f'hx-post="/edit-pdf/{n}" hx-target="#status-bar" '
                f'hx-swap="innerHTML" hx-disabled-elt="this">'
                f"Prepare / download PDF</button>"
            )
        parts.append("</details>")
    parts.append("</div>")
    return "\n".join(parts)
