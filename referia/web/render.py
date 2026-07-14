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
from typing import Any

from lynguine.util.misc import markdown2html


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _escape(value: Any) -> str:
    """HTML-escape a value for safe use in attributes or text."""
    return _html.escape(str(value) if value is not None else "")


def _htmx_field_attrs(column: str, trigger: str = "change") -> str:
    """Standard HTMX attributes for a form control that posts on the given trigger.

    ``trigger`` should be a valid HTMX event string.  Defaults to ``"change"``.
    Use ``"change, blur"`` for text-like inputs so that typing then immediately
    clicking Save is captured.  Use ``"change, mouseup"`` for range sliders so
    that a drag-and-release is captured even when the browser doesn't fire
    ``change`` until focus leaves the element.
    """
    col = _escape(column)
    return (
        f'name="{col}" '
        f'hx-post="/field/{col}" '
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
    """Wrap rendered HTML in a container div with id and visibility."""
    col = spec.get("field", "")
    css_id = f' id="widget-{_escape(col)}"' if col else ""
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
    val = int(value) if value is not None else 0
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
    val = float(value) if value is not None else 0.0
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


def _render_markdown_widget(spec: dict, value: Any) -> str:
    args = spec.get("args", {})
    content = args.get("value", args.get("description", str(value) if value else ""))
    return f'<div class="widget-markdown">{markdown2html(content) if content else ""}</div>'


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


def _render_populate_button(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", {})
    label = args.get("description", "Populate")
    col = _escape(column)
    return (
        f'<button class="widget-button populate-button" '
        f'hx-post="/populate/{col}" hx-target="#status-bar" hx-swap="innerHTML">'
        f"{_escape(label)}</button>"
    )


# ---------------------------------------------------------------------------
# Dispatch table — maps _referia.yml type strings → renderer functions
# ---------------------------------------------------------------------------

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
        specs: Ordered list of widget spec dicts from
            ``WebReviewer.get_widget_specs()``.
        data: Current record data dict mapping field names to values.

    Returns:
        HTML string containing the full review form wrapped in a ``<form>`` element.
    """
    parts = [render_widget(spec, data.get(spec.get("field", "")), data) for spec in specs]
    inner = "\n".join(parts)
    return f'<form id="review-form" hx-boost="false">\n{inner}\n</form>'
