"""CIP-0018 stacked inherit view — display-only composition of ancestor layers.

Query parameters select among named presentations already implemented in
referia. They must not load files, change jails, or widen writes (CIP-000E).
"""

from __future__ import annotations

import logging
import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import urlencode

log = logging.getLogger(__name__)

PARENT_ASSESSOR_LINK_KEY = "_parent_assessor_link"

ALLOWED_QUERY_KEYS = frozenset({"compose", "inherit_viewer", "inherit_review"})
FORBIDDEN_QUERY_KEYS = frozenset(
    {
        "writable",
        "directory",
        "filename",
        "path",
        "user_file",
        "allowed_roots",
    }
)
COMPOSE_VALUES = frozenset({"link", "stacked"})
BOOL_TRUE = frozenset({"1", "true"})
BOOL_FALSE = frozenset({"0", "false"})

_http_query: ContextVar[Mapping[str, Any] | None] = ContextVar(
    "referia_inherit_view_query", default=None
)


@dataclass(frozen=True)
class InterfaceLayer:
    """One Interface node in root-first inherit order."""

    title: str
    directory: str
    viewer: list
    review: list
    writable: bool = True
    is_self: bool = False


@dataclass(frozen=True)
class InheritViewOptions:
    """Allowlisted inherit presentation for one request (or Jupyter YAML)."""

    compose: str = "link"
    inherit_viewer: bool = True
    inherit_review: bool = True
    source: str = "default"

    def as_query_dict(self, *, include_compose_link: bool = False) -> dict[str, str]:
        """Query items to preserve on HTMX fetches and parent links."""
        out: dict[str, str] = {}
        if self.compose == "stacked":
            out["compose"] = "stacked"
            if not self.inherit_viewer:
                out["inherit_viewer"] = "0"
            if not self.inherit_review:
                out["inherit_review"] = "0"
        elif include_compose_link:
            out["compose"] = "link"
        return out


def set_request_query(query: Mapping[str, Any] | None):
    """Bind this HTTP request's query mapping (Starlette ``QueryParams``)."""
    return _http_query.set(query)


def reset_request_query(token) -> None:
    _http_query.reset(token)


def current_query() -> Mapping[str, Any] | None:
    return _http_query.get()


def yaml_compose_from_interface(interface: Any) -> str | None:
    """Author default ``inherit.compose`` from the child's own ``_data``."""
    data = getattr(interface, "_data", None)
    if not isinstance(data, dict):
        return None
    inherit = data.get("inherit")
    if not isinstance(inherit, dict):
        return None
    compose = inherit.get("compose")
    return str(compose) if compose is not None else None


def interface_has_parent(interface: Any) -> bool:
    """True for a real Interface with a loaded parent (not a MagicMock)."""
    if getattr(interface, "_parent", None) is None:
        return False
    return isinstance(getattr(interface, "_data", None), dict)


def view_options_for_interface(
    interface: Any, query: Mapping[str, Any] | None = None
) -> InheritViewOptions:
    if query is None:
        query = current_query()
    return parse_inherit_view_options(
        query=query,
        yaml_compose=yaml_compose_from_interface(interface),
    )


def parse_inherit_view_options(
    query: Mapping[str, Any] | str | None = None,
    yaml_compose: str | None = None,
) -> InheritViewOptions:
    """Precedence: query → YAML author default → ``link``.

    Unknown or invalid values are ignored (logged, never echoed). Extra keys
    including ``writable`` never change writability or load paths.
    """
    compose = "link"
    source = "default"
    yaml_parsed = _parse_compose(yaml_compose, origin="yaml")
    if yaml_parsed:
        compose = yaml_parsed
        source = "yaml"

    qmap = _query_map(query)
    for key in qmap:
        if key in FORBIDDEN_QUERY_KEYS:
            log.warning("Ignoring inherit view query parameter %s", key)

    raw_compose = qmap.get("compose")
    if raw_compose is not None:
        parsed = _parse_compose(raw_compose, origin="query")
        if parsed:
            compose = parsed
            source = "query"

    inherit_viewer = True
    inherit_review = True
    if compose == "stacked":
        inherit_viewer = _parse_bool(qmap.get("inherit_viewer"), default=True)
        inherit_review = _parse_bool(qmap.get("inherit_review"), default=True)

    return InheritViewOptions(
        compose=compose,
        inherit_viewer=inherit_viewer,
        inherit_review=inherit_review,
        source=source,
    )


def compose_viewer_review(
    interface: Any,
    options: InheritViewOptions,
    *,
    href_for_layer: Callable[[InterfaceLayer], str] | None = None,
) -> tuple[list, list] | None:
    """Build stacked viewer/review specs, or ``None`` to keep today's merge.

    Ancestor entries are wrapped as ``type: Section`` with ``inherited: true``.
    The child's entries stay unwrapped. Tagged parent-assessor link blobs are
    omitted (stacked mode puts an "open in parent" control on the Section).
    """
    if options.compose != "stacked":
        return None
    layers_fn = getattr(interface, "interface_layers", None)
    if not callable(layers_fn):
        return None
    layers = layers_fn()
    if not isinstance(layers, (list, tuple)):
        return None

    viewer_out: list = []
    review_out: list = []
    for layer in layers:
        if not isinstance(layer, InterfaceLayer):
            # Tolerate a 4-tuple from tests / older helpers.
            layer = _coerce_layer(layer)
        v_entries = _without_parent_links(_as_list(layer.viewer))
        r_entries = _as_list(layer.review)
        if layer.is_self:
            viewer_out.extend(v_entries)
            review_out.extend(r_entries)
            continue
        href = href_for_layer(layer) if href_for_layer else ""
        if options.inherit_viewer and v_entries:
            viewer_out.append(_inherited_section(layer, v_entries, href))
        if options.inherit_review and r_entries:
            review_out.append(_inherited_section(layer, r_entries, href))
    return viewer_out, review_out


def inherited_readonly_fields(
    interface: Any, options: InheritViewOptions
) -> set[str]:
    """Ancestor review fields that must not be written when the hop is not writable.

    Fields that also appear on the child's own review stay writable (the child
    widget is the write surface).
    """
    if options.compose != "stacked":
        return set()
    layers_fn = getattr(interface, "interface_layers", None)
    if not callable(layers_fn):
        return set()
    layers = layers_fn()
    if not isinstance(layers, (list, tuple)):
        return set()
    inherited: set[str] = set()
    child: set[str] = set()
    for layer in layers:
        if not isinstance(layer, InterfaceLayer):
            layer = _coerce_layer(layer)
        names = _field_names(layer.review)
        if layer.is_self:
            child |= names
        elif options.inherit_review and not layer.writable:
            inherited |= names
    return inherited - child


def toggle_href(
    options: InheritViewOptions, *, index: Any = None, stacked: bool
) -> str:
    params: dict[str, str] = {}
    if index is not None and str(index) != "":
        params["index"] = str(index)
    if stacked:
        params["compose"] = "stacked"
        extra = options.as_query_dict()
        extra.pop("compose", None)
        params.update(extra)
    else:
        params["compose"] = "link"
    return "?" + urlencode(params)


def toggle_html(options: InheritViewOptions, *, index: Any = None) -> str:
    """Bookmarkable Show/Hide inherited control (not client-only state)."""
    if options.compose == "stacked":
        href = toggle_href(options, index=index, stacked=False)
        label = "Hide inherited"
    else:
        href = toggle_href(options, index=index, stacked=True)
        label = "Show inherited"
    return (
        f'<a class="inherit-view-toggle" href="{_html_escape(href)}">{label}</a>'
    )


def layer_href(
    from_directory: str,
    layer: InterfaceLayer,
    options: InheritViewOptions,
    *,
    index: Any = None,
) -> str:
    """Relative URL from the child config dir to *layer*, plus view params."""
    dest = os.path.expandvars(layer.directory or "")
    src = os.path.expandvars(from_directory or ".")
    try:
        rel = os.path.relpath(dest, src)
    except ValueError:
        rel = dest
    rel = rel.replace("\\", "/")
    if rel in (".", ""):
        rel = "./"
    elif not rel.endswith("/"):
        rel += "/"
    params = options.as_query_dict()
    if index is not None and str(index) != "":
        params["index"] = str(index)
    qs = urlencode(params)
    return rel + (("?" + qs) if qs else "")


def collect_interface_layers(node: Any) -> list[InterfaceLayer]:
    """Walk ``_parent`` root-first. Used by ``Interface.interface_layers()``.

    Prefer ``_layer_viewer`` / ``_layer_review`` snapshots taken in referia's
    ``Interface.__init__`` before lynguine ``_process_parent`` deletes ignored
    keys (including ``review``) from the *parent* node's ``_data``.
    """
    chain: list[Any] = []
    seen: set[int] = set()
    current = node
    while current is not None:
        ident = id(current)
        if ident in seen:
            break
        seen.add(ident)
        chain.append(current)
        current = getattr(current, "_parent", None)
    chain.reverse()
    layers: list[InterfaceLayer] = []
    last = len(chain) - 1
    for i, item in enumerate(chain):
        data = getattr(item, "_data", None)
        if not isinstance(data, dict):
            data = {}
        directory = (
            getattr(item, "_directory", None)
            or getattr(item, "directory", None)
            or ""
        )
        title = getattr(item, "_layer_title", None) or data.get("title")
        if not title:
            title = os.path.basename(str(directory).rstrip(os.sep)) or str(
                directory
            )
        viewer = getattr(item, "_layer_viewer", None)
        if viewer is None:
            viewer = data.get("viewer") or []
        review = getattr(item, "_layer_review", None)
        if review is None:
            review = data.get("review") or []
        is_self = i == last
        writable = bool(getattr(item, "_writable", is_self))
        layers.append(
            InterfaceLayer(
                title=str(title),
                directory=str(directory),
                viewer=_as_list(viewer),
                review=_as_list(review),
                writable=writable,
                is_self=is_self,
            )
        )
    return layers


def _inherited_section(
    layer: InterfaceLayer, entries: list, href: str
) -> dict:
    spec = {
        "type": "Section",
        "title": layer.title,
        "inherited": True,
        "writable": bool(layer.writable),
        "entries": list(entries),
        "args": {"open": True},
    }
    if href:
        spec["parent_href"] = href
    return spec


def _without_parent_links(entries: Iterable) -> list:
    out = []
    for entry in entries:
        if isinstance(entry, dict) and entry.get(PARENT_ASSESSOR_LINK_KEY):
            continue
        out.append(entry)
    return out


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    return [value]


def _field_names(entries: Iterable) -> set[str]:
    names: set[str] = set()
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") in {"Section", "group", "load"}:
            sub = entry.get("entries") or entry.get("children") or []
            names |= _field_names(sub if isinstance(sub, list) else [])
            continue
        field = entry.get("field")
        if isinstance(field, list):
            names.update(str(f) for f in field if f and f != "_")
        elif field and field != "_":
            names.add(str(field))
    return names


def _coerce_layer(layer: Any) -> InterfaceLayer:
    if isinstance(layer, InterfaceLayer):
        return layer
    title, directory, viewer, review = layer[0], layer[1], layer[2], layer[3]
    writable = layer[4] if len(layer) > 4 else True
    is_self = layer[5] if len(layer) > 5 else False
    return InterfaceLayer(
        title=str(title),
        directory=str(directory),
        viewer=_as_list(viewer),
        review=_as_list(review),
        writable=bool(writable),
        is_self=bool(is_self),
    )


def _query_map(query: Mapping[str, Any] | str | None) -> dict[str, str]:
    if query is None:
        return {}
    if isinstance(query, str):
        from urllib.parse import parse_qs

        parsed = parse_qs(query.lstrip("?"), keep_blank_values=True)
        return {
            _norm_key(k): (vals[0] if vals else "")
            for k, vals in parsed.items()
        }
    items = getattr(query, "items", None)
    if not callable(items):
        return {}
    out: dict[str, str] = {}
    for key, value in items():
        nk = _norm_key(key)
        if nk in ALLOWED_QUERY_KEYS or nk in FORBIDDEN_QUERY_KEYS:
            if isinstance(value, (list, tuple)):
                value = value[0] if value else ""
            out[nk] = "" if value is None else str(value)
    return out


def _norm_key(key: Any) -> str:
    return str(key).strip().lower()


def _parse_compose(value: Any, *, origin: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in COMPOSE_VALUES:
        return text
    if text == "":
        return None
    log.warning("Ignoring invalid %s compose value", origin)
    return None


def _parse_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in BOOL_TRUE:
        return True
    if text in BOOL_FALSE:
        return False
    log.warning("Ignoring invalid inherit view boolean query value")
    return default


def _html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
