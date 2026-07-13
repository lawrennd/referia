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
    Column names whose displayed values may change after *column* is updated.
    The current implementation returns all field-bearing widget columns so the
    web layer simply re-renders the whole form; a dependency-tracking
    optimisation is deferred to a follow-on CIP.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from lynguine import log as _lynguine_log

log = logging.getLogger(__name__)

# Widget types that contain nested entries rather than being rendered directly.
_CLUSTER_TYPES = frozenset(
    {"group", "load", "composite", "loop", "precompute", "postcompute"}
)

# Widget types that don't carry a data field (no column to refresh).
_NON_FIELD_TYPES = frozenset(
    {"Label", "HTML", "HTMLMath", "Markdown",
     "SaveButton", "ReloadButton", "PopulateButton"}
)


class WebReviewer:
    """Stateful, widget-free review session for the web backend.

    :param user_file: Name of the YAML configuration file,
        defaults to ``"_referia.yml"``.
    :type user_file: str
    :param directory: Directory that contains the configuration file,
        defaults to ``"."``.
    :type directory: str

    Example::

        reviewer = WebReviewer("_referia.yml", "/path/to/review")
        reviewer.set_index(reviewer.index_list()[0])
        value = reviewer.get_value("score")
        reviewer.set_value("score", 5)
        reviewer.save_flows()
    """

    def __init__(self, user_file: str = "_referia.yml", directory: str = ".") -> None:
        from referia.config.interface import Interface
        from referia.assess.data import CustomDataFrame

        self._interface = Interface.from_file(user_file, directory)
        self._data = CustomDataFrame.from_flow(self._interface)

        indices = list(self._data.index)
        if indices:
            self._data.set_index(indices[0])

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def index_list(self) -> list:
        """Return all valid record indices as a plain list."""
        return list(self._data.index)

    def get_index(self) -> Any:
        """Return the currently active record index."""
        return self._data.get_index()

    def set_index(self, index: Any) -> None:
        """Switch the active record to *index*."""
        self._data.set_index(index)

    # ------------------------------------------------------------------
    # Value access
    # ------------------------------------------------------------------

    def get_value(self, column: str) -> Any:
        """Return the current value of *column* for the active record.

        :param column: Name of the data column.
        :return: The stored value (may be ``None`` / ``NaN``).
        """
        self._data.set_column(column)
        return self._data.get_value()

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
        """Persist current data to the configured output files."""
        self._data.save_flows()

    def load_flows(self, reload: bool = False) -> None:
        """Reload data from the configured source files.

        :param reload: Passed through to ``CustomDataFrame.load_flows()``
            (currently unused by the infrastructure but kept for API
            compatibility with ``Reviewer``).
        """
        self._data.load_flows()

    # ------------------------------------------------------------------
    # Widget spec extraction
    # ------------------------------------------------------------------

    def get_widget_specs(self) -> list[dict]:
        """Return a flat ordered list of widget spec dicts.

        Walks the ``review`` and ``viewer`` sections of the interface config
        and expands cluster entries recursively.  Each item in the returned
        list has at least a ``"type"`` key and, for field-bearing widgets, a
        ``"field"`` key.

        :return: Ordered list of widget spec dicts (viewer first, then review).
        """
        specs: list[dict] = []
        self._flatten_entries(self._viewer_raw(), specs)
        self._flatten_entries(self._review_raw(), specs)
        return specs

    def get_viewer_specs(self) -> list[dict]:
        """Return widget specs from the ``viewer`` section only.

        :return: Flat ordered list of viewer widget spec dicts.
        """
        specs: list[dict] = []
        self._flatten_entries(self._viewer_raw(), specs)
        return specs

    def get_review_specs(self) -> list[dict]:
        """Return widget specs from the ``review`` section only.

        :return: Flat ordered list of review widget spec dicts.
        """
        specs: list[dict] = []
        self._flatten_entries(self._review_raw(), specs)
        return specs

    def render_viewer_html(self, viewer_spec: dict) -> str:
        """Evaluate *viewer_spec* against the current record and return HTML.

        Uses ``CustomDataFrame.view_to_value()`` to resolve Liquid / display
        templates, then ``render_viewer()`` to produce the HTML string.

        :param viewer_spec: A viewer spec dict (``liquid``, ``display``, etc.).
        :return: Rendered HTML string (empty string on evaluation failure).
        """
        from referia.web.render import render_viewer as _render_viewer_html

        try:
            content = self._data.view_to_value(viewer_spec) or ""
        except Exception as exc:
            log.debug("Could not evaluate viewer spec %r: %s", viewer_spec, exc)
            content = ""
        return _render_viewer_html(viewer_spec, content)

    def _viewer_raw(self) -> list:
        viewer = self._interface.get("viewer", []) or []
        return viewer if isinstance(viewer, list) else [viewer]

    def _review_raw(self) -> list:
        review = self._interface.get("review", []) or []
        return review if isinstance(review, list) else [review]

    def _flatten_entries(self, entries: list, out: list) -> None:
        """Recursively flatten nested review/viewer cluster entries.

        :param entries: List of widget or cluster dicts.
        :param out: Accumulator list that receives leaf widget dicts.
        """
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            entry_type = entry.get("type", "")
            if entry_type in _CLUSTER_TYPES:
                sub = entry.get("entries", entry.get("specifications", []))
                if isinstance(sub, list):
                    self._flatten_entries(sub, out)
            else:
                out.append(entry)

    # ------------------------------------------------------------------
    # Widget dependency tracking
    # ------------------------------------------------------------------

    def affected_widgets(self, column: str) -> set[str]:
        """Return column names that may need refreshing after *column* changes.

        The current implementation conservatively returns **all** field-bearing
        widget columns so the web layer re-renders the complete form.  A
        finer-grained dependency graph is deferred to a follow-on CIP.

        :param column: The column that was just updated.
        :return: Set of column names to refresh.
        """
        return {
            spec["field"]
            for spec in self.get_widget_specs()
            if "field" in spec
        }

    # ------------------------------------------------------------------
    # Internal on-change logic (mirrors Reviewer.value_updated without widgets)
    # ------------------------------------------------------------------

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
