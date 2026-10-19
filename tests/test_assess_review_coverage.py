"""CIP-0013 Phase B: raise Reviewer (review.py) unit coverage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from referia.assess.data import CustomDataFrame
from referia.assess.review import Reviewer


def _bare_reviewer(**overrides):
    """Minimal Reviewer-like object with real methods bound."""
    r = MagicMock(spec=Reviewer)
    r._interface = {
        "viewer": {"type": "Markdown", "value": "viewer text"},
        "review": [{"type": "Checkbox", "field": "flag"}],
        "modified_suffix": "modified",
        "created_suffix": "created",
        "scored": True,
    }
    r._data = MagicMock()
    r._widgets = MagicMock()
    r._system = MagicMock()
    r.get_index = MagicMock(return_value=0)
    r.get_indices = MagicMock(return_value=[0, 1])
    r.set_index = MagicMock()
    r.get_selector = MagicMock(return_value=None)
    r.get_subindex = MagicMock(return_value=None)
    r.set_selector = MagicMock()
    r.set_subindex = MagicMock()
    r.populate_display = MagicMock()
    r.compute_onchange = MagicMock()
    r.get_column = MagicMock(return_value="notes")
    r.set_column = MagicMock()
    r.set_value = MagicMock()
    for k, v in overrides.items():
        setattr(r, k, v)
    # Bind real implementations
    r.template_to_value = lambda template: Reviewer.template_to_value(r, template)
    r.create_document = lambda document, summary=False: Reviewer.create_document(
        r, document, summary=summary
    )
    r.load_flows = lambda reload=False: Reviewer.load_flows(r, reload=reload)
    r.value_updated = lambda: Reviewer.value_updated(r)
    r._update_widget_visibility = lambda widgets: Reviewer._update_widget_visibility(
        r, widgets
    )
    return r


class TestTemplateToValue:
    def test_use_viewer(self):
        r = _bare_reviewer()
        r._data.view_to_value = MagicMock(return_value="VIEW")
        out = r.template_to_value({"use": "viewer"})
        assert "VIEW" in out

    def test_use_review_markdown(self):
        r = _bare_reviewer()
        r._widgets.to_markdown = MagicMock(return_value="## widgets")
        assert r.template_to_value({"use": "review"}) == "## widgets"
        assert r.template_to_value({"use": "scorer"}) == "## widgets"

    def test_plain_view_template(self):
        r = _bare_reviewer()
        r._data.view_to_value = MagicMock(return_value="plain")
        assert r.template_to_value({"display": "notes"}) == "plain"


class TestCreateDocument:
    def test_body_header_footer_assembly(self):
        r = _bare_reviewer()
        r.template_to_value = MagicMock(return_value="BODY")
        doc = {
            "type": "markdown",
            "header": "# Title",
            "body": {"use": "review"},
            "footer": "end",
            "filename": "out.md",
        }
        r.create_document(doc)
        r._system.create_document.assert_called_once()
        _, kwargs = r._system.create_document.call_args
        assert kwargs["content"].startswith("# Title")
        assert "BODY" in kwargs["content"]
        assert "end" in kwargs["content"]
        assert "header" not in kwargs
        assert "footer" not in kwargs

    def test_summary_aggregates_indices(self):
        r = _bare_reviewer()
        r.template_to_value = MagicMock(return_value="chunk")
        doc = {"type": "markdown", "body": {"use": "viewer"}, "filename": "s.md"}
        r.create_document(doc, summary=True)
        assert r.template_to_value.call_count == 2
        _, kwargs = r._system.create_document.call_args
        assert "chunk" in kwargs["content"]


class TestLoadFlows:
    def test_reload_restores_index(self):
        r = _bare_reviewer()
        r._data.load_flows = MagicMock()
        r.load_flows(reload=True)
        r._data.load_flows.assert_called_once()
        r.set_index.assert_called()
        r.populate_display.assert_called_once()

    def test_no_reload_skips_restore(self):
        r = _bare_reviewer()
        r._data.load_flows = MagicMock()
        r.load_flows(reload=False)
        r.set_index.assert_not_called()
        r.populate_display.assert_called_once()


class TestValueUpdated:
    def test_sets_modified_and_created_timestamps(self):
        r = _bare_reviewer()
        r.get_column = MagicMock(return_value="notes")
        r._data.set_dtype = MagicMock()
        r._data.get_value_column = MagicMock(return_value=None)
        r.set_column = MagicMock()
        r.set_value = MagicMock()
        with patch("referia.assess.review.data.empty", return_value=True):
            r.value_updated()
        r.compute_onchange.assert_called_once()
        assert r.set_value.call_count >= 2
        r._data.set_dtype.assert_any_call("notes_modified", "datetime64[ns]")
        r._data.set_dtype.assert_any_call("notes_created", "datetime64[ns]")

    def test_combinator_updates(self):
        r = _bare_reviewer()
        r._interface = {
            "modified_suffix": "modified",
            "created_suffix": "created",
            "combinator": [{"field": "combo", "liquid": "{{notes}}"}],
        }
        r.get_column = MagicMock(return_value="notes")
        r._data.set_dtype = MagicMock()
        r._data.get_value_column = MagicMock(return_value=pd.Timestamp("2020-01-01"))
        r._data.viewer_to_value = MagicMock(return_value="combined")
        r.set_column = MagicMock()
        r.set_value = MagicMock()
        with patch("referia.assess.review.data.empty", return_value=False):
            r.value_updated()
        written = [c.args[0] for c in r.set_value.call_args_list]
        assert "combined" in written


class TestWidgetVisibilityHelper:
    def test_string_condition_hides_when_false(self):
        data = CustomDataFrame(
            {"flag": [False, True], "notes": ["a", "b"]},
            colspecs={"writedata": ["flag", "notes"]},
        )
        data.autocache = True
        data.set_index(data.index[0])

        r = _bare_reviewer(_data=data)
        r.get_index = MagicMock(return_value=data.index[0])

        # Avoid real WidgetCluster (ipywidgets) — isinstance check only
        cluster = MagicMock()
        cluster._widget_list = ["flag_w"]
        widget = MagicMock()
        widget._visible_if_condition = "flag"
        widget.widget.layout.display = ""
        widget.widget.layout.height = ""
        widget.widget.layout.margin = ""
        widget.widget.layout.padding = ""
        cluster._widget_dict = {"flag_w": widget}

        with patch("referia.assess.review.WidgetCluster", type(None)):
            # MagicMock is not WidgetCluster; entry is str → widget path
            r._update_widget_visibility(cluster)
        assert widget.widget.layout.display == "none"

    def test_equals_and_not_conditions(self):
        data = CustomDataFrame(
            {"flag": [False], "notes": ["hello"]},
            colspecs={"writedata": ["flag", "notes"]},
        )
        data.autocache = True
        data.set_index(data.index[0])

        r = _bare_reviewer(_data=data)
        r.get_index = MagicMock(return_value=data.index[0])

        cluster = MagicMock()
        w_eq = MagicMock()
        w_eq._visible_if_condition = {"field": "notes", "equals": "hello"}
        w_eq.widget.layout.display = "none"
        w_eq.widget.layout.height = "0px"
        w_eq.widget.layout.margin = "0px"
        w_eq.widget.layout.padding = "0px"

        w_not = MagicMock()
        w_not._visible_if_condition = {"field": "flag", "not": True}
        w_not.widget.layout.display = "none"
        w_not.widget.layout.height = "0px"
        w_not.widget.layout.margin = "0px"
        w_not.widget.layout.padding = "0px"

        cluster._widget_list = ["eq", "nt"]
        cluster._widget_dict = {"eq": w_eq, "nt": w_not}
        r._update_widget_visibility(cluster)
        assert w_eq.widget.layout.display == ""
        assert w_not.widget.layout.display == ""
