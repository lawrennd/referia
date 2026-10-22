"""Stateful review session for the referia web display backend.

``WebReviewer`` wraps ``Interface`` and ``CustomDataFrame`` to provide the same
core review semantics as ``Reviewer`` without any ipywidgets dependency.  It is
the data/logic layer consumed by the FastAPI routes in ``referia.web.app``.

Public API
----------
WebReviewer(user_file, directory)
    Construct from a ``_referia.yml`` configuration file.

web_reviewer.index_list() -> list
    All valid record indices.

web_reviewer.get_index() -> object
    The currently active record index.

web_reviewer.set_index(index)
    Switch to a different record.

web_reviewer.get_value(column) -> object
    Current data value for *column* in the active record.

web_reviewer.set_value(column, value)
    Update *column* for the active record and trigger on-change logic
    (timestamps, combinators).

web_reviewer.save_flows()
    Persist data to output files.

web_reviewer.load_flows(reload=False)
    Reload data from source files.

web_reviewer.get_widget_specs() -> list[dict]
    Flat, ordered list of widget spec dicts derived from ``interface["review"]``
    and ``interface["viewer"]``.

web_reviewer.affected_widgets(column) -> set[str]
    Column names whose displayed values may change after *column* is updated
    (``visible_if`` dependents and combinator widget fields — not the whole form).
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Any

import pandas as pd

from lynguine import log as _lynguine_log

log = logging.getLogger(__name__)

# Widget types that contain nested entries rather than being rendered directly.
_CLUSTER_TYPES = frozenset(
    {"group", "load", "composite", "loop", "precompute", "postcompute", "Section"}
)

# Clusters that stay nested for web form rendering (collapsible sections).
_PRESERVE_CLUSTER_TYPES = frozenset({"Section"})

# Widget types that don't carry a data field (no column to refresh).
_NON_FIELD_TYPES = frozenset(
    {"Label", "HTML", "HTMLMath", "Markdown",
     "SaveButton", "ReloadButton", "PopulateButton"}
)

# referia CIP-0010 display layouts (viewer/review chrome).
_VALID_DISPLAY_LAYOUTS = frozenset({"side_by_side", "inline_list"})

# Relative calendar tokens for ``display.filter_defaults`` date bounds.
_RELATIVE_DATE_RE = re.compile(r"^today(?:([+-])(\d+)d)?$", re.IGNORECASE)

# Lynguine store codecs. A ``documents:`` mapping with these types is a named
# store (filename/directory), not a generate-document action. Misusing that
# reserved key produced a "Create yaml" button whose download 404'd.
_STORE_DOCUMENT_TYPES = frozenset(
    {"yaml", "yml", "csv", "excel", "xlsx", "json", "parquet", "pickle"}
)
_DOCUMENT_ACTION_KEYS = frozenset(
    {"content", "body", "header", "footer", "tally", "display", "liquid", "use", "template"}
)


def _is_document_action(doc: Any) -> bool:
    """True when *doc* is a generate-document spec, not a lynguine store."""
    if not isinstance(doc, dict) or "type" not in doc:
        return False
    dtype = str(doc.get("type") or "").strip().casefold()
    if dtype in _STORE_DOCUMENT_TYPES and "filename" in doc:
        if not any(key in doc for key in _DOCUMENT_ACTION_KEYS):
            return False
    return True


def _visible_if_depends_on(condition: Any, column: str) -> bool:
    """True when a widget ``visible_if`` condition references *column*."""
    if isinstance(condition, str):
        return condition == column
    if isinstance(condition, dict):
        return str(condition.get("field") or "") == column
    return False


def resolve_relative_date(value: Any, *, today: date | None = None) -> str:
    """Resolve ``today`` / ``today±Nd`` tokens to ISO dates; pass other strings through."""
    if value is None:
        return ""
    text = str(value).strip()
    match = _RELATIVE_DATE_RE.match(text)
    if not match:
        return text
    base = today or date.today()
    sign, amount = match.group(1), match.group(2)
    if sign is None:
        return base.isoformat()
    delta = timedelta(days=int(amount))
    return (base - delta if sign == "-" else base + delta).isoformat()


def resolve_filter_defaults(
    raw: dict[str, Any], *, today: date | None = None
) -> dict[str, Any]:
    """Normalise ``display.filter_defaults`` for session filter state.

    Booleans become ``\"true\"`` / ``\"false\"``. Nested dicts (e.g. date_range)
    resolve relative date strings on each value. Tristate boolean strings
    (``Any`` / ``True`` / ``False``, any capitalisation) become lowercase
    ``any`` / ``true`` / ``false`` so they match the filter bar and
    ``working_indices``.
    """
    out: dict[str, Any] = {}
    for key, value in raw.items():
        name = str(key)
        if isinstance(value, dict):
            out[name] = {
                str(sub_key): (
                    resolve_relative_date(sub_val, today=today)
                    if isinstance(sub_val, str)
                    else sub_val
                )
                for sub_key, sub_val in value.items()
            }
        elif isinstance(value, bool):
            out[name] = "true" if value else "false"
        elif isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"any", "true", "false"}:
                out[name] = lowered
            else:
                out[name] = resolve_relative_date(value, today=today)
        else:
            out[name] = value
    return out


class WebReviewer:
    """Stateful, widget-free review session for the web backend.

    :param user_file: Name of the YAML configuration file,
        defaults to ``"_referia.yml"``.
    :type user_file: str
    :param directory: Directory that contains the configuration file,
        defaults to ``"."``.  Callers that map a URL path to this directory
        (root-server mode) must validate it with
        ``referia.web.path_safety.safe_path_under_root`` first; this class
        does not re-check path traversal.
    :type directory: str

    Example::

        reviewer = WebReviewer("_referia.yml", "/path/to/review")
        reviewer.set_index(reviewer.index_list()[0])
        value = reviewer.get_value("score")
        reviewer.set_value("score", 5)
        reviewer.save_flows()
    """

    def __init__(
        self,
        user_file: str = "_referia.yml",
        directory: str = ".",
        *,
        allowed_roots: list | None = None,
    ) -> None:
        import os
        from pathlib import Path
        from referia.config.interface import Interface
        from referia.assess.data import CustomDataFrame

        self._directory = str(Path(directory).resolve())
        # WebReviewer is shared with the HTTP web app (routes.py). Keep the
        # CIP-000A path jail on by default. Trusted local Jupyter/CLI helpers
        # (referia.data.Data, referia.display.Scorer) may pass
        # unbounded_paths=True; this class must not.
        #
        # Default roots: review directory + its parent (sibling ``../info``,
        # ``../pdfpages`` layouts). Callers in root-server mode should also
        # pass the serve ``--root`` via *allowed_roots* so configs under that
        # tree (e.g. ``theses/criteria/``) remain readable.
        _config_dir = Path(self._directory)
        _roots: list[str] = [str(_config_dir), str(_config_dir.parent)]
        if allowed_roots:
            for root in allowed_roots:
                if root is None:
                    continue
                resolved = str(Path(root).expanduser().resolve())
                if resolved not in _roots:
                    _roots.append(resolved)
        self._interface = Interface.from_file(
            user_file, self._directory, allowed_roots=_roots
        )

        # Data loading resolves file paths relative to CWD, so temporarily
        # switch to the review directory for the duration of the load.
        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            self._data = CustomDataFrame.from_flow(self._interface)
        finally:
            os.chdir(_orig)

        # Jupyter Reviewer registers these while building widgets; web must
        # do the same so soft-fill / extract runs on index change (CoE
        # 2026-10-18_web-reviewer-skips-precompute-soft-fill).
        self._register_review_computes()
        self._ensure_compute_target_columns()
        # Widget defaults must exist before precompute: Propose/Name read
        # sigma2 / label_model from the row, not from the rendered widget.
        self._field_defaults: dict[str, Any] = self._build_field_defaults()

        indices = list(self._data.index)
        if indices:
            # set_index triggers compute_pre only when the index *changes*.
            # from_flow often already selects the first row, so the first
            # set_index is a no-op for precompute — run it explicitly below.
            self.set_index(indices[0])
            self._apply_field_defaults()
            self._run_review_precompute()
            self._run_interface_compute()

        # Session filter/sort state for display.layout: inline_list (CIP-0010).
        # Seed from ``display.filter_defaults`` when present (Clear restores it).
        self._filter_state: dict[str, Any] = self.get_filter_defaults()

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def index_list(self) -> list:
        """Return all valid record indices as a plain list."""
        return list(self._data.index)

    def get_index(self) -> Any:
        """Return the currently active record index."""
        return self._data.get_index()

    def _resolve_index_label(self, index: Any) -> Any:
        """Map *index* onto a typed label present in ``index_list()``.

        HTTP/HTMX query parameters arrive as strings. Allocation indices may
        be integers (or other non-str types). Prefer exact membership in the
        data index; otherwise accept a unique match where
        ``str(label) == str(index)``. Does not treat integers as positional
        offsets (see backlog ``2026-10-06_web-index-query-string-type``).

        :param index: Label as provided by the caller (typed or string form).
        :return: The typed label to pass to lynguine ``set_index``.
        :raises KeyError: If no matching label exists (or the string match
            is ambiguous).
        """
        data_index = self._data.index
        try:
            if index in data_index:
                return index
        except TypeError:
            pass

        matches = [idx for idx in self.index_list() if str(idx) == str(index)]
        if len(matches) == 1:
            return matches[0]
        raise KeyError(f'Index "{index}" not found in data')

    def set_index(self, index: Any) -> None:
        """Switch the active record to *index*.

        Accepts typed index labels or their string forms (for example
        ``"2"`` when the allocation index uses integer ``2``).

        Chdirs to the review directory while ``compute_pre`` / ``compute_post``
        run so relative paths in compute specs resolve like Jupyter.
        """
        import os

        label = self._resolve_index_label(index)
        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            self._data.set_index(label)
        finally:
            os.chdir(_orig)

    # ------------------------------------------------------------------
    # Display layout (CIP-0010)
    # ------------------------------------------------------------------

    def _display_config(self) -> dict:
        """Return the ``display:`` mapping from the interface (or empty)."""
        display = self._interface.get("display") if hasattr(self._interface, "get") else None
        if display is None:
            try:
                display = self._interface["display"] if "display" in self._interface else None
            except Exception:
                display = None
        return display if isinstance(display, dict) else {}

    def get_display_layout(self) -> str:
        """Return ``display.layout`` from config (default ``side_by_side``).

        :raises ValueError: If the configured layout name is unknown.
        """
        display = self._display_config()
        layout = display.get("layout", "side_by_side")
        if layout is None:
            return "side_by_side"
        layout = str(layout)
        if layout not in _VALID_DISPLAY_LAYOUTS:
            raise ValueError(
                f"Unknown display.layout {layout!r}; "
                f"expected one of {sorted(_VALID_DISPLAY_LAYOUTS)}"
            )
        return layout

    def get_display_detail_field(self) -> str | None:
        """Return ``display.detail_field`` for collapsible inline_list row body.

        When set (e.g. ``abstract``), ``render_inline_listing`` wraps that
        column in a closed ``<details>`` under each row. Empty / missing
        values skip the details chrome.
        """
        raw = self._display_config().get("detail_field")
        if raw is None or raw == "":
            return None
        return str(raw)

    def get_filter_specs(self) -> list:
        """Return ``filters:`` specs from the interface (may be empty)."""
        specs = self._interface.get("filters") if hasattr(self._interface, "get") else None
        if specs is None:
            try:
                specs = self._interface["filters"] if "filters" in self._interface else []
            except Exception:
                specs = []
        return specs if isinstance(specs, list) else []

    def get_sort_specs(self) -> list:
        """Return ``sort:`` specs from the interface (may be empty)."""
        specs = self._interface.get("sort") if hasattr(self._interface, "get") else None
        if specs is None:
            try:
                specs = self._interface["sort"] if "sort" in self._interface else []
            except Exception:
                specs = []
        return specs if isinstance(specs, list) else []

    def get_filter_defaults(self) -> dict[str, Any]:
        """Return resolved ``display.filter_defaults`` (session start / Clear).

        Relative date tokens ``today``, ``today-30d``, ``today+30d`` become
        ISO calendar dates. Boolean values become ``\"true\"`` / ``\"false\"``
        strings to match the filter-bar form state.
        """
        raw = self._display_config().get("filter_defaults")
        if not isinstance(raw, dict):
            return {}
        return resolve_filter_defaults(raw)

    def get_filter_state(self) -> dict[str, Any]:
        """Return the current session filter/sort UI state."""
        if not hasattr(self, "_filter_state") or self._filter_state is None:
            self._filter_state = self.get_filter_defaults()
        return self._filter_state

    def set_filter_state(self, state: dict[str, Any] | None) -> None:
        """Replace session filter/sort UI state."""
        self._filter_state = dict(state or {})

    def clear_filters(self) -> None:
        """Restore session filters to ``display.filter_defaults`` (or empty)."""
        self._filter_state = self.get_filter_defaults()

    def working_indices(self) -> list:
        """Indices after applying session filters and sort (tall working set)."""
        indices = list(self.index_list())
        state = self.get_filter_state()
        saved = None
        try:
            saved = self.get_index()
        except Exception:
            pass

        def _cell(idx: Any, field: str) -> Any:
            try:
                self.set_index(idx)
                return self.get_value(field)
            except Exception:
                try:
                    row = self.get_row_data()
                    return row.get(field)
                except Exception:
                    return None

        try:
            for spec in self.get_filter_specs():
                if not isinstance(spec, dict):
                    continue
                field = spec.get("field")
                if not field:
                    continue
                ftype = str(spec.get("type") or "categorical")
                constraint = state.get(field)
                if ftype == "boolean":
                    # Accept Any/any/empty; capitalised YAML ``Any`` used to
                    # fall through and behave like False (not == "true").
                    if constraint is None or str(constraint).strip().lower() in (
                        "",
                        "any",
                    ):
                        continue
                    want_true = str(constraint).strip().lower() == "true"
                    # Missing/NaN complete counts as not done (matches UI checkbox).
                    indices = [
                        idx
                        for idx in indices
                        if (
                            self._coerce_bool_cell(_cell(idx, field)) is True
                        )
                        is want_true
                    ]
                elif ftype == "date_range":
                    if not isinstance(constraint, dict):
                        continue
                    after = constraint.get("after") or None
                    before = constraint.get("before") or None
                    if not after and not before:
                        continue
                    kept = []
                    for idx in indices:
                        raw = _cell(idx, field)
                        try:
                            ts = pd.to_datetime(raw, errors="coerce")
                        except Exception:
                            ts = pd.NaT
                        if pd.isna(ts):
                            continue
                        if after:
                            try:
                                if ts < pd.to_datetime(after):
                                    continue
                            except Exception:
                                continue
                        if before:
                            try:
                                if ts > pd.to_datetime(before):
                                    continue
                            except Exception:
                                continue
                        kept.append(idx)
                    indices = kept
                elif ftype == "contains":
                    if not isinstance(constraint, dict):
                        continue
                    query = str(constraint.get("query") or "").strip()
                    if not query:
                        continue
                    mode = str(constraint.get("mode") or "words").lower()
                    if mode not in ("words", "exact"):
                        mode = "words"
                    indices = [
                        idx
                        for idx in indices
                        if self._contains_match(_cell(idx, field), query, mode)
                    ]
                else:
                    selected = constraint
                    if not selected:
                        continue
                    if not isinstance(selected, (list, set, tuple)):
                        selected = [selected]
                    selected_strs = {str(v) for v in selected}
                    indices = [
                        idx
                        for idx in indices
                        if str(_cell(idx, field)) in selected_strs
                    ]

            sort_key = state.get("_sort")
            sort_specs = self.get_sort_specs()
            if sort_key and isinstance(sort_key, str) and ":" in sort_key:
                field, order = sort_key.rsplit(":", 1)
                sort_specs = [{"field": field, "order": order}]
            if sort_specs:
                # Stable multi-key sort from last key to first.
                for spec in reversed(sort_specs):
                    if not isinstance(spec, dict):
                        continue
                    field = spec.get("field")
                    if not field:
                        continue
                    order = str(spec.get("order") or "asc").lower()
                    reverse = order == "desc"

                    def _sort_val(idx: Any, _field: str = field) -> Any:
                        val = _cell(idx, _field)
                        try:
                            ts = pd.to_datetime(val, errors="coerce")
                            if not pd.isna(ts):
                                return (0, ts)
                        except Exception:
                            pass
                        if val is None:
                            return (2, "")
                        return (1, str(val))

                    indices = sorted(indices, key=_sort_val, reverse=reverse)
        finally:
            if saved is not None:
                try:
                    self.set_index(saved)
                except Exception:
                    pass
        return indices

    @staticmethod
    def _coerce_bool_cell(val: Any) -> bool | None:
        """Map a cell to True/False/None for tristate boolean filters."""
        import math

        if val is None:
            return None
        if isinstance(val, bool):
            return val
        if isinstance(val, float) and math.isnan(val):
            return None
        if isinstance(val, (int, float)) and val in (0, 1):
            return bool(val)
        text = str(val).strip().lower()
        if text in ("true", "1", "yes"):
            return True
        if text in ("false", "0", "no"):
            return False
        return None

    @staticmethod
    def _contains_match(val: Any, query: str, mode: str = "words") -> bool:
        """Case-insensitive contains match for ``type: contains`` filters.

        *exact*: query appears as a contiguous substring.
        *words*: every whitespace-separated token appears somewhere in the value.
        """
        hay = str(val if val is not None else "").casefold()
        needle = (query or "").strip().casefold()
        if not needle:
            return True
        if mode == "exact":
            return needle in hay
        tokens = [t for t in needle.split() if t]
        if not tokens:
            return True
        return all(token in hay for token in tokens)

    def get_rows(self) -> list[dict]:
        """Build Liquid ``rows`` from the filtered+sorted tall working set.

        Each element is a plain dict of column values for one index, plus
        ``_index`` holding the record index label.
        """
        saved = None
        try:
            saved = self.get_index()
        except Exception:
            pass
        rows: list[dict] = []
        try:
            for idx in self.working_indices():
                self.set_index(idx)
                row = dict(self.get_row_data())
                row["_index"] = idx
                rows.append(row)
        finally:
            if saved is not None:
                try:
                    self.set_index(saved)
                except Exception:
                    pass
        return rows

    # ------------------------------------------------------------------
    # Value access
    # ------------------------------------------------------------------

    def _iter_review_widget_specs(self, entries: list | None = None):
        """Yield field-bearing widget specs, including nested ``Section``s."""
        if entries is None:
            entries = self._review_raw()
        for spec in entries or []:
            if not isinstance(spec, dict):
                continue
            if spec.get("type") in _CLUSTER_TYPES:
                sub = spec.get(
                    "entries",
                    spec.get("children", spec.get("specifications", [])),
                )
                yield from self._iter_review_widget_specs(
                    sub if isinstance(sub, list) else [sub]
                )
                continue
            yield spec

    def _build_field_defaults(self) -> dict[str, Any]:
        """Collect per-field defaults from ``review:`` widget specs.

        Honour explicit ``default:`` / ``value:`` / ``args.default`` (Jupyter
        parity), including widgets nested in ``Section``. Checkbox and Flag
        widgets default to ``False`` when unset so incomplete work is an
        explicit boolean rather than missing/NaN.
        """
        defaults: dict[str, Any] = {}
        for spec in self._iter_review_widget_specs():
            if not isinstance(spec, dict):
                continue
            field = spec.get("field")
            if not field:
                continue
            field = str(field)
            if "default" in spec:
                detail = spec["default"]
                if isinstance(detail, dict):
                    if "value" in detail:
                        defaults[field] = detail["value"]
                else:
                    defaults[field] = detail
                continue
            args = spec.get("args") if isinstance(spec.get("args"), dict) else {}
            if "default" in args:
                defaults[field] = args["default"]
                continue
            if "value" in spec:
                defaults[field] = spec["value"]
                continue
            if spec.get("type") in {"Checkbox", "Flag"}:
                defaults[field] = False
        return defaults

    def _cell_is_missing(self, val: Any) -> bool:
        import math
        import numpy as np

        try:
            if val is None:
                return True
            if isinstance(val, float) and math.isnan(val):
                return True
            if isinstance(val, (np.floating,)) and np.isnan(val):
                return True
            if isinstance(val, np.datetime64) and np.isnat(val):
                return True
            if pd.api.types.is_scalar(val) and pd.isnull(val):
                return True
        except (TypeError, ValueError):
            return False
        return False

    def _apply_field_defaults(self) -> None:
        """Write widget defaults into empty output cells on the current row.

        Compute ``row_args`` reads the DataFrame, not ``get_value()``, so
        display-only defaults would leave Propose/Name seeing ``None``.
        """
        defaults = getattr(self, "_field_defaults", None) or {}
        ismutable = getattr(self._data, "ismutable", None)
        for column, value in defaults.items():
            try:
                if column not in self._data.columns:
                    continue
                if callable(ismutable) and ismutable(column) is False:
                    continue
                self._data.set_column(column)
                if not self._cell_is_missing(self._data.get_value()):
                    continue
                self.set_value(column, value)
            except Exception as exc:
                log.debug("Could not apply default for %r: %s", column, exc)

    def get_value(self, column: str) -> Any:
        """Return the current value of *column* for the active record.

        NaN values (pandas sentinel for missing data) are normalised to
        ``None`` so renderers and callers can use a simple ``is None`` check
        rather than having to handle every numpy/pandas NaN variant.  This
        mirrors what the Jupyter interface achieves via ``remove_nan()``
        before passing values to widgets.

        When the cell is missing, apply a review-widget default when one is
        configured (or Checkbox/Flag → ``False``).

        :param column: Name of the data column.
        :return: The stored value, with NaN replaced by ``None`` (or default).
        """
        import math
        import numpy as np
        import pandas as pd

        try:
            known = column in self._data.columns or column == getattr(
                self._data.index, "name", None
            )
        except Exception:
            known = False
        if not known:
            defaults = getattr(self, "_field_defaults", None) or {}
            if column in defaults:
                return defaults[column]
            return None
        self._data.set_column(column)
        val = self._data.get_value()
        # Normalise all NaN-like sentinels to None.
        missing = False
        try:
            if val is None:
                missing = True
            elif isinstance(val, float) and math.isnan(val):
                missing = True
            elif isinstance(val, (np.floating,)) and np.isnan(val):
                missing = True
            elif isinstance(val, np.datetime64) and np.isnat(val):
                missing = True
            elif pd.api.types.is_scalar(val) and pd.isnull(val):
                missing = True
        except (TypeError, ValueError):
            pass
        if missing:
            defaults = getattr(self, "_field_defaults", None) or {}
            if column in defaults:
                return defaults[column]
            return None
        return val

    def get_row_data(self) -> dict:
        """Return all column values for the current record as a plain dict.

        Unlike :meth:`get_value`, which requires knowing the column name in
        advance, this returns the entire row so that callers (e.g. the
        renderer) can look up any column—including those used in
        ``visible_if`` conditions that have no corresponding widget.

        Values are read with :meth:`get_value` rather than ``to_pandas()``.
        ``to_pandas()`` joins every flow into one frame and raises when
        allocation and scores share column names, which would blank Liquid
        substitutions (``{{q1Question}}`` and similar constants).
        ``get_value`` is the same path Jupyter Liquid uses, including
        parameter columns from ``global_consts``.

        Mapping aliases from ``_name_column_map`` and from the interface
        ``input`` / ``output`` mapping (for example ``Title`` → ``Project title``,
        or ``number`` → the index column) are copied into the dict as well.
        Jupyter Liquid uses :meth:`lynguine.assess.data.CustomDataFrame.mapping`;
        the web renderer looks up ``{{Title}}`` by key, so aliases must be
        present or those substitutions go empty.  Index fields are often
        absent from ``_name_column_map`` even when they appear in YAML.
        """
        try:
            columns = list(self._data.columns)
        except Exception:
            return {}

        result: dict = {}
        for col in columns:
            try:
                result[col] = self.get_value(col)
            except Exception:
                result[col] = None

        try:
            idx_name = getattr(self._data.index, "name", None)
            if idx_name and idx_name not in result:
                result[idx_name] = self.get_index()
        except Exception:
            idx_name = None

        for name, column in self._row_mapping_aliases().items():
            if name in result:
                continue
            if column in result:
                result[name] = result[column]
                continue
            try:
                result[name] = self.get_value(column)
            except Exception:
                if column == idx_name:
                    result[name] = self.get_index()
                else:
                    result[name] = None
        return result

    def _row_mapping_aliases(self) -> dict:
        """Name → column aliases for Liquid keys on the current row."""
        aliases: dict = {}
        name_map = getattr(self._data, "_name_column_map", None)
        if isinstance(name_map, dict):
            aliases.update(name_map)
        for key in ("input", "output", "allocation", "scores"):
            try:
                block = self._interface[key] if key in self._interface else None
            except Exception:
                block = None
            if isinstance(block, dict):
                mapping = block.get("mapping")
                if isinstance(mapping, dict):
                    aliases.update(mapping)
        return aliases

    def set_value(self, column: str, value: Any) -> None:
        """Update *column* for the active record and run on-change logic.

        If the new value is identical to the stored value the call is a no-op.

        :param column: Name of the data column.
        :param value: New value to store.
        """
        self._data.set_column(column)
        old_value = self._data.get_value()
        if value != old_value:
            self._data.set_value(value)
            self._value_updated(column)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_flows(self) -> None:
        """Persist current data to the configured output files.

        File paths in the interface may be relative; chdir to the review
        directory so they resolve to the same location used by ``from_flow``.
        """
        import os

        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            self._data.save_flows()
        finally:
            os.chdir(_orig)

    def load_flows(self, reload: bool = False) -> None:
        """Reload data from the configured source files.

        Re-creates ``self._data`` from the interface configuration, preserving
        the current index when *reload* is True.

        :param reload: If True, attempt to restore the active index after
            reloading.  Defaults to False.
        :type reload: bool
        """
        import os
        from referia.assess.data import CustomDataFrame

        current_index = self._data.get_index() if reload else None
        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            self._data = CustomDataFrame.from_flow(self._interface)
        finally:
            os.chdir(_orig)

        self._register_review_computes()
        self._ensure_compute_target_columns()
        self._field_defaults = self._build_field_defaults()

        indices = list(self._data.index)
        if current_index is not None and current_index in indices:
            self.set_index(current_index)
        elif indices:
            self.set_index(indices[0])
        self._apply_field_defaults()
        # Same as __init__: from_flow may already hold this index so set_index
        # skips compute_pre — force review precomputes after reload.
        self._run_review_precompute()
        self._run_interface_compute()

    # ------------------------------------------------------------------
    # Widget spec extraction
    # ------------------------------------------------------------------

    def get_widget_specs(self) -> list[dict]:
        """Return a flat ordered list of widget spec dicts.

        Walks the ``review`` and ``viewer`` sections of the interface config
        and expands cluster entries recursively (including ``Section``
        children).  Each item in the returned list has at least a ``"type"``
        key and, for field-bearing widgets, a ``"field"`` key.

        :return: Ordered list of widget spec dicts (viewer first, then review).
        """
        specs: list[dict] = []
        self._flatten_entries(self._viewer_raw(), specs, preserve_sections=False)
        self._flatten_entries(self._review_raw(), specs, preserve_sections=False)
        return specs

    def get_viewer_specs(self) -> list[dict]:
        """Return widget specs from the ``viewer`` section only.

        :return: Flat ordered list of viewer widget spec dicts.
        """
        specs: list[dict] = []
        self._flatten_entries(self._viewer_raw(), specs, preserve_sections=False)
        return specs

    def get_review_specs(self) -> list[dict]:
        """Return review specs for form rendering.

        ``type: Section`` clusters are kept as nested nodes
        (``title`` + ``entries``) so the web renderer can wrap each group in
        a collapsible ``<details>``.  Other cluster types are still flattened.

        :return: Ordered list of leaf widgets and Section clusters.
        """
        specs: list[dict] = []
        self._flatten_entries(self._review_raw(), specs, preserve_sections=True)
        return specs

    def list_url_entries(self) -> list[dict]:
        """Resolve ``urls:`` entries for the current record.

        Jupyter opens these with ``webbrowser.open``.  The web panel renders
        them as ``<a target="_blank">`` links.

        :return: List of ``{"href": str, "label": str}`` dicts.
        """
        from unidecode import unidecode

        from referia.util.misc import renderable, tallyable

        entries: list[dict] = []
        for view in self._interface_section("urls"):
            if not isinstance(view, dict) or "url" not in view:
                continue
            try:
                urlterm = self._extract_url_term(view, renderable, tallyable)
                href = unidecode(str(view["url"]) + urlterm.replace(" ", "%20"))
            except Exception as exc:
                log.debug("Could not resolve url entry %r: %s", view, exc)
                continue
            if not href:
                continue
            entries.append({"href": href, "label": href})
        return entries

    def list_pdf_entries(self) -> list[dict]:
        """Describe ``localpdf`` / ``editpdf`` files for the current record.

        Paths are resolved on the server; the returned dicts are metadata for
        the document panel.  Serving goes through ``/record-document/{kind}/{n}``.

        :return: List of ``kind``, ``n``, ``label``, ``exists`` dicts.
        """
        entries: list[dict] = []
        for kind in ("localpdf", "editpdf"):
            for n, view in enumerate(self._interface_section(kind)):
                if not isinstance(view, dict):
                    continue
                path = self.get_record_document(kind, n)
                label = view.get("name") or (path.name if path is not None else kind)
                entries.append(
                    {
                        "kind": kind,
                        "n": n,
                        "label": str(label),
                        "exists": bool(path is not None and path.is_file()),
                    }
                )
        return entries

    def get_record_document(self, kind: str, n: int):
        """Return the resolved PDF path for ``localpdf``/``editpdf`` entry *n*.

        :return: A :class:`~pathlib.Path` or ``None`` if missing or unresolvable.
        """
        from pathlib import Path

        views = self._interface_section(kind)
        if n < 0 or n >= len(views):
            return None
        view = views[n]
        if not isinstance(view, dict):
            return None
        try:
            if kind == "localpdf":
                path = self._resolve_local_file(view)
            elif kind == "editpdf":
                path = self._resolve_editpdf_file(view)
            else:
                return None
        except Exception as exc:
            log.debug("Could not resolve %s[%s]: %s", kind, n, exc)
            return None
        return Path(path).expanduser() if path else None

    def allowed_roots_for_document(self, kind: str, n: int) -> list:
        """Directories that entry *n* of *kind* may legally serve from."""
        from pathlib import Path

        roots = [Path(self._directory).resolve()]
        views = self._interface_section(kind)
        if n < 0 or n >= len(views) or not isinstance(views[n], dict):
            return roots
        view = views[n]
        for key in ("directory", "sourcedirectory", "storedirectory"):
            raw = view.get(key)
            if not raw:
                continue
            try:
                roots.append(self._resolve_config_relative_dir(raw))
            except OSError:
                continue
        return roots

    def has_plotly_viewer(self) -> bool:
        """True when any ``viewer:`` entry is a ``PlotlyFigure`` (CIP-0011)."""
        from referia.assess.viewer_bindings import viewer_entry_type

        return any(
            viewer_entry_type(spec) == "PlotlyFigure"
            for spec in self.get_viewer_specs()
        )

    def render_viewer_html(
        self, viewer_spec: dict, *, viewer_index: int = 0
    ) -> str:
        """Evaluate *viewer_spec* against the current record and return HTML.

        Liquid / Markdown entries use ``view_to_value()`` then ``render_viewer()``.
        Interactive types (``PlotlyFigure``, ``StaticImage``) skip Liquid and
        load structured field data (CIP-0011).

        Under ``display.layout: inline_list``, injects Liquid local ``rows``
        (filtered+sorted tall working set) so templates can
        ``{% for row in rows %}``.

        :param viewer_spec: A viewer spec dict (``liquid``, ``display``, etc.).
        :param viewer_index: Position among viewer entries (stable DOM id).
        :return: Rendered HTML string (empty string on evaluation failure).
        """
        from referia.assess.viewer_bindings import is_interactive_viewer_type
        from referia.web.render import render_viewer as _render_viewer_html

        if is_interactive_viewer_type(viewer_spec):
            return self._render_interactive_viewer_html(
                viewer_spec, viewer_index=viewer_index
            )

        local: dict[str, Any] = {}
        try:
            if self.get_display_layout() == "inline_list":
                local["rows"] = self.get_rows()
        except ValueError:
            raise
        except Exception as exc:
            log.debug("Could not build rows for viewer: %s", exc)
            local["rows"] = []

        try:
            content = self._data.view_to_value(viewer_spec, local=local) or ""
        except Exception as exc:
            log.debug("Could not evaluate viewer spec %r: %s", viewer_spec, exc)
            content = ""
        return _render_viewer_html(
            viewer_spec, content, viewer_index=viewer_index
        )

    def _render_interactive_viewer_html(
        self, viewer_spec: dict, *, viewer_index: int = 0
    ) -> str:
        """Render PlotlyFigure / StaticImage / viewer-chrome widgets."""
        from referia.assess.viewer_bindings import (
            highlight_binding,
            is_viewer_chrome_type,
            parse_figure_spec,
            resolve_figure_payload,
            viewer_entry_type,
        )
        from referia.web.render import render_viewer as _render_viewer_html
        from referia.web.render import render_widget as _render_widget_html

        vtype = viewer_entry_type(viewer_spec)
        field = viewer_spec.get("field")
        highlight_value = None
        hl = highlight_binding(viewer_spec)
        if hl:
            try:
                highlight_value = self.get_value(hl["from_field"])
            except Exception:
                highlight_value = None

        if is_viewer_chrome_type(viewer_spec):
            data: dict = {}
            try:
                data = dict(self.get_row_data() or {})
            except Exception:
                data = {}
            for col in list(data.keys()):
                try:
                    data[col] = self.get_value(col)
                except Exception:
                    pass
            if field and field not in data:
                try:
                    data[str(field)] = self.get_value(str(field))
                except Exception:
                    data[str(field)] = None
            chrome_args = viewer_spec.get("args") or {}
            for dep in (
                chrome_args.get("options_field"),
                chrome_args.get("options_labels_field"),
            ):
                if dep and dep not in data:
                    try:
                        data[str(dep)] = self.get_value(str(dep))
                    except Exception:
                        data[str(dep)] = None
            val = data.get(field) if field else None
            inner = _render_widget_html(viewer_spec, val, data)
            return (
                f'<div class="viewer viewer-chrome" '
                f'id="viewer-chrome-{viewer_index}">{inner}</div>'
            )

        if vtype == "PlotlyFigure":
            raw = resolve_figure_payload(self.get_value, viewer_spec)
            figure = parse_figure_spec(raw)
            return _render_viewer_html(
                viewer_spec,
                "",
                figure=figure,
                highlight_value=highlight_value,
                viewer_index=viewer_index,
            )

        # StaticImage: field value or liquid-evaluated URL/path
        content = ""
        if field:
            try:
                val = self.get_value(str(field))
                content = "" if val is None else str(val)
            except Exception as exc:
                log.debug("StaticImage field %r: %s", field, exc)
        elif any(k in viewer_spec for k in ("liquid", "display", "join", "tally")):
            try:
                content = self._data.view_to_value(viewer_spec) or ""
            except Exception as exc:
                log.debug("StaticImage liquid: %s", exc)
        return _render_viewer_html(
            viewer_spec, content, viewer_index=viewer_index
        )

    def _viewer_raw(self) -> list:
        viewer = self._interface.get("viewer", []) or []
        return viewer if isinstance(viewer, list) else [viewer]

    def _review_raw(self) -> list:
        review = self._interface.get("review", []) or []
        return review if isinstance(review, list) else [review]

    def _register_review_computes(self) -> None:
        """Copy ``type: precompute`` / ``postcompute`` specs onto the data object.

        Mirrors Jupyter :func:`~referia.assess.review.extract_review` so
        soft-fill and PDF extract run when the active index changes.
        """
        self._data._precompute = []
        self._data._postcompute = []
        self._collect_review_computes(self._review_raw())

    def _collect_review_computes(self, entries: list) -> None:
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            entry_type = entry.get("type")
            if entry_type == "precompute":
                specs = entry.get("specifications", [])
                if isinstance(specs, list):
                    self._data._precompute.extend(specs)
                elif specs:
                    self._data._precompute.append(specs)
            elif entry_type == "postcompute":
                specs = entry.get("specifications", [])
                if isinstance(specs, list):
                    self._data._postcompute.extend(specs)
                elif specs:
                    self._data._postcompute.append(specs)
            elif entry_type in _CLUSTER_TYPES:
                sub = entry.get(
                    "entries",
                    entry.get("children", entry.get("specifications", [])),
                )
                if isinstance(sub, list):
                    self._collect_review_computes(sub)

    def _compute_field_names(self, specs: list) -> list[str]:
        names: list[str] = []
        for spec in specs or []:
            if not isinstance(spec, dict):
                continue
            fields = spec.get("field")
            if fields is None:
                continue
            if isinstance(fields, list):
                names.extend(str(f) for f in fields if f and f != "_")
            elif fields and fields != "_":
                names.append(str(fields))
        return names

    def _ensure_compute_target_columns(self) -> None:
        """Create missing cache columns for precompute / top-level compute fields.

        ``set_value_column`` refuses unknown columns; soft-fill into a new
        object field (e.g. ``applicant`` from ``extract_form_fields``) needs
        the column to exist first.
        """
        specs: list = list(getattr(self._data, "_precompute", []) or [])
        specs.extend(getattr(self._data, "_postcompute", []) or [])
        if "compute" in self._interface:
            top = self._interface["compute"]
            if isinstance(top, list):
                specs.extend(top)
            elif isinstance(top, dict):
                specs.append(top)

        for col in self._compute_field_names(specs):
            if col in self._data.columns:
                continue
            # Prefer __setitem__ (cache path). referia.add_column requires
            # series/scores and fails when only input/output are present.
            self._data[col] = None

    def _run_review_precompute(self) -> None:
        """Run ``review: type: precompute`` with cwd on the review directory.

        ``CustomDataFrame.set_index`` only calls ``compute_pre`` when the
        active index changes. After ``from_flow`` the first row is often
        already selected, so boot / reload would otherwise skip seed naming
        and soft-fill. Idempotent precomputes (e.g. ensure_seed_names) make
        a second run cheap when ``set_index`` already ran them.
        """
        import os

        if not getattr(self._data, "_precompute", None):
            return
        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            self._data.compute_pre()
        finally:
            os.chdir(_orig)

    def _run_interface_compute(self) -> None:
        """Run top-level ``compute:`` for the current index (cwd = review dir)."""
        import os

        if "compute" not in self._interface:
            return
        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            self._data._compute.run(
                self._data, {"compute": self._interface["compute"]}
            )
        finally:
            os.chdir(_orig)

    def _interface_section(self, key: str) -> list:
        try:
            section = self._interface[key] if key in self._interface else []
        except Exception:
            section = []
        if not section:
            return []
        return section if isinstance(section, list) else [section]

    def _extract_file_value(self, view: dict):
        from referia.util.misc import renderable, tallyable

        if renderable(view):
            return self._data.view_to_value(view)
        if tallyable(view):
            return self._data.tally_to_value(view)
        if "field" in view:
            return self.get_value(view["field"])
        if "file" in view:
            return view["file"]
        return None

    def _extract_url_term(self, view: dict, renderable, tallyable) -> str:
        if "field" in view:
            val = self.get_value(view["field"])
            if isinstance(val, str):
                return val
        if renderable(view):
            return str(self._data.view_to_value(view) or "")
        if tallyable(view):
            return str(self._data.tally_to_value(view) or "")
        return ""

    def _resolve_config_relative_dir(self, raw: str | None):
        """Resolve a YAML directory against the config directory, not process cwd.

        Relative values such as ``../files`` are joined to ``self._directory``.
        Absolute paths and ``$HOME`` / env-expanded paths are left as absolute.
        An empty value means the config directory itself.
        """
        import os
        from pathlib import Path

        base = Path(self._directory)
        text = os.path.expandvars(str(raw or "")).strip()
        if not text:
            return base.resolve()
        directory = Path(text).expanduser()
        if not directory.is_absolute():
            directory = base / directory
        return directory.resolve()

    def _resolve_local_file(self, view: dict):
        from pathlib import Path

        val = self._extract_file_value(view)
        if not isinstance(val, str) or not val:
            return None
        return self._resolve_config_relative_dir(view.get("directory")) / Path(val)

    def _resolve_editpdf_file(self, view: dict):
        """Prefer the annotated copy when it exists, otherwise the source PDF."""
        from pathlib import Path

        from referia.util.files import to_valid_file
        from referia.util.misc import renderable

        val = self._extract_file_value(view)
        if not isinstance(val, str) or not val:
            return None
        source_dir = self._resolve_config_relative_dir(view.get("sourcedirectory"))
        store_raw = view.get("storedirectory")
        store_dir = (
            self._resolve_config_relative_dir(store_raw) if store_raw else None
        )
        orig = source_dir / Path(val)
        if "name" in view:
            stub = str(view["name"]) + ".pdf"
        elif renderable(view):
            stub = self._data.view_to_tmpname(view) + ".pdf"
        else:
            stub = orig.name
        index = self.get_index()
        dest_name = to_valid_file(str(index)) + "_" + to_valid_file(stub)
        dest = (store_dir / dest_name) if store_dir is not None else None
        if dest is not None and dest.is_file():
            return dest
        return orig

    def _flatten_entries(
        self, entries: list, out: list, *, preserve_sections: bool = False
    ) -> None:
        """Recursively expand nested review/viewer cluster entries.

        :param entries: List of widget or cluster dicts.
        :param out: Accumulator list that receives leaf widgets (and, when
            *preserve_sections* is True, nested ``Section`` nodes).
        :param preserve_sections: Keep ``type: Section`` as a tree node with
            expanded ``entries`` instead of flattening its children.
        """
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            entry_type = entry.get("type", "")
            if (
                preserve_sections
                and entry_type in _PRESERVE_CLUSTER_TYPES
            ):
                sub = entry.get("entries", entry.get("children", []))
                children: list = []
                if isinstance(sub, list):
                    self._flatten_entries(
                        sub, children, preserve_sections=preserve_sections
                    )
                node = dict(entry)
                node["entries"] = children
                node.pop("children", None)
                out.append(node)
                continue
            # Soft-fill / compute clusters are registered separately
            # (_register_review_computes). Expanding them here would inject
            # compute dicts (field + function, no widget type) into the form
            # and steal OOB refreshes from real widgets of the same field
            # (e.g. Email Comment Textarea with visible_if).
            if entry_type in {"precompute", "postcompute"}:
                continue
            if entry_type in _CLUSTER_TYPES:
                sub = entry.get(
                    "entries",
                    entry.get("children", entry.get("specifications", [])),
                )
                if isinstance(sub, list):
                    self._flatten_entries(
                        sub, out, preserve_sections=preserve_sections
                    )
            else:
                out.append(entry)

    # ------------------------------------------------------------------
    # Widget dependency tracking
    # ------------------------------------------------------------------

    def affected_widgets(self, column: str) -> set[str]:
        """Return column names that may need refreshing after *column* changes.

        Returns only widgets that actually depend on *column*:

        * fields whose ``visible_if`` references *column*
        * combinator output fields that are shown as widgets (recomputed in
          :meth:`_value_updated`)

        Independent textareas/sliders are **not** returned.  Rebuilding the
        whole form on every blur destroyed the control the user had just
        focused (CoE 2026-10-18).  A fuller dependency graph (Liquid viewers,
        cross-field computes) can extend this later without reverting to
        “refresh everything”.

        :param column: The column that was just updated.
        :return: Set of column names to refresh (may be empty).
        """
        out: set[str] = set()
        widget_fields = {
            spec["field"]
            for spec in self.get_widget_specs()
            if "field" in spec
        }
        for spec in self.get_widget_specs():
            field = spec.get("field")
            if not field or field == column:
                continue
            if _visible_if_depends_on(spec.get("visible_if"), column):
                out.add(field)
        for view in self._interface.get("combinator") or []:
            if not isinstance(view, dict):
                continue
            cfield = view.get("field")
            if cfield and cfield in widget_fields and cfield != column:
                out.add(cfield)
        return out

    # ------------------------------------------------------------------
    # Internal on-change logic (mirrors Reviewer.value_updated without widgets)
    # ------------------------------------------------------------------

    def run_populate(self, compute_interface: dict) -> None:
        """Run an on-demand compute as triggered by a PopulateButton.

        Mirrors the Jupyter PopulateButton.on_click behaviour::

            self._parent._data._compute.run(
                self._parent._data, {"compute": args["compute"]}
            )

        File paths in compute functions may be relative; chdir to the review
        directory so they resolve correctly.

        :param compute_interface: Dict of the form ``{"compute": <spec>}`` as
            constructed from the PopulateButton's ``args.compute`` entry.
        """
        import os

        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            self._data._compute.run(self._data, compute_interface)
        finally:
            os.chdir(_orig)

    # ------------------------------------------------------------------
    # Document generation (CIP-000B remaining work)
    # ------------------------------------------------------------------

    @property
    def _system(self):
        """Lazily construct a :class:`~referia.system.Sys` for document I/O."""
        if not hasattr(self, "_system_instance") or self._system_instance is None:
            from referia.system import Sys

            self._system_instance = Sys(self._interface)
        return self._system_instance

    def list_document_entries(self, section: str = "documents") -> list[dict]:
        """Describe ``documents:`` / ``summary_documents:`` action buttons.

        :param section: Interface key, ``\"documents\"`` or
            ``\"summary_documents\"``.
        :return: List of ``n``, ``type``, ``label``, ``summary``, ``section``.
        """
        from referia.util.misc import document_action_label

        summary = section == "summary_documents"
        entries: list[dict] = []
        for n, doc in enumerate(self._interface_section(section)):
            if not _is_document_action(doc):
                continue
            dtype = str(doc["type"])
            entry = {
                "n": n,
                "type": dtype,
                "label": document_action_label(doc, summary=summary),
                "summary": summary,
                "section": section,
            }
            if "visible_if" in doc:
                entry["visible_if"] = doc["visible_if"]
            entries.append(entry)
        return entries

    def template_to_value(self, template: dict) -> str:
        """Render a document template field against the current record.

        Mirrors :meth:`referia.assess.review.Reviewer.template_to_value` without
        widgets.  ``use: review`` / ``use: scorer`` synthesise markdown from
        current review field values instead of ``WidgetCluster.to_markdown()``.
        """
        if not isinstance(template, dict):
            return str(template or "")
        if "use" in template:
            use = template["use"]
            if use == "viewer":
                viewer = self._interface.get("viewer", []) or []
                if not isinstance(viewer, list):
                    viewer = [viewer]
                parts = []
                for view in viewer:
                    try:
                        parts.append(str(self._data.view_to_value(view) or ""))
                    except Exception as exc:
                        log.debug("viewer template failed: %s", exc)
                return "\n\n".join(parts)
            if use in {"scorer", "review"}:
                return self._review_fields_markdown()
        return str(self._data.view_to_value(template) or "")

    def _review_fields_markdown(self) -> str:
        """Best-effort markdown of review fields when widgets are unavailable."""
        lines: list[str] = []
        for spec in self.get_review_specs():
            field = spec.get("field")
            if not field:
                continue
            label = (
                spec.get("args", {}).get("description")
                or spec.get("description")
                or field
            )
            val = self.get_value(field)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                val = ""
            lines.append(f"### {label}\n\n{val}\n")
        return "\n".join(lines)

    def generate_document(self, n: int, *, summary: bool = False) -> dict:
        """Generate ``documents[n]`` (or ``summary_documents[n]``) and return status.

        :return: Dict with ``type``, ``path`` (filesystem path or ``None``),
            ``href`` (``/document/...`` download when under the review dir),
            and ``status`` (``created`` / ``drafted``).
        """
        section = "summary_documents" if summary else "documents"
        docs = self._interface_section(section)
        if n < 0 or n >= len(docs) or not isinstance(docs[n], dict):
            raise IndexError(f"No document at {section}[{n}]")
        return self.create_document(docs[n], summary=summary)

    def create_document(self, document: dict, summary: bool = False) -> dict:
        """Generate one document spec without opening it in a desktop app.

        Ports :meth:`referia.assess.review.Reviewer.create_document` for the web
        backend: writes files via ``lynguine.access.io`` and returns a download
        path instead of calling :meth:`~referia.system.Sys.open_localfile`.
        """
        import os
        from pathlib import Path

        from lynguine import access

        if not isinstance(document, dict) or "type" not in document:
            raise ValueError("document must be a dict with a type key")

        args = self._document_template_args(document, summary=summary)
        doctype = document["type"]
        result: dict[str, Any] = {
            "type": doctype,
            "path": None,
            "href": None,
            "status": "created",
        }

        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            if doctype == "email":
                self._system.create_email(document, **args)
                result["status"] = "drafted"
                return result

            data, filename, content = self._system.create_document_content(
                document, **args
            )
            writers = {
                "docx": access.io.write_docx_file,
                "markdown": access.io.write_markdown_file,
                "letter": access.io.write_letter_file,
                "formlink": access.io.write_formlink,
            }
            writer = writers.get(doctype)
            if writer is None:
                # Unknown / excel etc.: use Sys but suppress desktop open.
                _open = self._system.open_localfile
                self._system.open_localfile = lambda *_a, **_k: None  # type: ignore[method-assign]
                try:
                    self._system.create_document(document, **args)
                finally:
                    self._system.open_localfile = _open  # type: ignore[method-assign]
                filename = args.get("filename") or filename
            else:
                writer(data=data, filename=filename, content=content)

            if filename:
                path = Path(filename).expanduser()
                if not path.is_absolute():
                    path = Path(self._directory) / path
                result["path"] = str(path.resolve())
                result["href"] = self.document_download_href(path)
            return result
        finally:
            os.chdir(_orig)

    def _document_template_args(self, document: dict, *, summary: bool) -> dict:
        """Resolve Liquid / view template fields on a document spec."""
        args: dict[str, Any] = {}
        template_keys = ("tally", "display", "list", "join", "liquid", "use")
        for field, value in document.items():
            if field == "type":
                continue
            args[field] = value
            if value is None or not isinstance(value, dict):
                continue
            if not any(k in value for k in template_keys):
                continue
            if summary and field in {"content", "body"}:
                current = self.get_index()
                parts: list[str] = []
                # Honour session filters/sort (inline_list working set).
                try:
                    indices = self.working_indices()
                except Exception:
                    indices = self.index_list()
                for idx in indices:
                    self.set_index(idx)
                    parts.append(self.template_to_value(value))
                    parts.append("\n\n")
                args[field] = "".join(parts)
                if current is not None:
                    self.set_index(current)
            else:
                args[field] = self.template_to_value(value)

        if "body" in args:
            if "content" in args:
                log.warning("Contents field being overwritten by body in create_document")
            args["content"] = args["body"]
        if "header" in args:
            args["content"] = args["header"] + "\n\n" + args.get("content", "")
            del args["header"]
        if "footer" in args:
            args["content"] = args.get("content", "") + "\n\n" + args["footer"]
            del args["footer"]
        return args

    def document_download_href(self, path) -> str | None:
        """Return a ``/document/...`` href if *path* is under the review directory."""
        from pathlib import Path

        try:
            resolved = Path(path).expanduser().resolve()
            rel = resolved.relative_to(Path(self._directory).resolve())
        except (OSError, ValueError, TypeError):
            return None
        return f"/document/{rel.as_posix()}"

    def ensure_edit_pdf(self, n: int):
        """Copy/extract ``editpdf[n]`` into ``storedirectory`` and return its Path.

        Mirrors the non-open part of :meth:`referia.system.Sys.edit_files` so
        the web UI can offer a download instead of launching Preview.
        """
        import os
        from pathlib import Path

        from referia.util.files import to_valid_file
        from referia.util.misc import renderable

        views = self._interface_section("editpdf")
        if n < 0 or n >= len(views) or not isinstance(views[n], dict):
            raise IndexError(f"No editpdf entry at index {n}")
        view = views[n]
        val = self._extract_file_value(view)
        if not isinstance(val, str) or not val:
            raise FileNotFoundError(f"No file value for editpdf[{n}]")
        if "storedirectory" not in view or "sourcedirectory" not in view:
            raise ValueError("editpdf entry requires sourcedirectory and storedirectory")

        source_dir = self._resolve_config_relative_dir(view.get("sourcedirectory"))
        store_dir = self._resolve_config_relative_dir(view.get("storedirectory"))
        orig = source_dir / Path(val)
        if "name" in view:
            stub = str(view["name"]) + ".pdf"
        elif renderable(view):
            stub = self._data.view_to_tmpname(view) + ".pdf"
        else:
            stub = orig.name
        index = self.get_index()
        dest_name = to_valid_file(str(index)) + "_" + to_valid_file(stub)
        dest = store_dir / dest_name

        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            store_dir.mkdir(parents=True, exist_ok=True)
            if not dest.is_file():
                self._system.copy_file(str(orig), str(dest), view, self._data)
        finally:
            os.chdir(_orig)

        if not dest.is_file():
            raise FileNotFoundError(f"Could not create edit PDF at {dest}")
        return dest.resolve()

    def _value_updated(self, column: str) -> None:
        """Run on-change side-effects for *column* without touching widgets.

        Replicates the non-widget parts of ``Reviewer.value_updated()``:

        1. Updates the ``<column>_modified`` timestamp.
        2. Sets the ``<column>_created`` timestamp when absent.
        3. Re-evaluates any combinator fields defined in the interface.
        """
        today_val = pd.to_datetime("today")

        # Modified timestamp
        modified_suffix: str = self._interface["modified_suffix"]
        modified_field = f"{column}_{modified_suffix}"
        try:
            self._data.set_dtype(modified_field, "datetime64[ns]")
            self._data.set_column(modified_field)
            self._data.set_value(today_val)
        except Exception as exc:
            log.debug("Could not set modified field %r: %s", modified_field, exc)

        # Created timestamp (only when absent)
        created_suffix: str = self._interface["created_suffix"]
        created_field = f"{column}_{created_suffix}"
        try:
            self._data.set_dtype(created_field, "datetime64[ns]")
            created_col_val = self._data.get_value_column(created_field)
            current_created = self._data.at[self._data.get_index(), created_col_val] if created_col_val in self._data.columns else None
            if current_created is None or pd.isna(current_created):
                self._data.set_column(created_field)
                self._data.set_value(today_val)
        except Exception as exc:
            log.debug("Could not set created field %r: %s", created_field, exc)

        # Combinators
        if "combinator" in self._interface:
            for view in self._interface["combinator"]:
                if "field" not in view:
                    continue
                col = view["field"]
                combinator_view = {k: v for k, v in view.items() if k != "field"}
                try:
                    combinator_val = self._data.viewer_to_value(combinator_view)
                    self._data.set_column(col)
                    self._data.set_value(combinator_val)
                except Exception as exc:
                    log.debug("Could not update combinator %r: %s", col, exc)
