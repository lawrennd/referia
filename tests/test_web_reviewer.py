"""Unit tests for referia.assess.web_review.WebReviewer.

All tests use unittest.mock to avoid requiring a real _referia.yml file or
any I/O.  The Interface and CustomDataFrame dependencies are patched so we can
exercise WebReviewer's logic in isolation.
"""

from __future__ import annotations

import types
from pathlib import Path
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
    extra=None,
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
    if extra:
        data.update(extra)

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
        col = current_col[0]
        idx = current_index[0]
        if (idx, col) in storage:
            return storage[(idx, col)]
        return storage.get(col)

    def _set_value(v):
        col = current_col[0]
        idx = current_index[0]
        storage[(idx, col)] = v
        storage[col] = v

    data.get_value.side_effect = _get_value
    data.set_value.side_effect = _set_value

    def _at_access(idx, col):
        if (idx, col) in storage:
            return storage[(idx, col)]
        return storage.get(col)

    data.at.__getitem__ = lambda self_inner, key: _at_access(*key)

    data.get_value_column.side_effect = lambda col: col  # identity
    data.save_flows.return_value = None
    data.load_flows.return_value = None
    data.set_dtype.return_value = None
    data.viewer_to_value.return_value = "combined"
    data.view_to_value.return_value = "combined"

    def _to_pandas():
        cols = [c for c in storage if not isinstance(c, tuple)]
        return pd.DataFrame({c: storage.get(c) for c in cols}, index=index_vals)

    data.to_pandas.side_effect = _to_pandas

    return data, storage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _build_reviewer(review=None, viewer=None, index_vals=None, col_vals=None, combinator=None, extra=None):
    """Construct a WebReviewer with patched Interface and CustomDataFrame."""
    from referia.assess.web_review import WebReviewer

    iface = _make_interface(
        review=review,
        viewer=viewer,
        combinator=combinator,
        extra=extra,
    )
    data, storage = _make_data(index_vals=index_vals, col_vals=col_vals)

    reviewer = WebReviewer.__new__(WebReviewer)
    reviewer._interface = iface
    reviewer._data = data
    reviewer._directory = "/tmp"
    reviewer._filter_state = reviewer.get_filter_defaults()
    reviewer._field_defaults = reviewer._build_field_defaults()
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

    def test_from_file_keeps_path_jail(self, tmp_path):
        """WebReviewer must not opt out of CIP-000A path jail (HTTP-shared)."""
        from referia.assess.web_review import WebReviewer

        cfg = tmp_path / "_referia.yml"
        cfg.write_text(
            "referia_config_version: 1\n"
            "title: jail-default\n"
            "strict_columns: false\n"
            "allocation:\n"
            "  type: fake\n"
            "  index: Name\n"
            "  nrows: 1\n"
            "  cols:\n"
            "    - Name\n"
        )
        captured = {}

        def _capture_from_file(*args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            iface = _make_interface()
            return iface

        mock_data, _ = _make_data(index_vals=["a"])
        with patch(
            "referia.config.interface.Interface.from_file",
            side_effect=_capture_from_file,
        ), patch(
            "referia.assess.data.CustomDataFrame.from_flow",
            return_value=mock_data,
        ):
            WebReviewer("_referia.yml", str(tmp_path))

        assert captured["kwargs"].get("unbounded_paths") is not True
        # Must stay jailed (no unbounded opt-out); sibling parent may be listed.
        assert "unbounded_paths" not in captured["kwargs"]
        roots = captured["kwargs"].get("allowed_roots") or []
        assert str(tmp_path.resolve()) in [str(Path(r).resolve()) for r in roots]


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

    def test_string_query_coerces_to_integer_label(self):
        """HTMX sends index=2 as str; allocation may use int Project number."""
        reviewer, data, _ = _build_reviewer(index_vals=[1, 2, 3])
        reviewer.set_index("2")
        data.set_index.assert_called_with(2)
        assert reviewer.get_index() == 2

    def test_typed_integer_label_still_works(self):
        reviewer, data, _ = _build_reviewer(index_vals=[1, 2, 3])
        reviewer.set_index(2)
        data.set_index.assert_called_with(2)

    def test_string_labels_unchanged(self):
        reviewer, data, _ = _build_reviewer(index_vals=["alice", "bob"])
        reviewer.set_index("bob")
        data.set_index.assert_called_with("bob")

    def test_missing_label_raises_keyerror(self):
        reviewer, _, _ = _build_reviewer(index_vals=[1, 2, 3])
        with pytest.raises(KeyError, match="not found"):
            reviewer.set_index("99")

    def test_numeric_string_is_label_not_positional(self):
        """index='2' must mean label 2, not index_list()[2] (which would be 3)."""
        reviewer, data, _ = _build_reviewer(index_vals=[1, 2, 3])
        reviewer.set_index("2")
        data.set_index.assert_called_with(2)
        assert data.set_index.call_args[0][0] != 3


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

    def test_section_preserved_in_review_specs_flattened_in_widget_specs(self):
        section = {
            "type": "Section",
            "title": "Chapter 1",
            "entries": [
                {"type": "Textarea", "field": "ch1Summary"},
                {"type": "Checkbox", "field": "ch1Flag"},
            ],
        }
        reviewer, _, _ = _build_reviewer(review=[section])
        review_specs = reviewer.get_review_specs()
        assert len(review_specs) == 1
        assert review_specs[0]["type"] == "Section"
        assert review_specs[0]["title"] == "Chapter 1"
        assert [e["field"] for e in review_specs[0]["entries"]] == [
            "ch1Summary",
            "ch1Flag",
        ]
        flat = reviewer.get_widget_specs()
        assert [e["field"] for e in flat] == ["ch1Summary", "ch1Flag"]

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

    def test_precompute_specs_not_flattened_as_widgets(self):
        """Non-empty precompute must not become form widgets (visible_if OOB)."""
        soft_fill = {
            "field": "Email Comment",
            "function": "render_liquid",
            "args": {"template": "hello"},
        }
        textarea = {
            "type": "Textarea",
            "field": "Email Comment",
            "visible_if": "Interview",
            "args": {"description": "Email Comment"},
        }
        precompute = {"type": "precompute", "specifications": [soft_fill]}
        reviewer, _, _ = _build_reviewer(review=[precompute, textarea])
        result = reviewer.get_widget_specs()
        assert len(result) == 1
        assert result[0]["type"] == "Textarea"
        assert result[0].get("visible_if") == "Interview"

    def test_postcompute_specs_not_flattened_as_widgets(self):
        soft_fill = {
            "field": "Email Comment",
            "function": "render_liquid",
            "args": {"template": "bye"},
        }
        textarea = {
            "type": "Textarea",
            "field": "Email Comment",
            "args": {"description": "Email Comment"},
        }
        postcompute = {"type": "postcompute", "specifications": [soft_fill]}
        reviewer, _, _ = _build_reviewer(review=[textarea, postcompute])
        result = reviewer.get_widget_specs()
        assert len(result) == 1
        assert result[0]["type"] == "Textarea"

    def test_nested_precompute_not_in_widget_specs(self):
        """precompute under a group is registered but never flattened as widgets."""
        soft_fill = {
            "field": "Candidate Email",
            "function": "render_liquid",
            "args": {"template": "{{x}}"},
        }
        review = [
            {
                "type": "group",
                "entries": [
                    {"type": "precompute", "specifications": [soft_fill]},
                    {
                        "type": "Text",
                        "field": "Candidate Email",
                        "args": {"description": "Email"},
                    },
                ],
            }
        ]
        reviewer, data, _ = _build_reviewer(review=review)
        data._precompute = []
        reviewer._register_review_computes()
        assert data._precompute == [soft_fill]
        widgets = reviewer.get_widget_specs()
        assert len(widgets) == 1
        assert widgets[0]["type"] == "Text"
        assert widgets[0]["field"] == "Candidate Email"

    def test_register_review_computes_copies_precompute_specs(self):
        """CoE 2026-10-18: precompute must be registered, not only skipped as widgets."""
        specs = [
            {"field": "email", "function": "render_liquid", "args": {"template": "x"}},
            {"field": "applicant", "function": "extract_form_fields"},
        ]
        precompute = {"type": "precompute", "specifications": specs}
        reviewer, data, _ = _build_reviewer(review=[precompute])
        data._precompute = []
        data._postcompute = []
        reviewer._register_review_computes()
        assert data._precompute == specs

    def test_set_index_chdirs_to_review_directory(self, tmp_path, monkeypatch):
        """compute_pre must see config-relative paths (serve cwd ≠ review dir)."""
        import os

        review_dir = tmp_path / "review"
        review_dir.mkdir()
        serve_cwd = tmp_path / "serve"
        serve_cwd.mkdir()
        monkeypatch.chdir(serve_cwd)

        seen = {}

        def _set_index(label):
            seen["cwd"] = os.getcwd()
            seen["label"] = label

        reviewer, data, _ = _build_reviewer(index_vals=["r0", "r1"])
        reviewer._directory = str(review_dir.resolve())
        data.set_index.side_effect = _set_index
        reviewer.set_index("r1")
        assert Path(seen["cwd"]).resolve() == review_dir.resolve()
        assert seen["label"] == "r1"
        assert Path(os.getcwd()).resolve() == serve_cwd.resolve()

    def test_non_list_viewer_wrapped(self):
        viewer = {"type": "Markdown", "display": "text"}
        reviewer, _, _ = _build_reviewer(viewer=viewer)
        reviewer._interface.get = lambda k, d=None: (
            viewer if k == "viewer" else ([] if k == "review" else d)
        )
        result = reviewer.get_widget_specs()
        assert result[0]["type"] == "Markdown"


# ---------------------------------------------------------------------------
# Tests: review precompute / postcompute registration (CoE 2026-10-18)
# ---------------------------------------------------------------------------


class TestReviewComputeRegistration:
    def test_register_postcompute_and_single_spec(self):
        """postcompute list + non-list specification both land on the data object."""
        post_list = [{"field": "summary", "function": "render_liquid"}]
        post_one = {"field": "flag", "function": "identity"}
        pre_one = {"field": "email", "function": "render_liquid"}
        review = [
            "skip-me",  # non-dict ignored
            {"type": "precompute", "specifications": pre_one},
            {"type": "postcompute", "specifications": post_list},
            {"type": "postcompute", "specifications": post_one},
        ]
        reviewer, data, _ = _build_reviewer(review=review)
        reviewer._register_review_computes()
        assert data._precompute == [pre_one]
        assert data._postcompute == post_list + [post_one]

    def test_collect_nested_precompute_under_group(self):
        """precompute nested under cluster types must still be registered."""
        nested_specs = [{"field": "applicant", "function": "extract_form_fields"}]
        review = [
            {
                "type": "group",
                "children": [
                    {"type": "precompute", "specifications": nested_specs},
                    {"type": "Text", "field": "notes"},
                ],
            }
        ]
        reviewer, data, _ = _build_reviewer(review=review)
        reviewer._register_review_computes()
        assert data._precompute == nested_specs

    def test_compute_field_names_filters_placeholders(self):
        reviewer, _, _ = _build_reviewer()
        names = reviewer._compute_field_names(
            [
                "not-a-dict",
                {"function": "noop"},  # no field
                {"field": "_"},
                {"field": ["email", "_", "", "name"]},
                {"field": "solo"},
            ]
        )
        assert names == ["email", "name", "solo"]

    def test_ensure_compute_target_columns_creates_missing(self):
        """Missing soft-fill targets are created via cache __setitem__."""
        specs = [
            {"field": "applicant", "function": "extract_form_fields"},
            {"field": "email", "function": "render_liquid"},
        ]
        reviewer, data, _ = _build_reviewer(
            review=[{"type": "precompute", "specifications": specs}],
            col_vals={"email": "already@example.com"},
        )
        # Real list so membership checks work; MagicMock columns is a list above.
        data.columns = ["email"]
        assigned = {}

        def _setitem(key, value):
            assigned[key] = value
            if key not in data.columns:
                data.columns = list(data.columns) + [key]

        data.__setitem__.side_effect = _setitem
        data._precompute = specs
        data._postcompute = []
        reviewer._ensure_compute_target_columns()
        assert "applicant" in assigned
        assert assigned["applicant"] is None
        assert "email" not in assigned  # already present

    def test_ensure_includes_top_level_compute_list_and_dict(self):
        reviewer, data, _ = _build_reviewer(
            extra={
                "compute": [
                    {"field": "from_list", "function": "render_liquid"},
                ]
            }
        )
        data.columns = []
        assigned = {}
        data.__setitem__.side_effect = lambda k, v: assigned.__setitem__(k, v)
        data._precompute = []
        data._postcompute = []
        reviewer._ensure_compute_target_columns()
        assert "from_list" in assigned

        # dict form of top-level compute
        iface = _make_interface(extra={"compute": {"field": "from_dict", "function": "noop"}})
        reviewer._interface = iface
        assigned.clear()
        reviewer._ensure_compute_target_columns()
        assert "from_dict" in assigned

    def test_run_interface_compute_chdirs_and_delegates(self, tmp_path, monkeypatch):
        import os

        review_dir = tmp_path / "review"
        review_dir.mkdir()
        other = tmp_path / "other"
        other.mkdir()
        monkeypatch.chdir(other)

        seen = {}
        reviewer, data, _ = _build_reviewer(
            extra={"compute": [{"field": "x", "function": "noop"}]}
        )
        reviewer._directory = str(review_dir.resolve())
        compute = MagicMock()

        def _run(df, cfg):
            seen["cwd"] = os.getcwd()
            seen["cfg"] = cfg

        compute.run.side_effect = _run
        data._compute = compute
        reviewer._run_interface_compute()
        assert Path(seen["cwd"]).resolve() == review_dir.resolve()
        assert seen["cfg"] == {"compute": [{"field": "x", "function": "noop"}]}
        assert Path(os.getcwd()).resolve() == other.resolve()

    def test_run_interface_compute_noop_without_compute(self):
        reviewer, data, _ = _build_reviewer()
        data._compute = MagicMock()
        reviewer._run_interface_compute()
        data._compute.run.assert_not_called()

    def test_load_flows_reregisters_and_runs_compute(self, tmp_path, monkeypatch):
        """reload path must re-register precompute and run top-level compute."""
        import os

        review_dir = tmp_path / "review"
        review_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        specs = [{"field": "applicant", "function": "extract_form_fields"}]
        reviewer, data, _ = _build_reviewer(
            review=[{"type": "precompute", "specifications": specs}],
            extra={"compute": [{"field": "x", "function": "noop"}]},
            index_vals=["r0", "r1"],
        )
        reviewer._directory = str(review_dir.resolve())
        reviewer.set_index("r1")  # side_effect-backed get_index tracks this

        mock_new = MagicMock()
        mock_new.index = ["r0", "r1"]
        mock_new.columns = []
        mock_new._compute = MagicMock()
        assigned = {}
        mock_new.__setitem__.side_effect = lambda k, v: assigned.__setitem__(k, v)

        with patch(
            "referia.assess.data.CustomDataFrame.from_flow",
            return_value=mock_new,
        ):
            reviewer.load_flows(reload=True)

        assert mock_new._precompute == specs
        assert "applicant" in assigned
        mock_new.set_index.assert_called_with("r1")
        mock_new._compute.run.assert_called_once()
        assert Path(os.getcwd()).resolve() == tmp_path.resolve()

    def test_init_registers_computes_and_runs_interface_compute(self, tmp_path):
        """Real __init__ must register review computes before first set_index."""
        from referia.assess.web_review import WebReviewer

        cfg = tmp_path / "_referia.yml"
        cfg.write_text(
            "referia_config_version: 1\n"
            "title: compute-init\n"
            "strict_columns: false\n"
            "allocation:\n"
            "  type: fake\n"
            "  index: Name\n"
            "  nrows: 1\n"
            "  cols:\n"
            "    - Name\n"
        )
        specs = [{"field": "applicant", "function": "extract_form_fields"}]
        iface = _make_interface(
            review=[{"type": "precompute", "specifications": specs}],
            extra={"compute": [{"field": "ready", "function": "noop"}]},
        )
        mock_data, _ = _make_data(index_vals=["a"])
        mock_data.columns = []
        mock_data._compute = MagicMock()
        assigned = {}
        mock_data.__setitem__.side_effect = lambda k, v: assigned.__setitem__(k, v)

        with patch(
            "referia.config.interface.Interface.from_file",
            return_value=iface,
        ), patch(
            "referia.assess.data.CustomDataFrame.from_flow",
            return_value=mock_data,
        ):
            WebReviewer("_referia.yml", str(tmp_path))

        assert mock_data._precompute == specs
        assert "applicant" in assigned
        mock_data.set_index.assert_called()
        mock_data._compute.run.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: affected_widgets
# ---------------------------------------------------------------------------


class TestAffectedWidgets:
    def test_independent_fields_not_affected(self):
        """Blur refresh must not rebuild unrelated fields (focus preserve)."""
        specs = [
            {"type": "Text", "field": "name"},
            {"type": "IntSlider", "field": "score"},
            {"type": "SaveButton"},  # no field
        ]
        reviewer, _, _ = _build_reviewer(review=specs)
        assert reviewer.affected_widgets("name") == set()

    def test_visible_if_dependent_is_affected(self):
        specs = [
            {"type": "Checkbox", "field": "Interview"},
            {
                "type": "Textarea",
                "field": "Email Comment",
                "visible_if": "Interview",
            },
        ]
        reviewer, _, _ = _build_reviewer(review=specs)
        assert reviewer.affected_widgets("Interview") == {"Email Comment"}

    def test_visible_if_dict_form_is_affected(self):
        specs = [
            {"type": "Text", "field": "Status"},
            {
                "type": "Textarea",
                "field": "Notes",
                "visible_if": {"field": "Status", "equals": "yes"},
            },
        ]
        reviewer, _, _ = _build_reviewer(review=specs)
        assert reviewer.affected_widgets("Status") == {"Notes"}

    def test_combinator_widget_field_is_affected(self):
        specs = [
            {"type": "IntSlider", "field": "score"},
            {"type": "Text", "field": "total"},
        ]
        reviewer, _, _ = _build_reviewer(
            review=specs,
            combinator=[{"field": "total", "liquid": "{{score}}"}],
        )
        assert reviewer.affected_widgets("score") == {"total"}

    def test_affected_widgets_ignores_button_types(self):
        specs = [
            {"type": "PopulateButton"},
            {"type": "Textarea", "field": "text"},
        ]
        reviewer, _, _ = _build_reviewer(review=specs)
        assert reviewer.affected_widgets("text") == set()


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


class TestGetRowData:
    """Tests for WebReviewer.get_row_data().

    get_row_data() must return ALL column values for the current row,
    not just those that have associated widgets.  This is required so that
    visible_if conditions can be evaluated against flag columns (e.g.
    "abstractPresent") that exist only in the data source, not as widgets.
    """

    def test_returns_widget_fields(self):
        reviewer, _, storage = _build_reviewer(
            col_vals={"score": 5, "comment": "good"},
        )
        result = reviewer.get_row_data()
        assert result["score"] == 5
        assert result["comment"] == "good"

    def test_returns_non_widget_flag_fields(self):
        """Columns used in visible_if but with no widget must appear in the result."""
        reviewer, _, storage = _build_reviewer(
            col_vals={"score": 5, "abstractPresent": True, "forewordPresent": False},
        )
        result = reviewer.get_row_data()
        assert result["abstractPresent"] == True  # noqa: E712 (numpy bool compat)
        assert result["forewordPresent"] == False  # noqa: E712 (numpy bool compat)

    def test_nan_values_normalised_to_none(self):
        """NaN (unset float columns) must be normalised to None."""
        import math

        reviewer, _, _ = _build_reviewer(
            col_vals={"score": float("nan")},
        )
        result = reviewer.get_row_data()
        assert result["score"] is None

    def test_includes_constants_when_to_pandas_fails(self):
        """to_pandas() overlap errors must not blank global_consts used in Liquid."""
        reviewer, data, _ = _build_reviewer(
            col_vals={"score": 1, "q1Question": "How many integers?"},
        )
        data.to_pandas.side_effect = ValueError("columns overlap but no suffix specified")
        result = reviewer.get_row_data()
        assert result["q1Question"] == "How many integers?"
        assert result["score"] == 1

    def test_empty_row_when_columns_unavailable(self):
        """If the column list cannot be read, return an empty dict."""
        reviewer, data, _ = _build_reviewer(col_vals={"score": 1})

        class _BoomColumns:
            def __iter__(self):
                raise RuntimeError("no columns")

        data.columns = _BoomColumns()
        result = reviewer.get_row_data()
        assert result == {}

    def test_includes_mapping_aliases(self):
        """Liquid keys such as {{Title}} must resolve via input mapping aliases."""
        reviewer, data, _ = _build_reviewer(
            col_vals={"Project title": "Toolkit for misuse", "score": 1},
        )
        data._name_column_map = {"Title": "Project title"}
        result = reviewer.get_row_data()
        assert result["Project title"] == "Toolkit for misuse"
        assert result["Title"] == "Toolkit for misuse"

    def test_mapping_alias_from_get_value_when_column_not_listed(self):
        """Aliases whose source column is missing from .columns still use get_value."""
        reviewer, data, _ = _build_reviewer(col_vals={"score": 1})
        data._name_column_map = {"Title": "Project title"}

        orig_get = reviewer.get_value

        def _get(column):
            if column == "Project title":
                return "Toolkit for misuse"
            return orig_get(column)

        reviewer.get_value = _get
        result = reviewer.get_row_data()
        assert result["Title"] == "Toolkit for misuse"

    def test_interface_mapping_covers_index_alias(self):
        """YAML mapping onto the index (number → Project number) must still fill."""
        reviewer, data, _ = _build_reviewer(col_vals={"score": 1})
        data._name_column_map = {}
        orig_get = reviewer.get_value

        def _get(column):
            if column == "Project number":
                return 1
            return orig_get(column)

        reviewer.get_value = _get
        reviewer._interface.__contains__ = lambda self, k: k == "input"
        reviewer._interface.__getitem__ = lambda self, k: {
            "input": {"mapping": {"number": "Project number"}}
        }[k]
        result = reviewer.get_row_data()
        assert result["number"] == 1


class TestDocumentEntries:
    def test_list_url_entries(self):
        reviewer, _, _ = _build_reviewer(
            extra={"urls": [{"url": "https://example.com/p?q="}]},
        )
        entries = reviewer.list_url_entries()
        assert entries == [{"href": "https://example.com/p?q=", "label": "https://example.com/p?q="}]

    def test_list_pdf_entries_localpdf(self, tmp_path):
        pdf = tmp_path / "thesis.pdf"
        pdf.write_bytes(b"%PDF-1.1\n%%EOF\n")
        reviewer, _, _ = _build_reviewer(
            col_vals={"ThesisPDF": "thesis.pdf"},
            extra={"localpdf": [{"directory": str(tmp_path), "field": "ThesisPDF", "name": "thesis"}]},
        )
        reviewer._directory = str(tmp_path)
        entries = reviewer.list_pdf_entries()
        assert len(entries) == 1
        assert entries[0]["kind"] == "localpdf"
        assert entries[0]["exists"] is True
        assert entries[0]["label"] == "thesis"

    def test_get_record_document_missing_field(self, tmp_path):
        reviewer, _, _ = _build_reviewer(
            extra={"localpdf": [{"directory": str(tmp_path), "field": "ThesisPDF"}]},
        )
        assert reviewer.get_record_document("localpdf", 0) is None

    def test_relative_directory_uses_config_dir_not_cwd(self, tmp_path, monkeypatch):
        """Relative localpdf directories must join to the config dir, not process cwd."""
        config_dir = tmp_path / "preliminary"
        files_dir = tmp_path / "files"
        other_cwd = tmp_path / "elsewhere"
        config_dir.mkdir()
        files_dir.mkdir()
        other_cwd.mkdir()
        pdf = files_dir / "app.pdf"
        pdf.write_bytes(b"%PDF-1.1\n%%EOF\n")

        reviewer, _, _ = _build_reviewer(
            col_vals={"ApplicationPDF": "app.pdf"},
            extra={"localpdf": [{"directory": "../files", "field": "ApplicationPDF", "name": "app"}]},
        )
        reviewer._directory = str(config_dir)
        monkeypatch.chdir(other_cwd)

        path = reviewer.get_record_document("localpdf", 0)
        assert path == pdf.resolve()
        entries = reviewer.list_pdf_entries()
        assert entries[0]["exists"] is True

        roots = reviewer.allowed_roots_for_document("localpdf", 0)
        assert files_dir.resolve() in roots

    def test_absolute_directory_still_works(self, tmp_path):
        pdf = tmp_path / "abs.pdf"
        pdf.write_bytes(b"%PDF-1.1\n%%EOF\n")
        reviewer, _, _ = _build_reviewer(
            col_vals={"ThesisPDF": "abs.pdf"},
            extra={"localpdf": [{"directory": str(tmp_path), "field": "ThesisPDF"}]},
        )
        reviewer._directory = str(tmp_path / "config")
        path = reviewer.get_record_document("localpdf", 0)
        assert path == pdf.resolve()

    def test_home_env_directory_still_works(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        pdf = home / "home.pdf"
        pdf.write_bytes(b"%PDF-1.1\n%%EOF\n")
        monkeypatch.setenv("HOME", str(home))
        reviewer, _, _ = _build_reviewer(
            col_vals={"ThesisPDF": "home.pdf"},
            extra={"localpdf": [{"directory": "$HOME", "field": "ThesisPDF"}]},
        )
        reviewer._directory = str(tmp_path / "config")
        path = reviewer.get_record_document("localpdf", 0)
        assert path == pdf.resolve()

    def test_editpdf_relative_source_and_store(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "review"
        source_dir = tmp_path / "source"
        store_dir = tmp_path / "annotated"
        other_cwd = tmp_path / "cwd"
        for d in (config_dir, source_dir, store_dir, other_cwd):
            d.mkdir()
        src_pdf = source_dir / "thesis.pdf"
        src_pdf.write_bytes(b"%PDF-1.1\n%%EOF\n")

        reviewer, _, _ = _build_reviewer(
            index_vals=["Alice"],
            col_vals={"ThesisPDF": "thesis.pdf"},
            extra={
                "editpdf": [{
                    "sourcedirectory": "../source",
                    "storedirectory": "../annotated",
                    "field": "ThesisPDF",
                    "name": "abstract",
                }],
            },
        )
        reviewer._directory = str(config_dir)
        monkeypatch.chdir(other_cwd)

        path = reviewer.get_record_document("editpdf", 0)
        assert path == src_pdf.resolve()
        roots = reviewer.allowed_roots_for_document("editpdf", 0)
        assert source_dir.resolve() in roots
        assert store_dir.resolve() in roots


class TestDocumentGeneration:
    def test_list_document_entries(self):
        reviewer, _, _ = _build_reviewer(
            extra={
                "documents": [
                    {"type": "docx", "name": "Letter"},
                    {"type": "email"},
                    {
                        "type": "docx",
                        "title": {"liquid": "Draft Thesis Review"},
                    },
                    {
                        "type": "docx",
                        "title": {"liquid": "Document Conversation: {{title}}"},
                    },
                ],
                "summary_documents": [{"type": "markdown"}],
            }
        )
        docs = reviewer.list_document_entries("documents")
        assert docs[0]["label"] == "Letter"
        assert docs[1]["label"] == "Create email"
        assert docs[2]["label"] == "Create Draft Thesis Review"
        assert docs[3]["label"] == "Create Document Conversation"
        summary = reviewer.list_document_entries("summary_documents")
        assert summary[0]["label"] == "Create Summary markdown"
        assert summary[0]["summary"] is True

    def test_list_document_entries_preserves_visible_if(self):
        reviewer, _, _ = _build_reviewer(
            extra={
                "documents": [
                    {"type": "email", "visible_if": "Interview"},
                    {"type": "docx", "name": "Always"},
                ],
            }
        )
        docs = reviewer.list_document_entries("documents")
        assert docs[0]["visible_if"] == "Interview"
        assert "visible_if" not in docs[1]

    def test_template_to_value_viewer(self):
        reviewer, data, _ = _build_reviewer(
            viewer=[{"liquid": "Hello {{name}}"}],
        )
        data.view_to_value.return_value = "Hello Alice"
        text = reviewer.template_to_value({"use": "viewer"})
        assert "Hello Alice" in text
        data.view_to_value.assert_called()

    def test_create_markdown_writes_without_open(self, tmp_path):
        out = tmp_path / "out.md"
        reviewer, data, _ = _build_reviewer(
            extra={
                "documents": [
                    {
                        "type": "markdown",
                        "filename": str(out.name),
                        "directory": str(tmp_path),
                        "content": "static body",
                    }
                ]
            }
        )
        reviewer._directory = str(tmp_path)
        data.view_to_value.side_effect = lambda t: t

        def _write(data, filename, content, include_content=True):
            Path(filename).write_text(content or "", encoding="utf-8")

        with patch("lynguine.access.io.write_markdown_file", side_effect=_write) as writer:
            with patch("referia.system.Sys.open_localfile") as open_local:
                result = reviewer.generate_document(0, summary=False)
                open_local.assert_not_called()
            writer.assert_called_once()

        assert result["status"] == "created"
        assert result["type"] == "markdown"
        assert out.is_file()
        assert result["href"] == f"/document/{out.name}"

    def test_create_email_drafts(self, tmp_path):
        reviewer, _, _ = _build_reviewer(
            extra={
                "documents": [
                    {"type": "email", "to": "a@example.com", "title": "Hi", "content": "Body"}
                ]
            }
        )
        reviewer._directory = str(tmp_path)
        with patch.object(reviewer._system, "create_email") as draft:
            result = reviewer.generate_document(0)
            draft.assert_called_once()
        assert result["status"] == "drafted"
        assert result["href"] is None

    def test_summary_document_uses_working_indices(self, tmp_path):
        reviewer, data, storage = _build_reviewer(
            index_vals=["a", "b"],
            col_vals={"title": "", "complete": False},
            extra={
                "display": {"layout": "inline_list"},
                "filters": [{"field": "complete", "type": "boolean"}],
                "summary_documents": [
                    {
                        "type": "markdown",
                        "filename": {"display": "out.md"},
                        "body": {"liquid": "{{title}}\n"},
                    }
                ],
            },
        )
        reviewer._directory = str(tmp_path)
        storage[("a", "title")] = "Keep"
        storage[("a", "complete")] = False
        storage[("b", "title")] = "Drop"
        storage[("b", "complete")] = True
        reviewer.set_filter_state({"complete": "false"})

        # Resolve liquid body against the current row (mock default is "combined").
        def _view_to_value(template):
            if isinstance(template, dict) and "liquid" in template:
                return str(storage.get((data.get_index(), "title"), "") or "")
            if isinstance(template, dict) and "display" in template:
                return str(template["display"])
            return "combined"

        data.view_to_value.side_effect = _view_to_value

        written = {}

        def _write(*, data, filename, content):
            written["content"] = content
            Path(tmp_path, filename).write_text(content or "")

        with patch("lynguine.access.io.write_markdown_file", side_effect=_write):
            reviewer.generate_document(0, summary=True)
        assert "Keep" in written["content"]
        assert "Drop" not in written["content"]

    def test_ensure_edit_pdf_copies(self, tmp_path):
        config_dir = tmp_path / "review"
        source_dir = tmp_path / "source"
        store_dir = tmp_path / "annotated"
        for d in (config_dir, source_dir, store_dir):
            d.mkdir()
        src_pdf = source_dir / "thesis.pdf"
        src_pdf.write_bytes(b"%PDF-1.1\n%%EOF\n")

        reviewer, _, _ = _build_reviewer(
            index_vals=["Alice"],
            col_vals={"ThesisPDF": "thesis.pdf"},
            extra={
                "editpdf": [{
                    "sourcedirectory": str(source_dir),
                    "storedirectory": str(store_dir),
                    "field": "ThesisPDF",
                    "name": "abstract",
                }],
            },
        )
        reviewer._directory = str(config_dir)

        with patch.object(
            reviewer._system,
            "copy_file",
            side_effect=lambda orig, dest, view, data: Path(dest).write_bytes(
                Path(orig).read_bytes()
            ),
        ):
            dest = reviewer.ensure_edit_pdf(0)

        assert dest.is_file()
        assert dest.parent == store_dir.resolve()
        assert dest.name.startswith("Alice_")


# ---------------------------------------------------------------------------
# Tests: display.layout inline_list (CIP-0010)
# ---------------------------------------------------------------------------


class TestDisplayLayout:
    def test_default_side_by_side(self):
        reviewer, _, _ = _build_reviewer()
        assert reviewer.get_display_layout() == "side_by_side"

    def test_inline_list(self):
        reviewer, _, _ = _build_reviewer(extra={"display": {"layout": "inline_list"}})
        assert reviewer.get_display_layout() == "inline_list"

    def test_unknown_layout_raises(self):
        reviewer, _, _ = _build_reviewer(extra={"display": {"layout": "tableau"}})
        with pytest.raises(ValueError, match="Unknown display.layout"):
            reviewer.get_display_layout()


class TestRowsAndFilters:
    def test_get_rows_includes_index_and_columns(self):
        reviewer, _, storage = _build_reviewer(
            index_vals=["a", "b"],
            col_vals={"title": "shared"},
            extra={"display": {"layout": "inline_list"}},
        )
        storage[("a", "title")] = "Alpha"
        storage[("b", "title")] = "Beta"
        rows = reviewer.get_rows()
        assert [r["_index"] for r in rows] == ["a", "b"]
        assert rows[0]["title"] == "Alpha"
        assert rows[1]["title"] == "Beta"

    def test_boolean_filter_shrinks_working_set(self):
        reviewer, _, storage = _build_reviewer(
            index_vals=["a", "b", "c"],
            col_vals={"complete": False},
            extra={
                "display": {"layout": "inline_list"},
                "filters": [{"field": "complete", "type": "boolean"}],
            },
        )
        storage[("a", "complete")] = True
        storage[("b", "complete")] = False
        storage[("c", "complete")] = True
        reviewer.set_filter_state({"complete": "true"})
        assert reviewer.working_indices() == ["a", "c"]

    def test_boolean_filter_false_includes_unset(self):
        """Unset/NaN complete should match Complete=False (incomplete work)."""
        reviewer, _, storage = _build_reviewer(
            index_vals=["a", "b", "c"],
            col_vals={"title": "x"},
            review=[{"type": "Checkbox", "field": "complete", "default": False}],
            extra={
                "display": {"layout": "inline_list"},
                "filters": [{"field": "complete", "type": "boolean"}],
            },
        )
        storage[("a", "complete")] = True
        storage[("b", "complete")] = None
        storage[("c", "complete")] = False
        reviewer.set_filter_state({"complete": "false"})
        assert reviewer.working_indices() == ["b", "c"]

    def test_contains_filter_words_and_exact(self):
        reviewer, _, storage = _build_reviewer(
            index_vals=["a", "b", "c"],
            col_vals={"title": ""},
            extra={
                "display": {"layout": "inline_list"},
                "filters": [{"field": "title", "type": "contains"}],
            },
        )
        storage[("a", "title")] = "MPhil Admissions Interview"
        storage[("b", "title")] = "PhD admissions overview"
        storage[("c", "title")] = "Supervision notes"
        reviewer.set_filter_state(
            {"title": {"query": "admissions mphil", "mode": "words"}}
        )
        assert reviewer.working_indices() == ["a"]
        reviewer.set_filter_state(
            {"title": {"query": "admissions", "mode": "exact"}}
        )
        assert reviewer.working_indices() == ["a", "b"]
        reviewer.set_filter_state(
            {"title": {"query": "Admissions Interview", "mode": "exact"}}
        )
        assert reviewer.working_indices() == ["a"]

    def test_filter_defaults_seed_and_clear(self):
        from datetime import date

        from referia.assess.web_review import resolve_filter_defaults

        fixed = date(2026, 10, 11)
        resolved = resolve_filter_defaults(
            {
                "complete": False,
                "date": {"after": "today-30d", "before": "today+30d"},
                "_sort": "date:asc",
                "_group": "directory",
            },
            today=fixed,
        )
        assert resolved["complete"] == "false"
        assert resolved["date"]["after"] == "2026-09-11"
        assert resolved["date"]["before"] == "2026-11-10"
        assert resolved["_sort"] == "date:asc"
        assert resolved["_group"] == "directory"
        # YAML ``Any`` / ``True`` must not stay title-cased (that used to
        # make ``complete: Any`` filter as incomplete-only).
        assert resolve_filter_defaults({"complete": "Any"})["complete"] == "any"
        assert resolve_filter_defaults({"complete": "True"})["complete"] == "true"
        assert resolve_filter_defaults({"complete": "FALSE"})["complete"] == "false"

        reviewer, _, storage = _build_reviewer(
            index_vals=["a", "b", "c"],
            col_vals={"complete": False, "date": "2026-10-01"},
            extra={
                "display": {
                    "layout": "inline_list",
                    "filter_defaults": {
                        "complete": False,
                        "date": {
                            "after": "2026-09-01",
                            "before": "2026-11-01",
                        },
                        "_sort": "date:asc",
                        "_group": "directory",
                    },
                },
                "filters": [
                    {"field": "complete", "type": "boolean"},
                    {"field": "date", "type": "date_range"},
                ],
                "sort": [{"field": "date", "order": "asc"}],
            },
        )
        storage[("a", "complete")] = False
        storage[("a", "date")] = "2026-10-01"
        storage[("b", "complete")] = True
        storage[("b", "date")] = "2026-10-05"
        storage[("c", "complete")] = False
        storage[("c", "date")] = "2025-01-01"  # outside window
        assert reviewer.get_filter_state()["complete"] == "false"
        assert reviewer.get_filter_state()["_sort"] == "date:asc"
        assert reviewer.working_indices() == ["a"]
        reviewer.set_filter_state({"complete": "any"})
        # No date window; config sort keeps oldest-first order.
        assert reviewer.working_indices() == ["c", "a", "b"]
        # Capitalised ``Any`` (as written in YAML) must also mean no filter.
        reviewer.set_filter_state({"complete": "Any"})
        assert reviewer.working_indices() == ["c", "a", "b"]
        reviewer.clear_filters()
        assert reviewer.get_filter_state()["complete"] == "false"
        assert reviewer.working_indices() == ["a"]

    def test_filter_defaults_any_does_not_hide_complete(self):
        """``complete: Any`` must not shrink the working set like False."""
        reviewer, _, storage = _build_reviewer(
            index_vals=["a", "b"],
            col_vals={"complete": False, "date": "2026-10-01"},
            extra={
                "display": {
                    "layout": "inline_list",
                    "filter_defaults": {
                        "complete": "Any",
                        "date": {
                            "after": "2026-09-01",
                            "before": "2026-11-01",
                        },
                    },
                },
                "filters": [
                    {"field": "complete", "type": "boolean"},
                    {"field": "date", "type": "date_range"},
                ],
            },
        )
        storage[("a", "complete")] = False
        storage[("a", "date")] = "2026-10-01"
        storage[("b", "complete")] = True
        storage[("b", "date")] = "2026-10-05"
        assert reviewer.get_filter_state()["complete"] == "any"
        assert set(reviewer.working_indices()) == {"a", "b"}

    def test_checkbox_default_applies_when_missing(self):
        reviewer, _, storage = _build_reviewer(
            index_vals=["a"],
            col_vals={"title": "x"},
            review=[{"type": "Checkbox", "field": "complete"}],
        )
        storage[("a", "complete")] = None
        reviewer.set_index("a")
        assert reviewer.get_value("complete") is False
        assert reviewer._field_defaults.get("complete") is False

    def test_explicit_default_overrides_checkbox(self):
        reviewer, _, storage = _build_reviewer(
            index_vals=["a"],
            col_vals={"title": "x"},
            review=[
                {
                    "type": "Checkbox",
                    "field": "complete",
                    "default": True,
                }
            ],
        )
        storage[("a", "complete")] = None
        reviewer.set_index("a")
        assert reviewer.get_value("complete") is True

    def test_sort_orders_working_indices(self):
        reviewer, _, storage = _build_reviewer(
            index_vals=["a", "b", "c"],
            col_vals={"date": "2020-01-01"},
            extra={
                "display": {"layout": "inline_list"},
                "sort": [{"field": "date", "order": "desc"}],
            },
        )
        storage[("a", "date")] = "2024-01-01"
        storage[("b", "date")] = "2026-06-01"
        storage[("c", "date")] = "2025-03-01"
        assert reviewer.working_indices() == ["b", "c", "a"]

    def test_render_viewer_html_passes_rows_local(self):
        reviewer, data, storage = _build_reviewer(
            index_vals=["a"],
            col_vals={"title": "Alpha"},
            extra={"display": {"layout": "inline_list"}},
        )
        storage[("a", "title")] = "Alpha"
        captured = {}

        def _capture(view, kwargs=None, local=None):
            captured["local"] = local
            return "## list"

        data.view_to_value.side_effect = _capture
        html = reviewer.render_viewer_html({"type": "Markdown", "liquid": "{{ rows }}"})
        assert "rows" in (captured.get("local") or {})
        assert captured["local"]["rows"][0]["title"] == "Alpha"
        assert "list" in html or "viewer" in html


class TestInteractiveViewerHtml:
    """CIP-0011: typed PlotlyFigure / StaticImage under viewer:."""

    def test_has_plotly_viewer(self):
        reviewer, _, _ = _build_reviewer(
            viewer=[
                {"type": "Markdown", "liquid": "x"},
                {"type": "PlotlyFigure", "field": "fig"},
            ]
        )
        assert reviewer.has_plotly_viewer() is True

    def test_has_plotly_viewer_false_for_liquid_only(self):
        reviewer, _, _ = _build_reviewer(
            viewer=[{"type": "Markdown", "liquid": "x"}]
        )
        assert reviewer.has_plotly_viewer() is False

    def test_render_plotly_figure_from_field(self):
        fig = {
            "data": [
                {
                    "type": "scatter",
                    "x": [0, 1],
                    "y": [0, 1],
                    "customdata": [{"topic": "A"}, {"topic": "B"}],
                }
            ],
            "layout": {},
        }
        reviewer, _, storage = _build_reviewer(
            index_vals=["a"],
            col_vals={"topic_scatter_spec": fig, "selected_topic": "B"},
            viewer=[
                {
                    "type": "PlotlyFigure",
                    "field": "topic_scatter_spec",
                    "on": {
                        "click_point": [
                            {"set_field": "selected_topic", "from": "customdata.topic"}
                        ]
                    },
                    "highlight": {"from_field": "selected_topic"},
                }
            ],
        )
        storage[("a", "topic_scatter_spec")] = fig
        storage[("a", "selected_topic")] = "B"
        html = reviewer.render_viewer_html(
            reviewer.get_viewer_specs()[0], viewer_index=0
        )
        assert 'class="viewer viewer-plotly"' in html
        assert "plotly-spec" in html
        assert "selected_topic" in html
        # Liquid path must not be used for typed figures
        reviewer._data.view_to_value.assert_not_called()

    def test_render_plotly_figure_missing_field_still_emits_container(self):
        reviewer, _, _ = _build_reviewer(
            index_vals=["a"],
            viewer=[{"type": "PlotlyFigure", "field": "missing_fig"}],
        )
        html = reviewer.render_viewer_html(
            {"type": "PlotlyFigure", "field": "missing_fig"}, viewer_index=2
        )
        assert 'id="viewer-plotly-2"' in html
        assert "No figure data" in html or "plotly-spec" in html

    def test_render_static_image_from_field(self):
        reviewer, _, storage = _build_reviewer(
            index_vals=["a"],
            col_vals={"photo": "https://example.com/p.png"},
            viewer=[{"type": "StaticImage", "field": "photo"}],
        )
        storage[("a", "photo")] = "https://example.com/p.png"
        html = reviewer.render_viewer_html(
            {"type": "StaticImage", "field": "photo"}, viewer_index=1
        )
        assert 'class="viewer viewer-image"' in html
        assert "https://example.com/p.png" in html

    def test_render_static_image_from_liquid(self):
        reviewer, data, _ = _build_reviewer(
            index_vals=["a"],
            viewer=[{"type": "StaticImage", "liquid": "{{ photo }}"}],
        )
        data.view_to_value.return_value = "https://example.com/liq.png"
        html = reviewer.render_viewer_html(
            {"type": "StaticImage", "liquid": "{{ photo }}"}, viewer_index=0
        )
        assert "https://example.com/liq.png" in html
        data.view_to_value.assert_called()

    def test_plotly_field_and_highlight_errors_are_soft(self):
        reviewer, _, _ = _build_reviewer(
            index_vals=["a"],
            viewer=[
                {
                    "type": "PlotlyFigure",
                    "field": "fig",
                    "highlight": {"from_field": "selected_topic"},
                }
            ],
        )
        reviewer.get_value = MagicMock(side_effect=RuntimeError("boom"))
        html = reviewer.render_viewer_html(
            {
                "type": "PlotlyFigure",
                "field": "fig",
                "highlight": {"from_field": "selected_topic"},
            },
            viewer_index=0,
        )
        assert "viewer-plotly" in html

    def test_static_image_liquid_error_is_soft(self):
        reviewer, data, _ = _build_reviewer(
            index_vals=["a"],
            viewer=[{"type": "StaticImage", "liquid": "{{ photo }}"}],
        )
        data.view_to_value.side_effect = RuntimeError("liq fail")
        html = reviewer.render_viewer_html(
            {"type": "StaticImage", "liquid": "{{ photo }}"}, viewer_index=0
        )
        assert "viewer-image" in html or "No image" in html

    def test_static_image_field_error_is_soft(self):
        reviewer, _, _ = _build_reviewer(
            index_vals=["a"],
            viewer=[{"type": "StaticImage", "field": "photo"}],
        )
        reviewer.get_value = MagicMock(side_effect=RuntimeError("boom"))
        html = reviewer.render_viewer_html(
            {"type": "StaticImage", "field": "photo"}, viewer_index=0
        )
        assert "viewer-image" in html or "No image" in html
