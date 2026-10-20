"""CIP-0013 Phase A: raise CustomDataFrame (data.py) unit coverage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

import referia.assess.data as assess_data
from referia.assess.data import CustomDataFrame, automapping, empty


def _writable_frame(extra_cols=None):
    """Two-row writedata frame with optional extra columns."""
    cols = {"notes": ["a", "b"], "score": [1.0, 2.0]}
    if extra_cols:
        cols.update(extra_cols)
    cdf = CustomDataFrame(cols, colspecs={"writedata": list(cols.keys())})
    cdf.autocache = True
    cdf.set_index(cdf.index[0])
    return cdf


class TestAutomappingAndEmpty:
    def test_automapping_valid_and_invalid_names(self):
        mapping = automapping(["validName", "Job Title", "class", "_", "_private", "123abc"])
        assert mapping["validName"] == "validName"
        assert "Job Title" in mapping.values() or any(v == "Job Title" for v in mapping.values())
        assert mapping["_"] == "_"
        assert mapping["_private"] == "_private"
        # keyword gets Field suffix
        assert any(k.endswith("Field") or k == "classField" for k in mapping)
        # leading digits stripped from name key
        assert "123abc" in mapping.values()

    def test_empty_helper(self):
        assert empty(None) is True
        assert empty(np.nan) is True
        assert empty("") is True
        assert empty("x") is False
        assert empty(0) is False


class TestColumnAndElementOps:
    def test_get_shape(self):
        cdf = _writable_frame()
        assert cdf.get_shape() == (2, 2)

    def test_get_column_values(self):
        cdf = _writable_frame()
        cdf.set_column("notes")
        series = cdf.get_column_values()
        assert list(series) == ["a", "b"]
        cdf._column = None
        assert cdf.get_column_values() is None

    def test_get_value_underscore_and_none(self):
        cdf = _writable_frame()
        # "_" short-circuits before lookup
        with patch.object(cdf, "get_column", return_value="_"):
            assert cdf.get_value() is None
        with patch.object(cdf, "get_column", return_value=None):
            assert cdf.get_value() is None

    def test_get_set_value_by_element_list(self):
        cdf = CustomDataFrame(
            {"items": [["x", "y"], ["p"]]},
            colspecs={"writedata": ["items"]},
        )
        cdf.autocache = True
        cdf.set_index(cdf.index[0])
        cdf.set_column("items")
        assert cdf.get_value_by_element(0) == "x"
        assert cdf.get_value_by_element(5) is None
        cdf.set_value_by_element("z", 1)
        assert cdf.get_value()[1] == "z"
        # extend list when element past end
        cdf.set_value_by_element("tail", 3)
        assert cdf.get_value()[3] == "tail"

    def test_get_set_value_by_element_dict(self):
        cdf = CustomDataFrame(
            {"meta": [{"a": 1}, {"a": 2}]},
            colspecs={"writedata": ["meta"]},
        )
        cdf.autocache = True
        cdf.set_index(cdf.index[0])
        cdf.set_column("meta")
        assert cdf.get_value_by_element("a") == 1
        assert cdf.get_value_by_element("missing") is None
        cdf.set_value_by_element(9, "a")
        assert cdf.get_value()["a"] == 9

    def test_get_value_by_element_type_mismatch(self):
        cdf = _writable_frame()
        cdf.set_column("notes")
        assert cdf.get_value_by_element(0) is None  # str cell, int element
        assert cdf.get_value_by_element("k") is None  # str cell, str element for non-dict

    def test_set_value_by_element_converts_scalar(self):
        cdf = _writable_frame()
        cdf.set_column("notes")
        cdf.set_value_by_element("second", 1)
        assert isinstance(cdf.get_value(), list)
        assert cdf.get_value()[1] == "second"
        cdf.set_value("plain")
        cdf.set_value_by_element("v", "key")
        assert cdf.get_value()["key"] == "v"
        assert "original" in cdf.get_value()

    def test_drop_column(self):
        cdf = _writable_frame()
        cdf.isglobal = MagicMock(return_value=False)
        cdf.ismutable = MagicMock(return_value=True)
        cdf.drop_column("notes")
        assert "notes" not in cdf._d["writedata"].columns
        with pytest.raises(KeyError):
            cdf.drop_column("notes")

    def test_filter_rows(self):
        cdf = _writable_frame()
        cdf.isglobal = MagicMock(return_value=False)
        pdf = cdf.to_pandas()
        cond = pdf["score"] > 1.5
        cdf.filter_rows(cond)
        assert len(cdf._d["writedata"]) == 1

    def test_set_dtype(self):
        cdf = _writable_frame()
        cdf.set_dtype("score", "float64")
        assert str(cdf._d["writedata"]["score"].dtype) == "float64"

    def test_add_column_to_writedata(self):
        cdf = _writable_frame()
        # interface required for _strict_columns(group)
        cdf.interface = {"strict_columns": False}
        cdf.add_column("extra", data=pd.Series([10, 20], index=cdf.index))
        assert "extra" in cdf.columns

    def test_add_column_rejects_duplicate(self):
        cdf = _writable_frame()
        cdf.interface = {"strict_columns": False}
        with pytest.raises(ValueError, match="already exists"):
            cdf.add_column("notes")

    def test_add_column_rejects_when_not_mutable(self):
        cdf = CustomDataFrame({"a": [1]}, colspecs={"input": ["a"]})
        cdf.interface = {"strict_columns": False}
        # input-only frames are typically non-mutable for writes
        if not cdf.mutable:
            with pytest.raises(ValueError, match="not a mutable"):
                cdf.add_column("b")


class TestIndexAndSubseries:
    def test_set_index_runs_pre_and_post(self):
        cdf = _writable_frame()
        cdf._precompute = []
        cdf._postcompute = []
        calls = []

        def pre():
            calls.append("pre")

        def post():
            calls.append("post")

        cdf.compute_pre = pre
        cdf.compute_post = post
        first, second = list(cdf.index)
        cdf.set_index(first)
        calls.clear()
        cdf.set_index(second)
        assert "post" in calls
        assert "pre" in calls

    def test_set_index_same_value_skips_compute(self):
        cdf = _writable_frame()
        first = cdf.index[0]
        cdf.set_index(first)
        calls = []
        cdf.compute_pre = lambda: calls.append("pre")
        cdf.compute_post = lambda: calls.append("post")
        cdf.set_index(first)
        assert calls == []

    def test_set_index_propagates_pre_error(self):
        cdf = _writable_frame()
        first, second = list(cdf.index)
        cdf.set_index(first)

        def boom():
            raise RuntimeError("pre fail")

        cdf.compute_pre = boom
        cdf.compute_post = lambda: None
        with pytest.raises(RuntimeError, match="pre fail"):
            cdf.set_index(second)

    def test_get_index_auto_selects_first(self):
        cdf = CustomDataFrame(
            {"notes": ["a", "b"]},
            colspecs={"writedata": ["notes"]},
        )
        cdf.autocache = True
        cdf._index = None
        with patch.object(CustomDataFrame.__bases__[0], "get_index", return_value=None):
            with patch.object(cdf, "set_index") as mock_set:
                idx = cdf.get_index()
        assert idx == cdf.index[0]
        mock_set.assert_called_once_with(cdf.index[0])

    def test_append_row_concat(self):
        cdf = _writable_frame()
        cdf.compute_append = MagicMock()
        df = cdf._d["writedata"]
        new = cdf._append_row(df, index="new_row")
        assert "new_row" in new.index

    def test_series_from_value(self):
        cdf = _writable_frame()
        series = cdf._series_from_value(cdf.to_pandas(), value="const", name="c")
        assert list(series) == ["const", "const"]


class TestDialectStrictColumns:
    def test_dialect_default_unversioned_false(self):
        cdf = _writable_frame()
        cdf.interface = {}
        assert cdf._dialect_strict_columns_default() is False

    def test_dialect_default_v2_true(self):
        class Iface(dict):
            _referia_config_version = 2

        cdf = _writable_frame()
        cdf.interface = Iface()
        assert cdf._dialect_strict_columns_default() is True

    def test_resolve_strict_columns_precedence(self):
        cdf = _writable_frame()

        class Iface(dict):
            _referia_config_version = 1

        iface = Iface()
        cdf.interface = iface
        assert cdf._resolve_strict_columns(iface, strict_columns=True) is True
        iface["strict_columns"] = False
        assert cdf._resolve_strict_columns(iface) is False

    def test_strict_columns_group_defaults(self):
        cdf = _writable_frame()
        # Groups must exist so ``"strict_columns" in interface[group]`` is safe
        cdf.interface = {"cache": {}, "globals": {}, "scores": {}}
        assert cdf._strict_columns("cache") is True
        assert cdf._strict_columns("globals") is True
        assert cdf._strict_columns("scores") is False


class TestConcatPreservingDtypes:
    def test_none_or_empty_new_row(self):
        df = pd.DataFrame({"a": [1]}, index=[0])
        assert assess_data.concat_preserving_dtypes(df, None) is df
        empty = pd.DataFrame(columns=["a"])
        out = assess_data.concat_preserving_dtypes(df, empty)
        assert list(out.columns) == ["a"]

    def test_append_populated_row(self):
        df = pd.DataFrame({"a": [1.0]}, index=[0])
        new = pd.DataFrame({"a": [2.0]}, index=[1])
        out = assess_data.concat_preserving_dtypes(df, new)
        assert list(out["a"]) == [1.0, 2.0]

    def test_empty_base_uses_new_row_columns(self):
        df = pd.DataFrame(columns=["a", "b"])
        new = pd.DataFrame({"a": [1], "b": [2]}, index=[0])
        out = assess_data.concat_preserving_dtypes(df, new)
        assert list(out.columns) == ["a", "b"]


class TestAddColumnPaths:
    def test_add_column_rejects_immutable_object(self):
        # Only input cols + autocache off → mutable property is False
        cdf = CustomDataFrame({"a": [1]}, colspecs={"input": ["a"]})
        cdf.autocache = False
        cdf.interface = {"strict_columns": False}
        assert cdf.mutable is False
        with pytest.raises(ValueError, match="not a mutable"):
            cdf.add_column("b")

    def test_add_column_rejects_strict_without_autocache(self):
        cdf = _writable_frame()
        cdf.interface = {"strict_columns": False}
        cdf.autocache = False
        with pytest.raises(ValueError, match="strict_columns"):
            cdf.add_column("brand_new")

    def test_drop_column_immutable(self):
        cdf = _writable_frame()
        cdf.isglobal = MagicMock(return_value=False)
        cdf.ismutable = MagicMock(return_value=False)
        with pytest.raises(KeyError, match="read only"):
            cdf.drop_column("notes")

    def test_add_series_column(self):
        cdf = _writable_frame()
        # Ensure writeseries exists for series column ops
        cdf._writeseries = pd.DataFrame({"sel": ["x"]}, index=cdf.index[:1])
        cdf.add_series_column("new_series_col")
        assert "new_series_col" in cdf._writeseries.columns
        cdf.add_series_column("new_series_col")  # warning path, no raise

    def test_set_series_value_adds_column(self):
        cdf = _writable_frame()
        cdf._writeseries = pd.DataFrame(index=cdf.index[:1])
        cdf.ismutable = MagicMock(return_value=True)
        cdf.isseries = MagicMock(return_value=False)
        cdf._update_type = MagicMock()
        cdf.set_series_value("v", "scol")
        assert "scol" in cdf._writeseries.columns


class TestFinalizeAndSubseries:
    def test_finalize_df_selector_and_fields_value(self):
        cdf = _writable_frame()
        iface = {
            "index": "idx",
            "selector": "notes",
            "fields": [{"name": "constCol", "value": "X"}],
            "strict_columns": False,
        }
        # Parent finalize returns a plain pandas frame (set_index uses inplace)
        parent_df = pd.DataFrame(
            {"notes": ["a", "b"], "score": [1.0, 2.0], "idx": ["r0", "r1"]}
        )

        with patch.object(
            CustomDataFrame.__bases__[0],
            "_finalize_df",
            return_value=parent_df,
        ):
            out = cdf._finalize_df(parent_df, iface, strict_columns=False)
        assert cdf._selector == "notes"
        assert "constCol" in out.columns

    def test_finalize_df_strict_index_dict(self):
        cdf = _writable_frame()
        iface = {
            "index": {"name": "myIndex", "liquid": "{{notes}}"},
            "strict_columns": True,
        }
        parent_df = cdf.to_pandas().copy()
        parent_df["myIndex"] = ["i0", "i1"]
        with patch.object(
            CustomDataFrame.__bases__[0],
            "_finalize_df",
            side_effect=lambda df, interface, strict_columns=None: df,
        ):
            # After rewrite, index becomes string name
            cdf._finalize_df(parent_df, iface, strict_columns=True)
        assert iface["index"] == "myIndex"

    def test_check_or_set_subseries_adds_row(self):
        cdf = _writable_frame()
        cdf.types = {"series": ["writeseries"]}
        cdf._d["writeseries"] = pd.DataFrame(columns=["sel"])
        cdf.get_subseries = MagicMock(return_value=pd.Series(dtype=object))
        cdf.add_series_row = MagicMock()
        # Empty subindices → add_series_row
        cdf.get_subseries = MagicMock(return_value=[])
        cdf.check_or_set_subseries()
        cdf.add_series_row.assert_called()

    def test_reset_subindex_sets_first(self):
        cdf = _writable_frame()
        cdf.get_subindices = MagicMock(return_value=pd.Index(["s0", "s1"]))
        cdf.set_subindex = MagicMock()
        cdf._writeseries = pd.DataFrame({"x": [1]})
        cdf._selector = "x"
        cdf.reset_subindex()
        cdf.set_subindex.assert_called_with("s0")


class TestComputePrePostHooks:
    def test_compute_pre_calls_run(self):
        cdf = _writable_frame()
        cdf._precompute = [{"function": "noop"}]
        cdf.compute = MagicMock()
        cdf.compute_pre()
        cdf.compute.run.assert_called_once()
        kwargs = cdf.compute.run.call_args.kwargs
        assert kwargs["interface"]["compute"] == cdf._precompute

    def test_compute_post_calls_run(self):
        cdf = _writable_frame()
        cdf._postcompute = [{"function": "noop"}]
        cdf.compute = MagicMock()
        cdf.compute_post()
        cdf.compute.run.assert_called_once()

    def test_preprocess_delegates(self):
        cdf = _writable_frame()
        cdf.compute = MagicMock()
        cdf.preprocess()
        cdf.compute.preprocess.assert_called_once_with(data=cdf)
