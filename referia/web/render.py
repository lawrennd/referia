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
import json
import logging
import re
from contextvars import ContextVar
from typing import Any
from urllib.parse import quote, urlencode

from lynguine.util.misc import markdown2html

log = logging.getLogger(__name__)

# Field names already warned about (avoid flooding logs on every re-render).
_warned_dom_ids: set[str] = set()

# Optional record index for inline_list per-row widgets (hx-vals + unique DOM ids).
_record_index_ctx: ContextVar[Any] = ContextVar("referia_record_index", default=None)
# Listing chrome (Section parameters): field posts write every filtered row.
_listing_chrome_ctx: ContextVar[bool] = ContextVar(
    "referia_listing_chrome", default=False
)
# Inherited ancestor review with inherit.writable: false (CIP-0018).
_readonly_inherited_ctx: ContextVar[bool] = ContextVar(
    "referia_readonly_inherited", default=False
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _escape(value: Any) -> str:
    """HTML-escape a value for safe use in attributes or text."""
    return _html.escape(str(value) if value is not None else "")


def _json_script_content(payload: Any) -> str:
    """Serialize *payload* for embedding in ``<script type=\"application/json\">``.

    Do not use :func:`html.escape`: script text content does not decode
    ``&quot;`` entities, so escaped JSON fails ``JSON.parse``.  Instead
    Unicode-escape ``<``, ``>``, and ``&`` so the payload cannot break out
    of the script element.
    """
    return (
        json.dumps(payload, default=str)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


_A_TAG_RE = re.compile(r"<a\b([^>]*)>", re.IGNORECASE)
_HEADING_RE = re.compile(r"(<h([1-6])\b[^>]*>.*?</h\2>)", re.IGNORECASE | re.DOTALL)


def _ensure_links_new_tab(html: str) -> str:
    """Add ``target="_blank"`` (and ``rel``) to anchors that lack a target.

    Listing title / url / PDF links already set this explicitly. Markdown and
    HTML viewer content from Liquid does not, so course-site and similar links
    would navigate away from the review session without this pass.
    """
    if not html or "<a" not in html.lower():
        return html

    def _fix(match: re.Match[str]) -> str:
        attrs = match.group(1)
        if re.search(r"\btarget\s*=", attrs, re.IGNORECASE):
            return match.group(0)
        extra = ' target="_blank"'
        if not re.search(r"\brel\s*=", attrs, re.IGNORECASE):
            extra += ' rel="noopener noreferrer"'
        return f"<a{attrs}{extra}>"

    return _A_TAG_RE.sub(_fix, html)


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

    When a record index is active (inline_list per-row forms), includes
    ``hx-vals`` so ``/field/{column}`` can update the correct tall row.

    Uses ``focus-scroll:false`` so swapping into ``#status-bar`` does not
    scroll/jump focus toward the green toast (CoE 2026-10-18).
    """
    col = _escape(column)
    col_url = _url_path_segment(column)
    if _readonly_inherited_ctx.get():
        return (
            f'name="{col}" readonly disabled aria-readonly="true" '
            f'title="Inherited from parent (read-only)"'
        )
    if _listing_chrome_ctx.get():
        return (
            f'name="{col}" '
            f'hx-post="/field-bulk/{col_url}" '
            f'hx-trigger="{trigger}" '
            f'hx-target="#review-panel" '
            f'hx-swap="innerHTML" '
            f'hx-disabled-elt="this"'
        )
    attrs = (
        f'name="{col}" '
        f'hx-post="/field/{col_url}" '
        f'hx-trigger="{trigger}" '
        f'hx-target="#status-bar" '
        f'hx-swap="innerHTML focus-scroll:false"'
    )
    record_index = _record_index_ctx.get()
    if record_index is not None:
        vals = _escape(json.dumps({"index": str(record_index)}))
        attrs += f' hx-vals="{vals}"'
    return attrs


def _visibility_style(spec: dict, data: dict) -> str:
    """Return ``style="display:none"`` when a ``visible_if`` condition is false.

    String conditions (``visible_if: "Interview"``) use checkbox truthiness so
    ``False`` / ``\"False\"`` / ``0`` hide the widget — plain ``bool()`` would
    treat the string ``\"False\"`` as visible.

    Dict form supports ``equals`` / ``value`` comparisons, or ``not: true`` to
    invert checkbox truthiness (show when the field is empty / unset)::

        visible_if: {field: pending_proposal, not: true}
    """
    condition = spec.get("visible_if")
    if condition is None:
        return ""
    if isinstance(condition, str):
        hidden = not _checkbox_checked(data.get(condition))
    elif isinstance(condition, dict):
        field_name = condition.get("field", "")
        current = data.get(field_name)
        if condition.get("not"):
            # Invert: visible when the field is falsy (no pending proposal, etc.).
            hidden = _checkbox_checked(current)
        else:
            expected = condition.get("value")
            if expected is None and "equals" in condition:
                expected = condition.get("equals")
            if expected is None:
                hidden = not _checkbox_checked(current)
            else:
                hidden = not _scalar_equals(current, expected)
    else:
        hidden = False
    return ' style="display:none"' if hidden else ""


def _combine_html_styles(*attrs: str) -> str:
    """Merge ``style="..."`` attribute fragments into one attribute."""
    parts: list[str] = []
    for attr in attrs:
        if not attr:
            continue
        text = str(attr).strip()
        if text.lower().startswith("style="):
            text = text.split("=", 1)[1].strip()
            if len(text) >= 2 and text[0] in {'"', "'"} and text[-1] == text[0]:
                text = text[1:-1]
        text = text.strip().rstrip(";")
        if text:
            parts.append(text)
    if not parts:
        return ""
    return f' style="{"; ".join(parts)}"'


def _label_html(description: str) -> str:
    if not description:
        return ""
    return f'<span class="widget-description">{_escape(description)}</span>'


def _wrap_widget(inner: str, spec: dict, data: dict) -> str:
    """Wrap rendered HTML in a container div with id and visibility.

    PopulateButtons use ``_populate_button_route_key()`` for the container id
    (``btn-widget-{route_key}``) so multiple buttons that share ``args.target``
    keep distinct DOM ids for HTMX OOB visibility swaps.  The write target is
    still used only for ``hx-indicator`` on the button itself.
    """
    widget_type = spec.get("type", "")
    record_index = _record_index_ctx.get()
    index_suffix = (
        f"-{_widget_dom_id(str(record_index))}" if record_index is not None else ""
    )
    if widget_type == "PopulateButton":
        col = _populate_button_route_key(spec)
        css_id = f' id="btn-widget-{_widget_dom_id(col)}{index_suffix}"' if col else ""
    else:
        col = spec.get("field", "")
        css_id = f' id="widget-{_widget_dom_id(col)}{index_suffix}"' if col else ""
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


def _render_dropdown(spec: dict, value: Any, data: dict | None = None) -> str:
    column = spec.get("field", "")
    args = spec.get("args", {})
    options = list(args.get("options") or [])
    # Dynamic options from another field (e.g. topic_keys after Propose split)
    opts_field = args.get("options_field")
    if opts_field and isinstance(data, dict):
        raw = data.get(opts_field)
        if isinstance(raw, (list, tuple)):
            options = [str(o) for o in raw]
        elif isinstance(raw, dict):
            options = [str(k) for k in raw.keys()]
    if value not in (None, "") and str(value) not in {str(o) for o in options}:
        options = [str(value)] + list(options)
    # Optional display labels keyed by option value (e.g. topic_labels → T0)
    labels_map: dict[str, str] = {}
    labels_field = args.get("options_labels_field")
    if labels_field and isinstance(data, dict):
        raw_labels = data.get(labels_field)
        if isinstance(raw_labels, dict):
            labels_map = {str(k): str(v) for k, v in raw_labels.items() if v not in (None, "")}
    label = _label_html(args.get("description", ""))
    opts_html = "".join(
        f'<option value="{_escape(o)}"{"  selected" if str(o) == str(value) else ""}>'
        f"{_escape(labels_map.get(str(o), str(o)))}</option>"
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


def _checkbox_checked(value: Any) -> bool:
    """Whether a Checkbox/Flag cell should render checked.

    Soft-fill often stores ``\"True\"`` / ``\"False\"`` strings from Liquid.
    Plain ``bool(value)`` treats every non-empty string as checked, so
    ``\"False\"`` would appear selected.
    """
    import math

    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and math.isnan(value):
        return False
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    text = str(value).strip().lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no", ""):
        return False
    return bool(value)


def _scalar_equals(current: Any, expected: Any) -> bool:
    """Compare ``visible_if`` ``equals`` / ``value`` against a cell.

    YAML 1.1 unquoted ``yes`` / ``no`` / ``true`` / ``false`` become Python
    bools, while Liquid compute fields typically emit the strings ``"yes"`` /
    ``"no"``. Match those so ``equals: yes`` is not silently always-hidden.
    Arbitrary non-empty strings must not match boolean ``True``.
    """
    if current is expected:
        return True
    if str(current) == str(expected):
        return True
    if isinstance(expected, bool):
        text = "" if current is None else str(current).strip().lower()
        if expected:
            return text in ("true", "1", "yes")
        return current is None or text in ("false", "0", "no", "")
    if isinstance(current, bool):
        return _scalar_equals(expected, current)
    return False


def _render_checkbox(spec: dict, value: Any) -> str:
    column = spec.get("field", "")
    args = spec.get("args", {})
    description = args.get("description", "") or column
    checked = " checked" if _checkbox_checked(value) else ""
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


_LIQUID_ENV = None


def _liquid_environment():
    """Shared python-liquid env (LAX), matching lynguine Compute filters."""
    global _LIQUID_ENV
    if _LIQUID_ENV is None:
        import liquid as lq
        from lynguine.util.liquid import (
            absolute_url,
            markdownify,
            relative_url,
            to_i,
            url_escape,
        )

        env = lq.Environment(tolerance=lq.Mode.LAX)
        env.add_filter("url_escape", url_escape)
        env.add_filter("markdownify", markdownify)
        env.add_filter("relative_url", relative_url)
        env.add_filter("absolute_url", absolute_url)
        env.add_filter("to_i", to_i)
        _LIQUID_ENV = env
    return _LIQUID_ENV


def _evaluate_liquid(template: str, data: dict) -> str:
    """Evaluate a Liquid template against the current row dict.

    Viewer HTML already uses ``CustomDataFrame.view_to_value`` / python-liquid.
    Review Markdown and Criterion widgets must do the same so ``{% if %}``
    tags are executed rather than shown as text.  Invalid templates are
    logged and render as empty rather than dumping the source into the form.
    """
    if not template:
        return ""
    from lynguine.util.misc import remove_nan

    try:
        context = remove_nan(dict(data or {}))
        return _liquid_environment().from_string(template).render(**context)
    except Exception as exc:
        log.error("Liquid evaluation failed: %s", exc)
        return ""


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


def _section_summary_html(spec: dict, title: str) -> str:
    """Section header text plus optional CIP-0018 'open in parent' control."""
    summary = _escape(title)
    href = spec.get("parent_href")
    if spec.get("inherited") and href:
        summary += (
            f' <a class="inherited-open-parent" href="{_escape(href)}">'
            f"open in parent</a>"
        )
    return summary


def iter_spec_leaves(specs: list | None):
    """Yield leaf widget/viewer dicts, walking nested ``type: Section``."""
    for spec in specs or []:
        if not isinstance(spec, dict):
            continue
        if spec.get("type") == "Section":
            yield from iter_spec_leaves(
                spec.get("entries") or spec.get("children") or []
            )
        else:
            yield spec


def render_viewer_tree(
    specs: list, leaf_html, data: dict | None = None
) -> list[str]:
    """Render viewer specs, wrapping inherited Sections like review details.

    *leaf_html(spec)* returns the HTML for one non-Section viewer entry
    (typically ``WebReviewer.render_viewer_html``).  Optional *data*
    evaluates ``visible_if`` on Section wrappers (leaves apply it in
    ``render_viewer``). Hidden blocks stay in the DOM with
    ``display:none`` so HTMX can reveal them after a field toggle.
    """
    row = data if data is not None else {}
    section_index = 0

    def _walk(items: list) -> list[str]:
        nonlocal section_index
        parts: list[str] = []
        for spec in items or []:
            if not isinstance(spec, dict):
                continue
            if spec.get("type") == "Section":
                title = (
                    spec.get("title")
                    or (spec.get("args") or {}).get("title")
                    or "Section"
                )
                extra = " inherited-section" if spec.get("inherited") else ""
                key = _escape(_section_key(str(title), section_index))
                section_index += 1
                inner = "\n".join(_walk(spec.get("entries") or []))
                summary = _section_summary_html(spec, str(title))
                open_attr = " open" if (spec.get("args") or {}).get("open", True) else ""
                vis = _visibility_style(spec, row)
                parts.append(
                    f'<details class="review-section viewer-section{extra}" '
                    f'data-section-key="viewer/{key}"{open_attr}{vis}>\n'
                    f"<summary>{summary}</summary>\n"
                    f"{inner}\n"
                    f"</details>"
                )
            else:
                parts.append(leaf_html(spec))
        return parts

    return _walk(specs)


def _render_markdown_widget(spec: dict, value: Any, data: dict | None = None) -> str:
    content = _markdown_widget_content(spec, value, data)
    rendered = _ensure_links_new_tab(markdown2html(content) if content else "")
    return f'<div class="widget-markdown">{rendered}</div>'


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
        f'hx-post="/save" hx-target="#status-bar" '
        f'hx-swap="innerHTML focus-scroll:false" hx-disabled-elt="this">'
        f"{_escape(label)}</button>"
    )


def _render_reload_button(spec: dict, value: Any) -> str:
    args = spec.get("args", {})
    label = args.get("description", "Reload")
    if _listing_chrome_ctx.get():
        return (
            f'<button type="button" class="widget-button reload-button" '
            f'hx-post="/reload" hx-target="#review-panel" '
            f'hx-swap="innerHTML" hx-disabled-elt="this">'
            f"{_escape(label)}</button>"
        )
    return (
        f'<button class="widget-button reload-button" '
        f'hx-post="/reload" hx-target="#status-bar" '
        f'hx-swap="innerHTML focus-scroll:false" hx-disabled-elt="this">'
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
    When ``compute.field`` is a list (multi-output), prefer ``args.target`` or
    the button's own ``field`` id — never return the list.
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
    """URL segment for POST /populate/{key}.

    Prefer the button's own ``field`` when it differs from the write target so
    multiple PopulateButtons can share a multi-output target (Propose / Undo).
    """
    own = spec.get("field")
    if own:
        return str(own)
    return _populate_button_target(spec)


def _populate_requires_field(spec: dict) -> str:
    """Field that must already be set before this PopulateButton can run."""
    args = spec.get("args") or {}
    raw = args.get("requires")
    if raw is None:
        raw = spec.get("requires")
    if raw is None or raw is False:
        return ""
    return str(raw).strip()


def _requires_satisfied(value: Any) -> bool:
    """True once extract (or similar) has written *value*, including ``[]``."""
    if value is None:
        return False
    if isinstance(value, (list, tuple, dict)):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, bool):
        return bool(value)
    try:
        if value != value:
            return False
    except Exception:
        pass
    if isinstance(value, (int, float)):
        return False
    return bool(value)


def _blocked_populate_button(label: str, reason: str) -> str:
    return (
        f'<button type="button" class="widget-button populate-button is-blocked" '
        f'disabled title="{_escape(reason)}">{_escape(label)}</button>'
    )


def _render_populate_button(spec: dict, value: Any, data: dict | None = None) -> str:
    args = spec.get("args", {})
    label = args.get("description", "Populate")
    route_key = _populate_button_route_key(spec)
    target = _populate_button_target(spec)
    col_url = _url_path_segment(route_key)
    indicator = f"widget-{_widget_dom_id(target)}"
    record_index = _record_index_ctx.get()
    requires = _populate_requires_field(spec)
    if _readonly_inherited_ctx.get():
        return _blocked_populate_button(
            label, "Inherited from parent (read-only)"
        )
    if requires and not _listing_chrome_ctx.get():
        row = data or {}
        if not _requires_satisfied(row.get(requires)):
            return _blocked_populate_button(label, "Extract this row first")
    if _listing_chrome_ctx.get():
        return (
            f'<button type="button" class="widget-button populate-button" '
            f'hx-post="/populate-all/{col_url}" hx-target="#review-panel" '
            f'hx-swap="innerHTML" hx-disabled-elt="this">'
            f"{_escape(label)}</button>"
        )
    if record_index is not None:
        vals = _escape(json.dumps({"index": str(record_index)}))
        # Listing rows refresh the whole panel so extras / detail_field update.
        return (
            f'<button class="widget-button populate-button" '
            f'hx-post="/populate/{col_url}" hx-target="#review-panel" '
            f'hx-swap="innerHTML" hx-vals="{vals}" hx-disabled-elt="this">'
            f"{_escape(label)}</button>"
        )
    return (
        f'<button class="widget-button populate-button" '
        f'hx-post="/populate/{col_url}" hx-target="#status-bar" '
        f'hx-swap="innerHTML focus-scroll:false" '
        f'hx-indicator="#{indicator}" hx-disabled-elt="this">'
        f"{_escape(label)}</button>"
    )


# ---------------------------------------------------------------------------
# Dispatch table — maps _referia.yml type strings → renderer functions
# ---------------------------------------------------------------------------

# Renderers in this set receive (spec, value, data) instead of (spec, value).
_DATA_AWARE_RENDERERS: frozenset[str] = frozenset(
    {"Criterion", "Markdown", "Dropdown", "Select", "PopulateButton"}
)

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

def render_widget(
    spec: dict,
    value: Any = None,
    data: dict | None = None,
    *,
    record_index: Any = None,
) -> str:
    """Render a single widget specification dict to an HTML string.

    Args:
        spec: Widget spec dict with keys ``type``, ``field``, ``args``, and
            optionally ``visible_if``.
        value: Current data value for the widget's field.
        data: Full record data dict used to evaluate ``visible_if`` conditions.
        record_index: When set (inline_list), scopes HTMX posts and DOM ids
            to that tall-table row.

    Returns:
        HTML string wrapped in ``<div class="widget-container">``.
    """
    if data is None:
        data = {}
    token = _record_index_ctx.set(record_index)
    try:
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
    finally:
        _record_index_ctx.reset(token)


def render_viewer(
    view_spec: dict,
    content: str = "",
    *,
    figure: dict | None = None,
    highlight_value: Any = None,
    viewer_index: int = 0,
    data: dict | None = None,
) -> str:
    """Render a pre-evaluated viewer entry to an HTML string.

    Liquid / display templates are resolved by ``WebReviewer`` before calling
    this function for Markdown/HTML entries.  Interactive types
    (``PlotlyFigure``, ``StaticImage``) receive structured ``figure`` / URL
    content instead (CIP-0011).

    Args:
        view_spec: Viewer spec dict (keys: ``type``, optionally ``liquid``,
            ``display``, ``on``, ``highlight``, ``field``).
        content: Pre-rendered string content (Markdown/HTML) or image URL.
        figure: Plotly-like ``{data, layout}`` dict for ``PlotlyFigure``.
        highlight_value: Current value of ``highlight.from_field`` (optional).
        viewer_index: Stable index among ``viewer:`` entries (DOM id).
        data: Current row used to evaluate ``visible_if`` (same rules as
            review widgets). Hidden viewers stay in the DOM with
            ``display:none`` so HTMX OOB can reveal them.

    Returns:
        HTML string for the viewer block.
    """
    from referia.assess.viewer_bindings import (
        click_point_actions,
        highlight_binding,
        viewer_entry_type,
    )

    row = data if data is not None else {}
    vis = _visibility_style(view_spec, row)
    view_type = viewer_entry_type(view_spec)
    if view_type == "PlotlyFigure":
        from referia.assess.viewer_bindings import plotly_size_options

        return _render_plotly_viewer(
            view_spec,
            figure=figure,
            highlight_value=highlight_value,
            viewer_index=viewer_index,
            click_actions=click_point_actions(view_spec),
            highlight=highlight_binding(view_spec),
            size=plotly_size_options(view_spec),
            vis=vis,
        )
    if view_type == "StaticImage":
        src = _escape(content or "")
        return (
            f'<div class="viewer viewer-image" id="viewer-image-{viewer_index}"'
            f"{vis}>"
            f'<img src="{src}" alt="viewer image" loading="lazy" />'
            f"</div>"
        )
    if view_type in {"Markdown", "HTMLMath"}:
        rendered = _ensure_links_new_tab(markdown2html(content) if content else "")
        rendered = _collapse_matching_headings(rendered, view_spec)
        return (
            f'<div class="viewer viewer-markdown" '
            f'id="viewer-markdown-{int(viewer_index)}"{vis}>{rendered}</div>'
        )
    html = _ensure_links_new_tab(content)
    html = _collapse_matching_headings(html, view_spec)
    return (
        f'<div class="viewer viewer-html" id="viewer-html-{int(viewer_index)}"'
        f"{vis}>"
        f"{html}</div>"
    )


def _viewer_collapse_options(view_spec: dict | None) -> dict[str, Any] | None:
    """Return normalised ``collapse:`` options, or ``None`` when inactive.

    Expected YAML::

        collapse:
          headings: [LLM]
          default: closed   # or open
    """
    if not isinstance(view_spec, dict):
        return None
    raw = view_spec.get("collapse")
    if not isinstance(raw, dict):
        return None
    names = raw.get("headings") or raw.get("heading") or []
    if isinstance(names, str):
        names = [names]
    if not isinstance(names, (list, tuple)):
        return None
    folded = {str(name).strip().casefold() for name in names if str(name).strip()}
    if not folded:
        return None
    default = str(raw.get("default") or "closed").strip().casefold()
    return {"headings": folded, "open": default in {"open", "opened", "true"}}


def _heading_plain_text(heading_html: str) -> str:
    """Strip tags from a heading element."""
    inner = re.sub(r"^<h[1-6]\b[^>]*>", "", heading_html, flags=re.IGNORECASE)
    inner = re.sub(r"</h[1-6]>\s*$", "", inner, flags=re.IGNORECASE)
    return re.sub(r"<[^>]+>", "", inner)


def _heading_matches(text: str, names: set[str]) -> bool:
    """True when heading text equals a name, or its first word does."""
    folded = " ".join(text.split()).casefold()
    if not folded:
        return False
    if folded in names:
        return True
    first = folded.split(" ", 1)[0].strip(".:-")
    return first in names


def _collapse_matching_headings(html: str, view_spec: dict | None) -> str:
    """Wrap configured headings and their following siblings in ``<details>``.

    CIP-0014: opt-in viewer collapse. Unmatched headings stay in the open
    flow. The original heading tag is omitted from the body so the summary
    is the only title (same as review ``type: Section``).
    """
    options = _viewer_collapse_options(view_spec)
    if not options or not html:
        return html

    matches = list(_HEADING_RE.finditer(html))
    if not matches:
        return html

    names = options["headings"]
    open_attr = " open" if options["open"] else ""
    out: list[str] = [html[: matches[0].start()]]
    counts: dict[str, int] = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        heading_html = match.group(1)
        body = html[match.end() : end]
        text = _heading_plain_text(heading_html)
        if not _heading_matches(text, names):
            out.append(heading_html)
            out.append(body)
            continue
        label = " ".join(text.split()) or "Section"
        slug = re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-") or "heading"
        counts[slug] = counts.get(slug, 0) + 1
        key = _escape(f"{slug}-{counts[slug]}")
        out.append(
            f'<details class="viewer-heading-collapse" '
            f'data-section-key="{key}"{open_attr}>\n'
            f"<summary>{_escape(label)}</summary>\n"
            f"{body}"
            f"</details>"
        )
    return "".join(out)


def _render_plotly_viewer(
    view_spec: dict,
    *,
    figure: dict | None,
    highlight_value: Any,
    viewer_index: int,
    click_actions: list[dict[str, Any]],
    highlight: dict[str, str] | None,
    size: dict[str, Any] | None = None,
    vis: str = "",
) -> str:
    """Emit a Plotly container with JSON spec and click-binding metadata."""
    from referia.assess.viewer_bindings import apply_highlight, apply_plotly_size

    mode = (highlight or {}).get("mode", "default")
    from_field = (highlight or {}).get("from_field", "")
    size_opts = size or {"mode": "figure", "observe": True, "aspect_ratio": None}
    size_mode = size_opts.get("mode") or "figure"
    observe = bool(size_opts.get("observe", True))
    aspect = size_opts.get("aspect_ratio")
    fig = apply_highlight(figure, selected=highlight_value, mode=mode) if figure else None
    if fig is None:
        fig = {"data": [], "layout": {"title": {"text": "No figure data"}}}
    fig = apply_plotly_size(fig, mode=size_mode) or fig
    fig_json = _json_script_content(fig)
    bindings_json = _json_script_content(click_actions)
    hl_attr = _escape(from_field) if from_field else ""
    mode_attr = _escape(mode)
    size_attr = _escape(size_mode)
    observe_attr = "1" if observe else "0"
    fill_class = " viewer-plotly--fill" if size_mode == "container" else ""
    aspect_style = ""
    aspect_attr = ""
    if size_mode == "container" and aspect:
        aspect_safe = _escape(aspect)
        aspect_attr = f' data-size-aspect="{aspect_safe}"'
        aspect_style = f' style="--plotly-aspect: {aspect_safe}"'
    style_attr = _combine_html_styles(aspect_style, vis)
    vid = f"viewer-plotly-{viewer_index}"
    tid = f"plotly-target-{viewer_index}"
    return (
        f'<div class="viewer viewer-plotly{fill_class}" id="{vid}" '
        f'data-viewer-index="{viewer_index}" '
        f'data-highlight-field="{hl_attr}" '
        f'data-highlight-mode="{mode_attr}" '
        f'data-size-mode="{size_attr}" '
        f'data-size-observe="{observe_attr}"'
        f"{aspect_attr}{style_attr}>"
        f'<div class="plotly-target" id="{tid}"></div>'
        f'<script type="application/json" class="plotly-spec" '
        f'id="plotly-spec-{viewer_index}">'
        f"{fig_json}</script>"
        f'<script type="application/json" class="plotly-bindings" '
        f'id="plotly-bindings-{viewer_index}">'
        f"{bindings_json}</script>"
        f"</div>"
    )


def render_plotly_spec_oob(viewer_index: int, figure: dict | None) -> str:
    """OOB fragment that updates only the Plotly JSON (keeps the live graph)."""
    fig = figure or {"data": [], "layout": {}}
    fig_json = _json_script_content(fig)
    return (
        f'<script type="application/json" class="plotly-spec" '
        f'id="plotly-spec-{int(viewer_index)}" hx-swap-oob="true">'
        f"{fig_json}</script>"
    )


def render_form(
    specs: list[dict],
    data: dict,
    *,
    record_index: Any = None,
    form_id: str | None = None,
) -> str:
    """Render all widget specs for a record into a complete HTML form fragment.

    Args:
        specs: Ordered list of widget / Section-cluster specs from
            ``WebReviewer.get_review_specs()``.  Nested
            ``type: Section`` nodes carry ``title`` and ``entries``.
        data: Current record data dict mapping field names to values.
        record_index: When set, scopes field posts/ids to that record
            (``inline_list`` per-row forms).

    Returns:
        HTML string containing the full review form wrapped in a ``<form>``
        element.          Each ``type: Section`` with ``entries:`` becomes a
        collapsible ``<details class="review-section">`` (closed by default).
        Set ``args.collapse: false`` (or ``collapsible: false``) for a static
        heading that stays in the open flow — e.g. cache buttons that must
        not sit inside Extract / Embed parameters.
        Sibling widgets outside a Section stay in the open flow.
    """
    section_index = 0

    def _render_list(items: list[dict]) -> list[str]:
        nonlocal section_index
        parts: list[str] = []
        for spec in items:
            if not isinstance(spec, dict):
                continue
            field = spec.get("field", "")
            if (
                _readonly_inherited_ctx.get()
                and str(field).endswith("Present")
                and not _checkbox_checked(data.get(field))
            ):
                continue
            if spec.get("type") == "Section":
                if _visibility_style(spec, data):
                    continue
                title = _resolve_section_title(spec, data) or "Section"
                key = _escape(_section_key(title, section_index))
                section_index += 1
                children = spec.get("entries") or spec.get("children") or []
                if not isinstance(children, list):
                    children = []
                token = None
                inherited = bool(spec.get("inherited"))
                writable = spec.get("writable", True)
                if inherited and not writable:
                    token = _readonly_inherited_ctx.set(True)
                try:
                    body = "\n".join(_render_list(children))
                finally:
                    if token is not None:
                        _readonly_inherited_ctx.reset(token)
                args = spec.get("args") or {}
                extra_class = " inherited-section" if inherited else ""
                summary = _section_summary_html(spec, title)
                if not _section_collapsible(spec):
                    heading = f"<h3>{summary}</h3>\n" if title else ""
                    parts.append(
                        f'<section class="review-section review-section-static{extra_class}" '
                        f'data-section-key="{key}">\n'
                        f"{heading}"
                        f"{body}\n"
                        f"</section>"
                    )
                    continue
                open_attr = " open" if args.get("open") else ""
                parts.append(
                    f'<details class="review-section{extra_class}" '
                    f'data-section-key="{key}"{open_attr}>\n'
                    f"<summary>{summary}</summary>\n"
                    f"{body}\n"
                    f"</details>"
                )
                continue
            value = data.get(field) if field else None
            parts.append(
                render_widget(spec, value, data, record_index=record_index)
            )
        return parts

    inner = "\n".join(_render_list(specs))
    if form_id:
        fid = form_id
    elif record_index is not None:
        fid = f'review-form-{_widget_dom_id(str(record_index))}'
    else:
        fid = "review-form"
    return f'<form id="{fid}" hx-boost="false">\n{inner}\n</form>'


def render_filter_bar(
    filter_specs: list[dict],
    sort_specs: list[dict],
    filter_state: dict | None = None,
) -> str:
    """HTML for the inline_list filter/sort bar (directory-listing style)."""
    state = filter_state or {}
    parts = [
        '<form class="filters inline-listing-filters" hx-post="/filters" '
        'hx-target="#review-panel" hx-swap="innerHTML">',
    ]
    for spec in filter_specs or []:
        if not isinstance(spec, dict):
            continue
        field = str(spec.get("field") or "")
        if not field:
            continue
        ftype = str(spec.get("type") or "categorical")
        label = _escape(spec.get("label") or field)
        fname = _escape(field)
        current = state.get(field)
        if ftype == "boolean":
            selected = (
                str(current).strip().lower()
                if current is not None and str(current).strip() != ""
                else "any"
            )
            if selected not in {"any", "true", "false"}:
                selected = "any"
            parts.append(f"<label>{label}&nbsp;")
            parts.append(f'<select name="filter__{fname}">')
            for opt, opt_label in (
                ("any", "Any"),
                ("true", "True"),
                ("false", "False"),
            ):
                sel = " selected" if selected == opt else ""
                parts.append(
                    f'<option value="{opt}"{sel}>{opt_label}</option>'
                )
            parts.append("</select></label>")
        elif ftype == "date_range":
            after = ""
            before = ""
            if isinstance(current, dict):
                after = str(current.get("after") or "")
                before = str(current.get("before") or "")
            parts.append(
                f"<label>{label} after&nbsp;<input type=\"date\" "
                f'name="filter__{fname}__after" value="{_escape(after)}"></label>'
            )
            parts.append(
                f"<label>{label} before&nbsp;<input type=\"date\" "
                f'name="filter__{fname}__before" value="{_escape(before)}"></label>'
            )
        elif ftype == "contains":
            query = ""
            mode = "words"
            if isinstance(current, dict):
                query = str(current.get("query") or "")
                mode = str(current.get("mode") or "words").lower()
            if mode not in ("words", "exact"):
                mode = "words"
            parts.append(f"<label>{label}&nbsp;")
            parts.append(
                f'<input type="search" name="filter__{fname}__query" '
                f'value="{_escape(query)}" placeholder="contains…" '
                f'size="18">'
            )
            parts.append(
                f'<select name="filter__{fname}__mode" '
                f'title="Match mode">'
            )
            for opt, opt_label in (("words", "Words"), ("exact", "Exact")):
                sel = " selected" if mode == opt else ""
                parts.append(
                    f'<option value="{opt}"{sel}>{opt_label}</option>'
                )
            parts.append("</select></label>")
        else:
            values = spec.get("values") or []
            if not isinstance(values, list):
                values = []
            if isinstance(current, (list, set, tuple)):
                selected = str(next(iter(current), "")) if current else ""
            else:
                selected = str(current) if current not in (None, "") else ""
            parts.append(f"<label>{label}&nbsp;")
            parts.append(f'<select name="filter__{fname}">')
            parts.append('<option value="">Any</option>')
            for val in values:
                sel = " selected" if str(val) == selected else ""
                parts.append(
                    f'<option value="{_escape(val)}"{sel}>{_escape(val)}</option>'
                )
            parts.append("</select></label>")

    if sort_specs:
        sort_current = str(state.get("_sort") or "")
        parts.append("<label>Sort&nbsp;<select name=\"sort\">")
        parts.append('<option value="">Default</option>')
        seen_fields: set[str] = set()
        for spec in sort_specs:
            if not isinstance(spec, dict):
                continue
            field = str(spec.get("field") or "")
            if not field or field in seen_fields:
                continue
            seen_fields.add(field)
            for order, order_label in (("desc", "newest"), ("asc", "oldest")):
                key = f"{field}:{order}"
                sel = " selected" if sort_current == key else ""
                option_label = _escape(f"{field} ({order_label})")
                parts.append(
                    f'<option value="{_escape(key)}"{sel}>{option_label}</option>'
                )
        parts.append("</select></label>")

    group_current = str(state.get("_group") or "directory").lower()
    if group_current not in {"directory", "version", "month", "none"}:
        group_current = "directory"
    parts.append(
        '<label>Group by&nbsp;'
        '<select name="group" onchange="this.form.requestSubmit()">'
    )
    for key, label in (
        ("directory", "Directory"),
        ("version", "Version"),
        ("month", "Month"),
        ("none", "None"),
    ):
        sel = " selected" if group_current == key else ""
        parts.append(f'<option value="{key}"{sel}>{label}</option>')
    parts.append("</select></label>")

    parts.append('<button type="submit">Filter</button>')
    parts.append(
        '<button type="button" class="clear" '
        'hx-post="/filters/clear" hx-target="#review-panel" '
        'hx-swap="innerHTML">Clear</button>'
    )
    parts.append("</form>")
    return "\n".join(parts)


def _section_collapsible(spec: dict) -> bool:
    """True unless the Section opts out with ``collapse`` / ``collapsible``."""
    args = spec.get("args") or {}
    for key in ("collapse", "collapsible"):
        if key in args:
            return bool(args[key])
    return True


_LISTING_SKIP_TYPES = frozenset(
    {
        "SaveButton",
        "ReloadButton",
        "precompute",
        "postcompute",
        "Section",
        "Markdown",
        "HTML",
        "HTMLMath",
        "Label",
    }
)


def _split_review_specs_for_listing(
    specs: list[dict],
) -> tuple[dict | None, list[dict]]:
    """Pull out the ``complete`` Checkbox; return (complete_spec, other_specs).

    Save/Reload buttons are omitted from per-row extras (nav already has Save).
    Compute and Markdown extras are skipped so listing rows stay compact.
    """
    complete_spec = None
    extras: list[dict] = []
    for spec in specs or []:
        if not isinstance(spec, dict):
            continue
        wtype = spec.get("type", "")
        if wtype in _LISTING_SKIP_TYPES:
            continue
        if (
            complete_spec is None
            and wtype in {"Checkbox", "Flag"}
            and str(spec.get("field") or "") == "complete"
        ):
            complete_spec = spec
            continue
        extras.append(spec)
    return complete_spec, extras


def render_complete_checkbox(
    value: Any,
    *,
    record_index: Any,
    field: str = "complete",
) -> str:
    """Leading complete toggle for a listing row (checkbox + Done label)."""
    checked = " checked" if _checkbox_checked(value) else ""
    token = _record_index_ctx.set(record_index)
    try:
        dom = (
            f'widget-{_widget_dom_id(field)}-'
            f'{_widget_dom_id(str(record_index))}'
        )
        return (
            f'<div class="widget-container complete-toggle" id="{dom}">'
            f'<label class="complete-check" title="Mark complete">'
            f'<input type="checkbox" {_htmx_field_attrs(field)} '
            f'value="true"{checked} aria-label="Complete">'
            f'<span class="complete-check-label">Done</span>'
            f"</label></div>"
        )
    finally:
        _record_index_ctx.reset(token)


def render_select_all_checkbox(
    all_complete: bool,
    *,
    field: str = "complete",
    count: int = 0,
) -> str:
    """Listing-row control that sets *field* on every filtered index."""
    checked = " checked" if all_complete else ""
    col = _escape(field)
    col_url = _url_path_segment(field)
    n = int(count)
    noun = "config" if n == 1 else "configs"
    return (
        f'<div class="widget-container complete-toggle" id="select-all-{_widget_dom_id(field)}">'
        f'<label class="complete-check" title="Set Done on all filtered rows">'
        f'<input type="checkbox" name="{col}" value="true"{checked} '
        f'aria-label="Select all filtered" '
        f'hx-post="/field-bulk/{col_url}" '
        f'hx-trigger="change" '
        f'hx-target="#review-panel" '
        f'hx-swap="innerHTML">'
        f'<span class="complete-check-label">Done</span>'
        f"</label></div>"
        f'<div class="entry-main">'
        f'<span class="entry-title">Select all filtered</span>'
        f'<span class="badge-meta">{n} {noun}</span>'
        f'<span class="desc">Sets Done on every config matching the current filters.</span>'
        f"</div>"
    )


def render_populate_all_button(
    spec: dict, *, count: int = 0, entries: list[dict] | None = None
) -> str:
    """Listing chrome that runs a PopulateButton on every filtered index."""
    args = spec.get("args") or {}
    label = str(args.get("description") or "Populate")
    route_key = _populate_button_route_key(spec)
    col_url = _url_path_segment(route_key)
    n = int(count)
    noun = "row" if n == 1 else "rows"
    requires = _populate_requires_field(spec)
    blocked = False
    reason = f"Run {_escape(label)} on all filtered rows"
    desc = "Runs this action on every row matching the current filters."
    if requires:
        rows = entries or []
        blocked = (not rows) or any(
            not _requires_satisfied((entry.get("data") or {}).get(requires))
            for entry in rows
        )
        if blocked:
            reason = "Extract all filtered rows first"
            desc = "Extract every filtered row before embedding."
    button = (
        _blocked_populate_button(f"{label} all", reason)
        if blocked
        else (
            f'<button type="button" class="widget-button populate-button" '
            f'hx-post="/populate-all/{col_url}" '
            f'hx-target="#review-panel" hx-swap="innerHTML" '
            f'hx-disabled-elt="this" '
            f'title="{reason}">'
            f"{_escape(label)} all</button>"
        )
    )
    return (
        f'<div class="widget-container complete-toggle">'
        f"{button}"
        f"</div>"
        f'<div class="entry-main">'
        f'<span class="entry-title">{_escape(label)} all filtered</span>'
        f'<span class="badge-meta">{n} {noun}</span>'
        f'<span class="desc">{desc}</span>'
        f"</div>"
    )


def _populate_all_flag(spec: dict) -> bool:
    """True when a PopulateButton should also emit populate-all chrome."""
    raw = (spec.get("args") or {}).get("all")
    if isinstance(raw, bool):
        return raw
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def populate_all_chrome_html(review_specs: list | None, *, count: int) -> str:
    """``side_by_side`` chrome for PopulateButtons with ``args.all: true``.

    ``inline_list`` already emits this via :func:`render_inline_listing`.
    Building a 2013-row listing just to get Classify all pegs the worker.
    """
    specs = [
        spec
        for spec in iter_spec_leaves(review_specs)
        if spec.get("type") == "PopulateButton" and _populate_all_flag(spec)
    ]
    if not specs:
        return ""
    items = []
    for spec in specs:
        items.append('<li class="inline-entry select-all-entry">')
        items.append(render_populate_all_button(spec, count=count))
        items.append("</li>")
    return (
        '<section class="select-all-section"><ul>'
        + "".join(items)
        + "</ul></section>"
    )


def _listing_row_title(data: dict, idx: Any) -> Any:
    title = data.get("title") or data.get("Title")
    if title:
        return title
    name = data.get("Name")
    if name and idx not in (None, "") and str(idx) != str(name):
        return f"{name} · {idx}"
    return name or idx


def _listing_detail_noun(detail_field: str) -> str:
    key = str(detail_field or "").strip().lower()
    if key == "units":
        return "paragraph"
    if "phrase" in key:
        return "phrase"
    if "ground" in key:
        return "point"
    return "item"


def _listing_row_description(data: dict, *, detail_field: str = "") -> str:
    desc = data.get("description") or data.get("Description") or ""
    if not desc:
        desc = data.get("filename") or ""
    desc = str(desc)
    if not detail_field:
        return desc
    detail_val = data.get(detail_field)
    if not isinstance(detail_val, list):
        return desc
    n = len(detail_val)
    noun = _listing_detail_noun(detail_field)
    count_bit = f"{n} {noun}" if n == 1 else f"{n} {noun}s"
    return f"{desc} · {count_bit}" if desc else count_bit


_LISTING_COLLAPSE_TYPES = frozenset({"Textarea"})


def _listing_extra_widget_html(spec: dict, data: dict, idx: Any) -> str:
    """Render a listing extra; Textareas sit in a closed ``<details>``."""
    field = spec.get("field", "")
    value = data.get(field) if field else None
    if spec.get("type") not in _LISTING_COLLAPSE_TYPES:
        return render_widget(spec, value, data, record_index=idx)
    args = spec.get("args") or {}
    label = args.get("description") or field or "Notes"
    inner_spec = dict(spec)
    inner_args = dict(args)
    inner_args["description"] = ""
    inner_spec["args"] = inner_args
    inner = render_widget(inner_spec, value, data, record_index=idx)
    return (
        f'<details class="entry-detail entry-extra-collapse">'
        f"<summary>{_escape(str(label))}</summary>"
        f'<div class="entry-detail-body entry-widget-body">{inner}</div>'
        f"</details>"
    )


def _listing_detail_text(value: Any) -> str:
    """Plain text for ``display.detail_field`` (string or list of unit dicts)."""
    if value is None or value == "":
        return ""
    if isinstance(value, list):
        if not value:
            return ""
        if all(isinstance(item, dict) for item in value):
            blocks: list[str] = []
            for i, item in enumerate(value, 1):
                phrase = item.get("phrase")
                if phrase not in (None, "") or item.get("kind") not in (None, ""):
                    kind = item.get("kind") or ""
                    header = f"{i}."
                    if kind:
                        header += f" [{kind}]"
                    basis = item.get("basis")
                    if basis not in (None, ""):
                        header += f" [{basis}]"
                    if item.get("embedding"):
                        header += " embedded"
                    body = str(phrase or "").strip()
                    blocks.append(f"{header} {body}".strip() if body else header)
                    continue
                ident = item.get("unit_id") or item.get("id") or i
                words = item.get("word_count")
                text = item.get("text") or item.get("body") or ""
                header = f"{i}. {ident}"
                if words not in (None, ""):
                    header += f" ({words} words)"
                blocks.append(f"{header}\n{text}" if text else header)
            return "\n\n".join(blocks)
        return "\n".join(str(item) for item in value if item not in (None, ""))
    return str(value).strip()


def _version_badge(data: dict) -> str:
    """Render ``referia_config_version`` (or ``version``) as a compact badge."""
    raw = data.get("referia_config_version")
    if raw is None or raw == "":
        raw = data.get("version")
    if raw is None or raw == "":
        return ""
    return f'<span class="badge-version">v{_escape(raw)}</span>'


def _listing_page_href(
    path: str,
    *,
    offset: int | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> str:
    """Build ``/listing-page?...`` for CIP-0020 append/page navigation."""
    query: dict[str, str] = {}
    if offset:
        query["list_offset"] = str(int(offset))
    if page:
        query["list_page"] = str(int(page))
    if page_size is not None and int(page_size) not in (50, 0):
        query["list_page_size"] = str(int(page_size))
    qs = urlencode(query)
    return f"{path}?{qs}" if qs else path


def _listing_hx_attrs(href: str, *, target: str, swap: str, select: str = "") -> str:
    extra = f' hx-select="{_escape(select)}"' if select else ""
    return (
        f'hx-get="{_escape(href)}" '
        f'hx-target="{_escape(target)}" '
        f'hx-swap="{_escape(swap)}"{extra}'
    )


def render_listing_window_nav(
    window: dict,
    *,
    listing_path: str = "/listing-page",
    htmx: bool = True,
) -> str:
    """Sentinel (append) or pager (page) for a CIP-0020 listing window.

    *htmx* False is the Jupyter path: Load more / Prev / Next as plain links.
    """
    remaining = int(window.get("remaining") or 0)
    paging = str(window.get("paging") or "append")
    page_size = int(window.get("page_size") or 0)
    offset = int(window.get("offset") or 0)
    page = int(window.get("page") or 1)
    pages = int(window.get("pages") or 1)
    if page_size == 0:
        return ""
    if paging == "page":
        prev_page = page - 1
        next_page = page + 1
        prev_href = _listing_page_href(
            listing_path, page=prev_page, page_size=page_size
        )
        next_href = _listing_page_href(
            listing_path, page=next_page, page_size=page_size
        )
        if htmx:
            prev = (
                f'<button type="button" class="listing-page-prev" '
                f'{_listing_hx_attrs(prev_href, target="#inline-listing-region", swap="innerHTML")} '
                f'{"disabled" if page <= 1 else ""}>Previous</button>'
            )
            nxt = (
                f'<button type="button" class="listing-page-next" '
                f'{_listing_hx_attrs(next_href, target="#inline-listing-region", swap="innerHTML")} '
                f'{"disabled" if page >= pages else ""}>Next</button>'
            )
        else:
            prev = (
                f'<a class="listing-page-prev" href="{_escape(prev_href)}">Previous</a>'
                if page > 1
                else '<span class="listing-page-prev is-disabled">Previous</span>'
            )
            nxt = (
                f'<a class="listing-page-next" href="{_escape(next_href)}">Next</a>'
                if page < pages
                else '<span class="listing-page-next is-disabled">Next</span>'
            )
        return (
            f'<nav class="listing-pager" aria-label="Listing pages">'
            f"{prev}"
            f'<span class="listing-page-status">Page {page} of {pages}</span>'
            f"{nxt}"
            f"</nav>"
        )
    if remaining <= 0:
        return ""
    next_offset = offset + page_size
    href = _listing_page_href(
        listing_path, offset=next_offset, page_size=page_size
    )
    if htmx:
        hx = _listing_hx_attrs(
            href,
            target="#inline-listing-rows",
            swap="beforeend",
            select=".listing-page-chunk > *",
        )
        return (
            f'<div id="listing-sentinel" class="listing-sentinel" '
            f'{hx} hx-trigger="revealed">'
            f'<button type="button" class="load-more" {hx}>Load more</button>'
            f"</div>"
        )
    return (
        f'<div id="listing-sentinel" class="listing-sentinel">'
        f'<a class="load-more" href="{_escape(href)}">Load more</a>'
        f"</div>"
    )


def render_inline_listing(
    entries: list[dict],
    review_specs: list[dict],
    *,
    group_by: str = "directory",
    detail_field: str | None = None,
    documents: list[dict] | None = None,
    working_count: int | None = None,
    window: dict | None = None,
    listing_path: str = "/listing-page",
    fragment: bool = False,
    htmx: bool = True,
) -> str:
    """Directory-listing style list for ``display.layout: inline_list``.

    Each *entry* is a dict with keys:
    ``index``, ``data`` (row dict), optional ``href``, optional ``group``.
    A leading Complete checkbox is promoted when ``review`` has
    ``field: complete``; remaining widgets render as compact extras.
    When a complete field exists, a select-all row is prepended.
    PopulateButtons also get a listing-chrome ``… all`` row that posts
    ``/populate-all/{field}``.

    *group_by* controls section heading style (``directory`` adds a trailing
    slash; ``version`` does not).

    *detail_field* (from ``display.detail_field``) optionally names a tall
    column whose non-empty value is shown in a closed ``<details>`` under
    the row (e.g. ``abstract``).

    *documents* are per-row Create-document actions (e.g. Email feedback).
    Each button posts ``index`` so generation uses that listing row, not
    the session's current record.

    CIP-0020: *working_count* is the filtered set size (populate-all /
    select-all labels). *window* adds append sentinel or pager chrome.
    *fragment* is the HTMX listing-page response (rows + nav, no filter bar).
    *htmx* False is Jupyter: Load more / Prev / Next as ordinary links.
    """
    complete_spec, extra_specs = _split_review_specs_for_listing(review_specs)
    populate_specs = [
        spec for spec in extra_specs if spec.get("type") == "PopulateButton"
    ]
    chrome_specs = [
        spec
        for spec in (review_specs or [])
        if isinstance(spec, dict) and spec.get("type") == "Section"
    ]
    detail_key = str(detail_field).strip() if detail_field else ""
    complete_field = (
        str(complete_spec.get("field")) if complete_spec else "complete"
    )

    # Group by entry["group"] preserving first-seen order.
    groups: list[tuple[str, list[dict]]] = []
    seen: dict[str, list[dict]] = {}
    for entry in entries:
        group = str(entry.get("group") or "")
        if group not in seen:
            seen[group] = []
            groups.append((group, seen[group]))
        seen[group].append(entry)

    if not entries and not chrome_specs:
        return '<p class="no-rows">No rows match the current filters.</p>'

    sections: list[str] = ['<div class="inline-listing">']
    if chrome_specs and not fragment:
        chrome_data = (entries[0].get("data") if entries else {}) or {}
        token = _listing_chrome_ctx.set(True)
        try:
            chrome_html = render_form(
                chrome_specs, chrome_data, form_id="listing-chrome-form"
            )
        finally:
            _listing_chrome_ctx.reset(token)
        sections.append(f'<section class="listing-chrome">{chrome_html}</section>')
    if not entries:
        sections.append('<p class="no-rows">No rows match the current filters.</p>')
        sections.append("</div>")
        return "\n".join(sections)
    if not fragment and (complete_spec is not None or populate_specs):
        sections.append('<section class="select-all-section">')
        sections.append("<ul>")
        if complete_spec is not None:
            all_done = all(
                bool((entry.get("data") or {}).get(complete_field))
                for entry in entries
            )
            sections.append('<li class="inline-entry select-all-entry">')
            sections.append(
                render_select_all_checkbox(
                    all_done,
                    field=complete_field,
                    count=(
                        working_count if working_count is not None else len(entries)
                    ),
                )
            )
            sections.append("</li>")
        for spec in populate_specs:
            sections.append('<li class="inline-entry select-all-entry">')
            sections.append(
                render_populate_all_button(
                    spec,
                    count=(
                        working_count if working_count is not None else len(entries)
                    ),
                    entries=entries,
                )
            )
            sections.append("</li>")
        sections.append("</ul>")
        sections.append("</section>")

    row_sections: list[str] = []
    for group_name, group_entries in groups:
        row_sections.append("<section>")
        if group_name:
            heading = (
                f"{_escape(group_name)}/"
                if group_by == "directory"
                else _escape(group_name)
            )
            row_sections.append(f"<h2>{heading}</h2>")
        row_sections.append("<ul>")
        for entry in group_entries:
            idx = entry.get("index")
            data = entry.get("data") or {}
            href = entry.get("href")
            title = _listing_row_title(data, idx)
            date = data.get("date") or data.get("Date") or ""
            desc = _listing_row_description(data, detail_field=detail_key)
            complete_val = data.get(complete_field)
            is_complete = bool(complete_val)
            li_class = "inline-entry"
            if is_complete:
                li_class += " is-complete"

            row_sections.append(
                f'<li class="{li_class}" data-index="{_escape(idx)}">'
            )
            if complete_spec is not None:
                row_sections.append(
                    render_complete_checkbox(
                        complete_val, record_index=idx, field=complete_field
                    )
                )
            row_sections.append('<div class="entry-main">')
            if href:
                row_sections.append(
                    f'<a class="entry-title" href="{_escape(href)}" '
                    f'target="_blank" rel="noopener noreferrer">'
                    f"{_escape(title)}</a>"
                )
            else:
                row_sections.append(
                    f'<span class="entry-title">{_escape(title)}</span>'
                )
            if is_complete:
                row_sections.append(
                    '<span class="badge-complete">complete</span>'
                )
            version_html = _version_badge(data)
            if version_html:
                row_sections.append(version_html)
            if date:
                row_sections.append(
                    f'<span class="date">{_escape(date)}</span>'
                )
            if desc:
                row_sections.append(
                    f'<span class="desc">{_escape(desc)}</span>'
                )
            if detail_key:
                detail_val = data.get(detail_key)
                if detail_val is None or detail_val == "":
                    for k, v in data.items():
                        if str(k).lower() == detail_key.lower():
                            detail_val = v
                            break
                detail_text = _listing_detail_text(detail_val)
                if detail_text:
                    label = {
                        "units": "Units",
                        "extraction_phrases": "Phrases",
                    }.get(
                        detail_key,
                        detail_key.replace("_", " ").strip().title() or "Detail",
                    )
                    row_sections.append(
                        f'<details class="entry-detail" '
                        f'data-detail-field="{_escape(detail_key)}">'
                        f"<summary>{_escape(label)}</summary>"
                        f'<div class="entry-detail-body">'
                        f"{_escape(detail_text)}"
                        f"</div></details>"
                    )
            extras_html = []
            if extra_specs:
                for spec in extra_specs:
                    extras_html.append(
                        _listing_extra_widget_html(spec, data, idx)
                    )
            row_docs = ""
            if documents:
                row_docs = render_document_actions(
                    documents=documents,
                    data=data,
                    record_index=idx,
                    container_id=(
                        f"row-document-actions-{_widget_dom_id(str(idx))}"
                    ),
                )
            if extras_html or row_docs:
                row_sections.append(
                    '<div class="entry-extras">'
                    + "\n".join(extras_html)
                    + row_docs
                    + "</div>"
                )
            row_sections.append("</div>")
            row_sections.append("</li>")
        row_sections.append("</ul>")
        row_sections.append("</section>")

    rows_html = "\n".join(row_sections)
    nav = (
        render_listing_window_nav(
            window, listing_path=listing_path, htmx=htmx
        )
        if window
        else ""
    )
    if fragment:
        paging = str((window or {}).get("paging") or "append")
        if paging == "page":
            return (
                f'<div id="inline-listing-rows">{rows_html}</div>\n{nav}'
            )
        chunk = f'<div class="listing-page-chunk">{rows_html}</div>'
        if not htmx:
            return f"{chunk}\n{nav}" if nav else chunk
        if nav:
            sentinel = nav.replace(
                'id="listing-sentinel"',
                'id="listing-sentinel" hx-swap-oob="outerHTML"',
                1,
            )
        else:
            sentinel = (
                '<div id="listing-sentinel" hx-swap-oob="outerHTML"></div>'
            )
        return f"{chunk}\n{sentinel}"

    sections.append('<div id="inline-listing-region">')
    sections.append(f'<div id="inline-listing-rows">{rows_html}</div>')
    if nav:
        sections.append(nav)
    sections.append("</div>")
    sections.append("</div>")
    return "\n".join(sections)


def render_document_actions(
    documents: list[dict] | None = None,
    summary_documents: list[dict] | None = None,
    data: dict | None = None,
    *,
    record_index: Any = None,
    container_id: str = "nav-document-actions",
) -> str:
    """HTML for Create / Create Summary document buttons (nav chrome).

    Button specs come from ``WebReviewer.list_document_entries``.  HTMX posts
    use unprefixed paths (``base.html`` rewrites them in root-server mode).

    Optional *data* evaluates each entry's ``visible_if`` (same rules as review
    widgets).  The container always has ``id="nav-document-actions"`` so field
    updates can OOB-swap it when visibility changes.

    When *record_index* is set (inline_list rows), each button includes
    ``hx-vals`` so generation targets that row.  *container_id* must then be
    unique per row so a nav OOB swap does not replace the listing buttons.

    Returns an empty string when there are no document actions at all.
    """
    action_entries = list(documents or []) + list(summary_documents or [])
    if not action_entries:
        return ""
    token = (
        _record_index_ctx.set(record_index) if record_index is not None else None
    )
    try:
        extra_class = " row-document-actions" if record_index is not None else ""
        extra_hx = ""
        ctx_index = _record_index_ctx.get()
        if ctx_index is not None:
            vals = _escape(json.dumps({"index": str(ctx_index)}))
            extra_hx = f' hx-vals="{vals}"'
        parts = [
            f'<div class="nav-document-actions{extra_class}" '
            f'id="{_escape(container_id)}">'
        ]
        for entry in action_entries:
            if data is not None and entry.get("visible_if") is not None:
                if _visibility_style(entry, data):
                    continue
            n = int(entry.get("n") or 0)
            label = _escape(str(entry.get("label") or "Create document"))
            if entry.get("summary"):
                action = f"/generate-summary-document/{n}"
            else:
                action = f"/generate-document/{n}"
            parts.append(
                f'<button type="button" class="widget-button document-button" '
                f'hx-post="{_escape(action)}" hx-target="#status-bar" '
                f'hx-swap="innerHTML focus-scroll:false" '
                f'hx-disabled-elt="this"{extra_hx}>'
                f"{label}</button>"
            )
        parts.append("</div>")
        return "\n".join(parts)
    finally:
        if token is not None:
            _record_index_ctx.reset(token)


def render_document_panel(
    pdfs: list[dict],
    urls: list[dict],
    prefix: str = "",
    current_index: Any = None,
    data: dict | None = None,
) -> str:
    """HTML for PDFs and URL links in the document column.

    Create-document actions live in the panel nav via
    :func:`render_document_actions` (not in this panel).

    *prefix* is the root-server config path (e.g. ``/theses/examined/introduction``)
    or empty in single-config mode.  Iframe ``src`` values must include it;
    HTMX prefix rewriting does not apply to ``<iframe>`` requests.

    *current_index* is appended as ``?index=`` so each record has a distinct
    document URL (see backlog ``2026-10-07_web-record-document-index-in-url``).

    Optional *data* evaluates each PDF entry's ``visible_if`` (same rules as
    review widgets) so missing chapters can be omitted from the panel.
    """
    from urllib.parse import quote

    row = data or {}
    visible_pdfs = []
    for entry in pdfs or []:
        if entry.get("visible_if") is not None and _visibility_style(entry, row):
            continue
        visible_pdfs.append(entry)
    pdfs = visible_pdfs
    if not pdfs and not urls:
        return ""
    index_q = ""
    if current_index is not None:
        index_q = f"?index={quote(str(current_index), safe='')}"
    parts = ['<div class="document-panel">', "<h2>Documents</h2>"]
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
                f'hx-swap="innerHTML focus-scroll:false" hx-disabled-elt="this">'
                f"Prepare / download PDF</button>"
            )
        parts.append("</details>")
    parts.append("</div>")
    return "\n".join(parts)
