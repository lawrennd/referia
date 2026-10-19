"""Interactive viewer entry helpers (CIP-0011).

Typed entries under ``viewer:`` (e.g. ``PlotlyFigure``) may declare ``on:`` /
``highlight:`` bindings that share the same field store as ``review:``.
Liquid / Markdown entries without ``type:`` / ``on:`` remain one-way.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, MutableMapping, Sequence

# Figure / image panes (CIP-0011) plus review-style chrome allowed on the
# viewer side (focus selector, Propose split, etc.).
VIEWER_CHROME_TYPES = frozenset(
    {
        "Dropdown",
        "Select",
        "PopulateButton",
        "Textarea",
        "Text",
        "TextBox",
        "IntText",
        "BoundedIntText",
        "FloatText",
        "BoundedFloatText",
        "Checkbox",
        "RadioButtons",
        "Label",
        "HTML",
    }
)
INTERACTIVE_VIEWER_TYPES = frozenset({"PlotlyFigure", "StaticImage"}) | VIEWER_CHROME_TYPES
DEFAULT_VIEWER_TYPE = "Markdown"


def normalize_viewer_entry(
    spec: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a copy of *spec* with YAML 1.1 boolean-key quirks repaired.

    PyYAML maps unquoted ``on:`` / ``off:`` to boolean ``True`` / ``False``
    keys.  Interactive bindings live under the string key ``\"on\"``, so we
    promote ``True`` → ``\"on\"`` (and ``False`` → ``\"off\"``) when the
    string form is absent.
    """
    if not isinstance(spec, Mapping):
        return {}
    out = dict(spec)
    if True in out and "on" not in out:
        out["on"] = out.pop(True)
    if False in out and "off" not in out:
        out["off"] = out.pop(False)
    return out


def viewer_entry_type(spec: Mapping[str, Any] | None) -> str:
    """Return the viewer entry type (default Markdown when omitted)."""
    if not isinstance(spec, Mapping):
        return DEFAULT_VIEWER_TYPE
    raw = spec.get("type")
    if raw is None or raw == "":
        return DEFAULT_VIEWER_TYPE
    return str(raw)


def is_interactive_viewer_type(spec: Mapping[str, Any] | None) -> bool:
    """True when *spec* is a typed interactive figure or viewer-chrome widget."""
    return viewer_entry_type(spec) in INTERACTIVE_VIEWER_TYPES


def is_viewer_chrome_type(spec: Mapping[str, Any] | None) -> bool:
    """True when *spec* is a review-style widget hosted in the viewer pane."""
    return viewer_entry_type(spec) in VIEWER_CHROME_TYPES


def is_liquid_viewer(spec: Mapping[str, Any] | None) -> bool:
    """True when the entry should use the one-way Liquid/Markdown path."""
    return not is_interactive_viewer_type(spec)


def click_point_actions(spec: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Return normalised ``on.click_point`` ``set_field`` actions.

    Each action is ``{"set_field": str, "from": str}``.  Non-dict / incomplete
    entries are skipped.
    """
    spec = normalize_viewer_entry(spec)
    on = spec.get("on")
    if not isinstance(on, Mapping):
        return []
    raw = on.get("click_point")
    if raw is None:
        return []
    if isinstance(raw, Mapping):
        items: Sequence[Any] = [raw]
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        items = raw
    else:
        return []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        field = item.get("set_field")
        source = item.get("from")
        if not field or source is None or source == "":
            continue
        out.append({"set_field": str(field), "from": str(source)})
    return out


def highlight_binding(spec: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return ``{"from_field": ..., "mode": ...}`` or ``None``."""
    spec = normalize_viewer_entry(spec)
    hl = spec.get("highlight")
    if not isinstance(hl, Mapping):
        return None
    from_field = hl.get("from_field")
    if not from_field:
        return None
    mode = hl.get("mode") or "default"
    return {"from_field": str(from_field), "mode": str(mode)}


def figure_source_binding(spec: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return ``{"map_field": ..., "key_field": ...}`` for focus-driven plane swap.

    YAML::

        figure_source:
          map_field: uq_by_topic   # dict[topic_key → Plotly figure]
          key_field: focus_topic   # which key to show

    When set, the base figure is ``data[map_field][data[key_field]]`` instead
    of a single static ``field:`` value.  ``field:`` remains a writable cache
    (e.g. after Propose split) and a fallback when the map/key is missing.
    """
    spec = normalize_viewer_entry(spec)
    src = spec.get("figure_source")
    if not isinstance(src, Mapping):
        return None
    map_field = src.get("map_field")
    key_field = src.get("key_field")
    if not map_field or not key_field:
        return None
    return {"map_field": str(map_field), "key_field": str(key_field)}


def resolve_figure_payload(
    get_value,
    spec: Mapping[str, Any] | None,
) -> Any:
    """Load raw figure JSON from ``figure_source`` or fallback ``field``.

    *get_value* is typically ``reviewer.get_value``.  Missing map keys fall
    back to ``spec["field"]``.
    """
    spec = normalize_viewer_entry(spec)
    src = figure_source_binding(spec)
    if src is not None:
        try:
            mapping = get_value(src["map_field"])
        except Exception:
            mapping = None
        try:
            key = get_value(src["key_field"])
        except Exception:
            key = None
        if isinstance(mapping, Mapping) and key is not None and key in mapping:
            return mapping[key]
        # Soft fallback: first entry in the map
        if isinstance(mapping, Mapping) and mapping:
            return next(iter(mapping.values()))
    field = spec.get("field")
    if field:
        try:
            return get_value(str(field))
        except Exception:
            return None
    return None


PLOTLY_SIZE_MODES = frozenset({"figure", "container"})


def plotly_size_options(spec: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return Plotly sizing options from a viewer entry ``size:`` block.

    YAML::

        size:
          mode: figure      # honor layout width/height from the figure JSON
          # mode: container  # grow with the pane; ignore fixed layout size
          observe: true     # ResizeObserver → Plotly.Plots.resize (splitter)
          aspect_ratio: 4/3 # optional; CSS aspect-ratio when mode=container

    A bare string ``size: container`` is accepted as shorthand for
    ``mode: container``.  Defaults: ``mode=figure``, ``observe=true`` (so
    splitter width changes still restyle fixed-height figures).
    """
    spec = normalize_viewer_entry(spec)
    mode = "figure"
    observe = True
    aspect_ratio: str | None = None
    raw = spec.get("size")
    if isinstance(raw, str):
        token = raw.strip().lower()
        if token in PLOTLY_SIZE_MODES:
            mode = token
    elif isinstance(raw, Mapping):
        m = raw.get("mode", raw.get("fit"))
        if m is not None and str(m).strip().lower() in PLOTLY_SIZE_MODES:
            mode = str(m).strip().lower()
        if "observe" in raw:
            observe = bool(raw.get("observe"))
        ar = raw.get("aspect_ratio", raw.get("aspect"))
        if ar is not None and str(ar).strip() != "":
            aspect_ratio = str(ar).strip().replace(":", "/")
    if mode == "container" and aspect_ratio is None:
        aspect_ratio = "4/3"
    return {
        "mode": mode,
        "observe": observe,
        "aspect_ratio": aspect_ratio,
    }


def apply_plotly_size(
    figure: Mapping[str, Any] | None,
    *,
    mode: str = "figure",
) -> dict[str, Any] | None:
    """Adjust figure layout for ``size.mode``.

    ``container`` sets ``autosize`` and drops fixed ``layout.height`` /
    ``layout.width`` so the plot fills its DOM pane.  ``figure`` leaves
    the payload unchanged.
    """
    parsed = parse_figure_spec(figure)
    if parsed is None:
        return None
    if mode != "container":
        return parsed
    out = dict(parsed)
    layout = dict(parsed.get("layout") or {})
    layout["autosize"] = True
    layout.pop("height", None)
    layout.pop("width", None)
    out["layout"] = layout
    return out


def resolve_path(payload: Any, path: str) -> Any:
    """Resolve a dotted path against a mapping / sequence / object.

    Supports ``customdata.phrase``, ``customdata.0.topic``, and plain keys.
    Missing segments return ``None``.
    """
    if path is None or path == "":
        return None
    parts = str(path).split(".")
    cur: Any = payload
    for part in parts:
        if cur is None:
            return None
        if isinstance(cur, Mapping):
            cur = cur.get(part)
            continue
        if isinstance(cur, Sequence) and not isinstance(cur, (str, bytes)):
            try:
                idx = int(part)
            except ValueError:
                return None
            if idx < 0 or idx >= len(cur):
                return None
            cur = cur[idx]
            continue
        cur = getattr(cur, part, None)
    return cur


def field_updates_from_click(
    spec: Mapping[str, Any] | None,
    click_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Map ``on.click_point`` bindings to ``{field: value}`` from a click payload.

    The payload should expose the same structure Plotly uses in events
    (typically including ``customdata``).  Unresolvable paths are omitted.
    """
    if not isinstance(click_payload, Mapping):
        return {}
    updates: dict[str, Any] = {}
    for action in click_point_actions(spec):
        value = resolve_path(click_payload, action["from"])
        if value is None:
            continue
        updates[action["set_field"]] = value
    return updates


def parse_figure_spec(raw: Any) -> dict[str, Any] | None:
    """Coerce a field value into a Plotly-like ``{data, layout}`` dict."""
    if raw is None:
        return None
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return None
    # Bare trace list stored in the field.
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, Mapping)):
        return {"data": list(raw), "layout": {}}
    if not isinstance(raw, Mapping):
        return None
    fig = dict(raw)
    if "data" not in fig and "layout" not in fig:
        return None
    fig.setdefault("data", [])
    fig.setdefault("layout", {})
    return fig


def apply_highlight(
    figure: Mapping[str, Any] | None,
    *,
    selected: Any,
    mode: str = "default",
) -> dict[str, Any] | None:
    """Return a shallow-copied figure with highlight metadata applied.

    v1 marks matching points via ``marker.opacity`` when traces expose
    ``customdata`` topic (or the selected value appears in customdata).
    Unknown modes fall back to ``default``.  Returns ``None`` if *figure*
    is missing.
    """
    parsed = parse_figure_spec(figure)
    if parsed is None:
        return None
    data = []
    for trace in parsed.get("data") or []:
        if not isinstance(trace, Mapping):
            data.append(trace)
            continue
        t = dict(trace)
        custom = t.get("customdata")
        if selected is None or custom is None:
            data.append(t)
            continue
        opacities: list[float] = []
        matched_any = False
        seq = custom if isinstance(custom, Sequence) and not isinstance(custom, (str, bytes)) else [custom]
        for item in seq:
            hit = _customdata_matches(item, selected)
            matched_any = matched_any or hit
            if mode == "responsibility_ink" and isinstance(item, Mapping):
                mass = item.get("responsibilities")
                if isinstance(mass, Mapping) and selected in mass:
                    try:
                        opacities.append(max(0.15, min(1.0, float(mass[selected]))))
                        continue
                    except (TypeError, ValueError):
                        pass
            opacities.append(1.0 if hit else 0.25)
        if matched_any or opacities:
            marker = dict(t.get("marker") or {})
            marker["opacity"] = opacities
            t["marker"] = marker
        data.append(t)
    out = dict(parsed)
    out["data"] = data
    out["layout"] = dict(parsed.get("layout") or {})
    return out


def _customdata_matches(item: Any, selected: Any) -> bool:
    if item == selected:
        return True
    if isinstance(item, Mapping):
        for key in ("topic", "selected_topic", "id", "phrase"):
            if key in item and item[key] == selected:
                return True
    return False


def viewers_highlighting_field(
    specs: Sequence[Mapping[str, Any]] | None,
    column: str,
) -> list[dict[str, Any]]:
    """Return interactive viewer specs whose highlight watches *column*."""
    if not specs:
        return []
    out: list[dict[str, Any]] = []
    for spec in specs:
        if not is_interactive_viewer_type(spec):
            continue
        hl = highlight_binding(spec)
        if hl and hl["from_field"] == column:
            out.append(dict(spec))
    return out


def viewers_watching_field(
    specs: Sequence[Mapping[str, Any]] | None,
    column: str,
) -> list[dict[str, Any]]:
    """Return Plotly viewers that should restyle when *column* changes.

    Watches ``highlight.from_field`` and ``figure_source.key_field`` /
    ``figure_source.map_field``.
    """
    if not specs:
        return []
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for spec in specs:
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
        sid = id(spec)
        if sid in seen:
            continue
        seen.add(sid)
        out.append(dict(spec))
    return out
