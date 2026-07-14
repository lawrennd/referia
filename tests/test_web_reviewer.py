"""Unit tests for referia.assess.web_review.WebReviewer.

All tests use unittest.mock to avoid requiring a real _referia.yml file or
any I/O.  The Interface and CustomDataFrame dependencies are patched so we can
exercise WebReviewer's logic in isolation.
"""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch, PropertyMock

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers for building mock objects
# ---------------------------------------------------------------------------


def _make_interface(
    review=None,
    viewer=None,
    modified_suffix="modified",
    created_suffix="created",
    combinator=None,
):
    """Return a dict-like mock for Interface."""
    data = {
        "review": review or [],
        "viewer": viewer or [],
        "modified_suffix": modified_suffix,
        "created_suffix": created_suffix,
    }
    if combinator is not None:
        data["combinator"] = combinator

    iface = MagicMock()
    iface.__getitem__ = lambda self, k: data[k]
    iface.__contains__ = lambda self, k: k in data
    iface.get = lambda k, default=None: data.get(k, default)
    return iface


def _make_data(index_vals=None, col_vals=None):
    """Return a mock for CustomDataFrame."""
    if index_vals is None:
        index_vals = ["row0", "row1"]
    if col_vals is None:
        col_vals = {}

    storage: dict = dict(col_vals)
    current_index = [index_vals[0]]
    current_col = [None]

    data = MagicMock()
    type(data).index = PropertyMock(return_value=index_vals)
    data.columns = list(col_vals.keys())

    data.get_index.side_effect = lambda: current_index[0]
    data.set_index.side_effect = lambda v: current_index.__setitem__(0, v)

    data.get_column.side_effect = lambda: current_col[0]
    data.set_column.side_effect = lambda c: current_col.__setitem__(0, c)

    def _get_value():
        return storage.get(current_col[0])

    def _set_value(v):
        storage[current_col[0]] = v

    data.get_value.side_effect = _get_value
    data.set_value.side_effect = _set_value

    def _at_access(idx, col):
        return storage.get(col)

    data.at.__getitem__ = lambda self_inner, key: _at_access(*key)

    data.get_value_column.side_effect = lambda col: col  # identity
    data.save_flows.return_value = None
    data.load_flows.return_value = None
    data.set_dtype.return_value = None
    data.viewer_to_value.return_value = "combined"

    return data, storage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _build_reviewer(review=None, viewer=None, index_vals=None, col_vals=None, combinator=None):
    """Construct a WebReviewer with patched Interface and CustomDataFrame."""
    from referia.assess.web_review import WebReviewer

    iface = _make_interface(
        review=review,
        viewer=viewer,
        combinator=combinator,
    )
    data, storage = _make_data(index_vals=index_vals, col_vals=col_vals)

    reviewer = WebReviewer.__new__(WebReviewer)
    reviewer._interface = iface
    reviewer._data = data
    return reviewer, data, storage


# ---------------------------------------------------------------------------
# Tests: construction (index initialisation)
# ---------------------------------------------------------------------------


class TestWebReviewerConstruction:
    def test_initial_index_set_to_first(self):
        reviewer, data, _ = _build_reviewer(index_vals=["a", "b", "c"])
        # After construction the index should be set to the first item
        # (In the real __init__ this happens; here we verify the mock is wired.)
        assert reviewer.get_index() == "a"

    def test_index_list_returns_all_indices(self):
        reviewer, _, _ = _build_reviewer(index_vals=["x", "y", "z"])
        assert reviewer.index_list() == ["x", "y", "z"]


# ---------------------------------------------------------------------------
# Tests: index navigation
# ---------------------------------------------------------------------------


class TestSetIndex:
    def test_set_index_changes_active_record(self):
        reviewer, data, _ = _build_reviewer(index_vals=["r0", "r1"])
        reviewer.set_index("r1")
        data.set_index.assert_called_with("r1")

    def test_get_index_after_set(self):
        reviewer, data, _ = _build_reviewer(index_vals=["r0", "r1"])
        reviewer.set_index("r1")
        assert reviewer.get_index() == "r1"


# ---------------------------------------------------------------------------
# Tests: value get/set
# ---------------------------------------------------------------------------


class TestGetValue:
    def test_get_value_sets_column_then_reads(self):
        reviewer, data, storage = _build_reviewer(col_vals={"score": 3})
        val = reviewer.get_value("score")
        data.set_column.assert_called_with("score")
        assert val == 3

    def test_get_value_none_for_missing_column(self):
        reviewer, _, _ = _build_reviewer(col_vals={})
        assert reviewer.get_value("nonexistent") is None


class TestSetValue:
    def test_set_value_updates_storage(self):
        reviewer, data, storage = _build_reviewer(col_vals={"score": 0})
        reviewer.set_value("score", 7)
        assert storage["score"] == 7

    def test_set_value_noop_when_unchanged(self):
        reviewer, data, storage = _build_reviewer(col_vals={"score": 5})
        reviewer.set_value("score", 5)
        # set_value on _data should NOT have been called with 5 again
        data.set_value.assert_not_called()

    def test_set_value_triggers_modified_timestamp(self):
        reviewer, data, storage = _build_reviewer(col_vals={"score": 0})
        reviewer.set_value("score", 1)
        # set_dtype should be called for the modified field
        calls = [str(c) for c in data.set_dtype.call_args_list]
        assert any("score_modified" in c for c in calls)

    def test_set_value_triggers_created_timestamp_when_absent(self):
        reviewer, data, storage = _build_reviewer(col_vals={"score": 0})
        reviewer.set_value("score", 1)
        calls = [str(c) for c in data.set_dtype.call_args_list]
        assert any("score_created" in c for c in calls)


# ---------------------------------------------------------------------------
# Tests: persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_save_flows_delegates_to_data(self):
        import os

        reviewer, data, _ = _build_reviewer()
        reviewer._directory = os.getcwd()  # valid path, chdir is a no-op
        reviewer.save_flows()
        data.save_flows.assert_called_once()

    def test_load_flows_delegates_to_data(self):
        import os
        from unittest.mock import MagicMock, patch

        reviewer, data, _ = _build_reviewer()
        reviewer._directory = os.getcwd()

        mock_new_data = MagicMock()
        mock_new_data.index = list(data.index)
        mock_new_data.get_index.return_value = data.index[0]

        with patch("referia.assess.data.CustomDataFrame.from_flow", return_value=mock_new_data):
            reviewer.load_flows()

    def test_load_flows_reload_kwarg_accepted(self):
        import os
        from unittest.mock import MagicMock, patch

        reviewer, data, _ = _build_reviewer()
        reviewer._directory = os.getcwd()

        mock_new_data = MagicMock()
        mock_new_data.index = list(data.index)
        mock_new_data.get_index.return_value = data.index[0]

        with patch("referia.assess.data.CustomDataFrame.from_flow", return_value=mock_new_data):
            reviewer.load_flows(reload=True)

    # ------------------------------------------------------------------
    # chdir tests — the fix for "first save works, later saves don't"
    # ------------------------------------------------------------------

    def test_save_flows_chdirs_to_review_directory(self):
        """save_flows must chdir to _directory so relative file paths resolve."""
        import os
        from unittest.mock import patch, call

        reviewer, data, _ = _build_reviewer()
        reviewer._directory = "/fake/review/dir"

        chdir_calls = []
        orig_getcwd = os.getcwd()

        with patch("os.chdir", side_effect=lambda p: chdir_calls.append(p)) as mock_chdir:
            with patch("os.getcwd", return_value=orig_getcwd):
                reviewer.save_flows()

        # First chdir: into the review directory
        assert chdir_calls[0] == "/fake/review/dir"
        # Second chdir: back to original
        assert chdir_calls[1] == orig_getcwd

    def test_save_flows_restores_directory_on_exception(self):
        """chdir back to original directory even when save_flows raises."""
        import os
        from unittest.mock import patch

        reviewer, data, _ = _build_reviewer()
        reviewer._directory = "/fake/review/dir"
        data.save_flows.side_effect = OSError("disk full")

        orig = os.getcwd()
        chdir_calls = []

        with patch("os.chdir", side_effect=lambda p: chdir_calls.append(p)):
            with patch("os.getcwd", return_value=orig):
                with pytest.raises(OSError):
                    reviewer.save_flows()

        # Must still have changed back even on failure
        assert chdir_calls[-1] == orig

    def test_load_flows_chdirs_to_review_directory(self):
        """load_flows must chdir to _directory so data files are found."""
        import os
        from unittest.mock import patch, MagicMock

        reviewer, data, _ = _build_reviewer()
        reviewer._directory = "/fake/review/dir"

        chdir_calls = []
        orig = os.getcwd()

        mock_new_data = MagicMock()
        mock_new_data.index = ["row0"]
        mock_new_data.get_index.return_value = "row0"

        with patch("os.chdir", side_effect=lambda p: chdir_calls.append(p)):
            with patch("os.getcwd", return_value=orig):
                with patch(
                    "referia.assess.data.CustomDataFrame.from_flow",
                    return_value=mock_new_data,
                ):
                    reviewer.load_flows()

        assert chdir_calls[0] == "/fake/review/dir"
        assert chdir_calls[-1] == orig

    def test_save_flows_data_sees_review_directory_as_cwd(self):
        """data.save_flows() is called only after chdir(_directory), not before.

        Verifies that the chdir to the review directory happens *before*
        delegating to ``data.save_flows()``, so relative paths inside the data
        layer resolve against the review directory.
        """
        import os
        from unittest.mock import patch, call

        reviewer, data, _ = _build_reviewer()
        reviewer._directory = "/fake/review/dir"

        call_log: list[str] = []

        def _fake_chdir(path: str) -> None:
            call_log.append(f"chdir:{path}")

        def _fake_save_flows() -> None:
            call_log.append("save_flows")

        data.save_flows.side_effect = _fake_save_flows
        orig = os.getcwd()

        with patch("os.chdir", side_effect=_fake_chdir):
            with patch("os.getcwd", return_value=orig):
                reviewer.save_flows()

        # chdir to review dir must happen before save_flows
        assert call_log.index(f"chdir:{reviewer._directory}") < call_log.index("save_flows")
        # restore-chdir must happen after save_flows
        assert call_log.index(f"chdir:{orig}") > call_log.index("save_flows")


# ---------------------------------------------------------------------------
# Tests: widget spec extraction
# ---------------------------------------------------------------------------


class TestGetWidgetSpecs:
    def test_empty_interface_returns_empty_list(self):
        reviewer, _, _ = _build_reviewer(review=[], viewer=[])
        assert reviewer.get_widget_specs() == []

    def test_flat_review_items_returned(self):
        specs = [
            {"type": "Textarea", "field": "summary"},
            {"type": "IntSlider", "field": "score"},
        ]
        reviewer, _, _ = _build_reviewer(review=specs)
        result = reviewer.get_widget_specs()
        assert len(result) == 2
        assert result[0]["field"] == "summary"
        assert result[1]["field"] == "score"

    def test_viewer_items_prepended_to_review(self):
        viewer = [{"type": "Markdown", "display": "## Title"}]
        review = [{"type": "Textarea", "field": "notes"}]
        reviewer, _, _ = _build_reviewer(review=review, viewer=viewer)
        result = reviewer.get_widget_specs()
        assert len(result) == 2
        assert result[0]["type"] == "Markdown"
        assert result[1]["type"] == "Textarea"

    def test_group_cluster_flattened(self):
        group = {
            "type": "group",
            "entries": [
                {"type": "Text", "field": "name"},
                {"type": "IntText", "field": "age"},
            ],
        }
        reviewer, _, _ = _build_reviewer(review=[group])
        result = reviewer.get_widget_specs()
        assert len(result) == 2
        assert result[0]["field"] == "name"

    def test_nested_clusters_flattened(self):
        inner = {
            "type": "group",
            "entries": [{"type": "Checkbox", "field": "flag"}],
        }
        outer = {"type": "group", "entries": [inner]}
        reviewer, _, _ = _build_reviewer(review=[outer])
        result = reviewer.get_widget_specs()
        assert len(result) == 1
        assert result[0]["field"] == "flag"

    def test_precompute_cluster_skipped(self):
        precompute = {"type": "precompute", "specifications": []}
        leaf = {"type": "Text", "field": "val"}
        reviewer, _, _ = _build_reviewer(review=[precompute, leaf])
        result = reviewer.get_widget_specs()
        assert len(result) == 1
        assert result[0]["field"] == "val"

    def test_non_list_viewer_wrapped(self):
        viewer = {"type": "Markdown", "display": "text"}
        reviewer, _, _ = _build_reviewer(viewer=viewer)
        reviewer._interface.get = lambda k, d=None: (
            viewer if k == "viewer" else ([] if k == "review" else d)
        )
        result = reviewer.get_widget_specs()
        assert result[0]["type"] == "Markdown"


# ---------------------------------------------------------------------------
# Tests: affected_widgets
# ---------------------------------------------------------------------------


class TestAffectedWidgets:
    def test_returns_all_field_columns(self):
        specs = [
            {"type": "Text", "field": "name"},
            {"type": "IntSlider", "field": "score"},
            {"type": "SaveButton"},  # no field
        ]
        reviewer, _, _ = _build_reviewer(review=specs)
        affected = reviewer.affected_widgets("name")
        assert "name" in affected
        assert "score" in affected
        assert len(affected) == 2

    def test_affected_widgets_ignores_button_types(self):
        specs = [
            {"type": "PopulateButton"},
            {"type": "Textarea", "field": "text"},
        ]
        reviewer, _, _ = _build_reviewer(review=specs)
        assert reviewer.affected_widgets("text") == {"text"}


# ---------------------------------------------------------------------------
# Tests: combinator update on set_value
# ---------------------------------------------------------------------------


class TestCombinatorUpdate:
    def test_combinator_field_updated_after_set_value(self):
        combinator = [{"field": "total", "liquid": "{{a}} {{b}}"}]
        reviewer, data, storage = _build_reviewer(
            col_vals={"score": 0},
            combinator=combinator,
        )
        data.viewer_to_value.return_value = "combined_value"

        reviewer.set_value("score", 3)

        # viewer_to_value should have been called with combinator spec (sans "field")
        data.viewer_to_value.assert_called_once_with({"liquid": "{{a}} {{b}}"})
        # and the result stored in "total"
        assert storage.get("total") == "combined_value"
