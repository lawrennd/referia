"""Tests for CIP-0011 Jupyter PlotlyFigureViewer / StaticImageViewer."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, PropertyMock, patch

import ipywidgets as ipyw
import pytest


def _plotly_modules(figure_widget, traces=None):
    """Install fake plotly modules; FigureWidget returns a real Widget."""
    mock_go = MagicMock()
    if traces is None:
        mock_trace = MagicMock()
        traces = [mock_trace]
    figure_widget.data = traces
    mock_go.Figure.return_value = MagicMock()
    mock_go.FigureWidget.return_value = figure_widget
    plotly_pkg = MagicMock()
    plotly_pkg.graph_objects = mock_go
    return mock_go, traces, {
        "plotly": plotly_pkg,
        "plotly.graph_objects": mock_go,
    }


@pytest.fixture
def parent():
    p = MagicMock()
    values = {
        "topic_scatter_spec": {
            "data": [
                {
                    "type": "scatter",
                    "x": [0, 1],
                    "y": [0, 1],
                    "customdata": [{"topic": "A"}, {"topic": "B"}],
                }
            ],
            "layout": {},
        },
        "selected_topic": "B",
        "photo": "https://example.com/a.png",
    }
    current = {"col": None}

    def set_column(c):
        current["col"] = c

    def get_value():
        return values.get(current["col"])

    def set_value(v):
        values[current["col"]] = v

    p.set_column.side_effect = set_column
    p.get_value.side_effect = get_value
    p.set_value.side_effect = set_value
    p._widgets = MagicMock()
    p._data = MagicMock()
    p._data.viewer_to_value.return_value = "https://example.com/liq.png"
    return p


class TestStaticImageViewer:
    def test_refresh_from_field(self, parent):
        from referia.util.widgets import StaticImageViewer

        w = StaticImageViewer(
            field_name="_viewer_label0",
            column_name="_viewer_label0",
            parent=parent,
            viewer_spec={"type": "StaticImage", "field": "photo"},
        )
        assert "https://example.com/a.png" in w.widget.value
        assert w.private is True
        assert w.to_markdown() == ""
        assert w.name == "_viewer_label0"
        assert StaticImageViewer._default_widget() is ipyw.HTML
        assert w.get_value() == w.widget.value
        w.set_value("<em>No image</em>")
        assert w.widget.value == "<em>No image</em>"
        assert w.has_trait("value") is False

    def test_refresh_from_liquid(self, parent):
        from referia.util.widgets import StaticImageViewer

        w = StaticImageViewer(
            field_name="_viewer_label0",
            column_name="_viewer_label0",
            parent=parent,
            viewer_spec={"type": "StaticImage", "liquid": "{{ photo }}"},
        )
        assert "https://example.com/liq.png" in w.widget.value

    def test_refresh_empty_when_missing(self, parent):
        from referia.util.widgets import StaticImageViewer

        w = StaticImageViewer(
            field_name="_viewer_label0",
            column_name="_viewer_label0",
            parent=parent,
            viewer_spec={"type": "StaticImage", "field": "missing"},
        )
        assert "No image" in w.widget.value

    def test_field_none_renders_empty(self, parent):
        from referia.util.widgets import StaticImageViewer

        parent.get_value.side_effect = lambda: None
        w = StaticImageViewer(
            field_name="_v",
            parent=parent,
            viewer_spec={"type": "StaticImage", "field": "photo"},
        )
        assert "No image" in w.widget.value

    def test_field_read_exception_is_soft(self, parent):
        from referia.util.widgets import StaticImageViewer

        parent.set_column.side_effect = RuntimeError("col fail")
        w = StaticImageViewer(
            field_name="_v",
            parent=parent,
            viewer_spec={"type": "StaticImage", "field": "photo"},
        )
        assert "No image" in w.widget.value

    def test_liquid_exception_is_soft(self, parent):
        from referia.util.widgets import StaticImageViewer

        parent._data.viewer_to_value.side_effect = RuntimeError("liq fail")
        w = StaticImageViewer(
            field_name="_v",
            parent=parent,
            viewer_spec={"type": "StaticImage", "liquid": "{{ photo }}"},
        )
        assert "No image" in w.widget.value

    def test_get_set_value_exception_paths(self, parent):
        from referia.util.widgets import StaticImageViewer

        w = StaticImageViewer(
            field_name="_v",
            parent=parent,
            viewer_spec={"type": "StaticImage", "field": "photo"},
        )
        with patch.object(
            type(w.widget), "value", new_callable=PropertyMock
        ) as prop:
            prop.side_effect = RuntimeError("read fail")
            assert w.get_value() is None
        with patch.object(
            type(w.widget), "value", new_callable=PropertyMock
        ) as prop:
            prop.side_effect = RuntimeError("write fail")
            w.set_value("x")  # must not raise


class TestPlotlyFigureViewer:
    def test_import_error_fallback(self, parent):
        from referia.util.widgets import PlotlyFigureViewer

        real_import = __import__

        def selective_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "plotly" or name.startswith("plotly."):
                raise ImportError("forced")
            return real_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=selective_import):
            w = PlotlyFigureViewer(
                field_name="_viewer_label0",
                column_name="_viewer_label0",
                parent=parent,
                viewer_spec={
                    "type": "PlotlyFigure",
                    "field": "topic_scatter_spec",
                    "highlight": {"from_field": "selected_topic"},
                },
            )
        assert w.private is True
        assert w.name == "_viewer_label0"
        assert w.to_markdown() == ""
        assert PlotlyFigureViewer._default_widget() is ipyw.VBox
        assert w.get_value() is None
        w.set_value("ignored")
        assert w.has_trait("value") is False
        html = w.widget.children[0].value
        assert "Plotly is not installed" in html
        assert w._figure_widget is None

    def test_field_and_highlight_read_errors_are_soft(self, parent):
        from referia.util.widgets import PlotlyFigureViewer

        parent.set_column.side_effect = RuntimeError("boom")
        mock_fw = ipyw.HTML(value="fig")
        mock_go, traces, modules = _plotly_modules(mock_fw)

        with patch.dict(sys.modules, modules):
            w = PlotlyFigureViewer(
                field_name="_v",
                parent=parent,
                viewer_spec={
                    "type": "PlotlyFigure",
                    "field": "topic_scatter_spec",
                    "highlight": {"from_field": "selected_topic"},
                },
            )
        assert w._figure_widget is mock_fw
        mock_go.Figure.assert_called()

    def test_refresh_with_mocked_plotly_and_click(self, parent):
        from referia.util.widgets import PlotlyFigureViewer

        mock_fw = ipyw.HTML(value="fig")
        mock_go, traces, modules = _plotly_modules(mock_fw)
        mock_trace = traces[0]

        with patch.dict(sys.modules, modules):
            w = PlotlyFigureViewer(
                field_name="_viewer_label0",
                column_name="_viewer_label0",
                parent=parent,
                viewer_spec={
                    "type": "PlotlyFigure",
                    "field": "topic_scatter_spec",
                    "highlight": {
                        "from_field": "selected_topic",
                        "mode": "default",
                    },
                    "on": {
                        "click_point": [
                            {
                                "set_field": "selected_topic",
                                "from": "customdata.topic",
                            }
                        ]
                    },
                },
            )

        mock_go.FigureWidget.assert_called()
        mock_trace.on_click.assert_called()
        assert list(w.widget.children) == [mock_fw]

        callback = mock_trace.on_click.call_args[0][0]
        points = MagicMock()
        points.point_inds = [1]
        points.xs = [1]
        points.ys = [1]
        trace = MagicMock()
        trace.customdata = [{"topic": "A"}, {"topic": "B"}]
        callback(trace, points, None)
        assert parent.set_value.call_args[0][0] == "B"
        parent._widgets.refresh.assert_called()

    def test_click_with_empty_points_is_noop(self, parent):
        from referia.util.widgets import PlotlyFigureViewer

        mock_fw = ipyw.HTML(value="fig")
        mock_go, traces, modules = _plotly_modules(mock_fw)
        mock_trace = traces[0]

        with patch.dict(sys.modules, modules):
            w = PlotlyFigureViewer(
                field_name="_viewer_label0",
                column_name="_viewer_label0",
                parent=parent,
                viewer_spec={"type": "PlotlyFigure", "field": "topic_scatter_spec"},
            )
        callback = mock_trace.on_click.call_args[0][0]
        points = MagicMock()
        points.point_inds = []
        parent.set_value.reset_mock()
        callback(MagicMock(), points, None)
        parent.set_value.assert_not_called()
        assert w._figure_widget is mock_fw
        assert mock_go.FigureWidget.called

    def test_click_customdata_index_error_falls_back(self, parent):
        from referia.util.widgets import PlotlyFigureViewer

        mock_fw = ipyw.HTML(value="fig")
        _, traces, modules = _plotly_modules(mock_fw)
        mock_trace = traces[0]

        with patch.dict(sys.modules, modules):
            PlotlyFigureViewer(
                field_name="_v",
                parent=parent,
                viewer_spec={
                    "type": "PlotlyFigure",
                    "field": "topic_scatter_spec",
                    "on": {
                        "click_point": [
                            {"set_field": "selected_topic", "from": "customdata"}
                        ]
                    },
                },
            )
        callback = mock_trace.on_click.call_args[0][0]
        points = MagicMock()
        points.point_inds = [0]
        points.xs = [0]
        points.ys = [0]
        # Indexing customdata raises → whole customdata used as value
        broken = MagicMock()
        broken.__getitem__ = MagicMock(side_effect=IndexError("oob"))
        trace = MagicMock()
        trace.customdata = broken
        parent.set_value.reset_mock()
        callback(trace, points, None)
        parent.set_value.assert_called()
        assert parent.set_value.call_args[0][0] is broken

    def test_click_with_no_parent_is_noop(self):
        from referia.util.widgets import PlotlyFigureViewer

        mock_fw = ipyw.HTML(value="fig")
        _, traces, modules = _plotly_modules(mock_fw)
        mock_trace = traces[0]

        with patch.dict(sys.modules, modules):
            PlotlyFigureViewer(
                field_name="_v",
                parent=None,
                viewer_spec={
                    "type": "PlotlyFigure",
                    "field": "topic_scatter_spec",
                    "on": {
                        "click_point": [
                            {"set_field": "selected_topic", "from": "pointNumber"}
                        ]
                    },
                },
            )
        callback = mock_trace.on_click.call_args[0][0]
        points = MagicMock()
        points.point_inds = [0]
        points.xs = []
        points.ys = []
        # No parent → early return after computing updates
        callback(MagicMock(customdata=None), points, None)

    def test_click_set_value_and_refresh_errors_are_soft(self, parent):
        from referia.util.widgets import PlotlyFigureViewer

        mock_fw = ipyw.HTML(value="fig")
        _, traces, modules = _plotly_modules(mock_fw)
        mock_trace = traces[0]

        with patch.dict(sys.modules, modules):
            PlotlyFigureViewer(
                field_name="_v",
                parent=parent,
                viewer_spec={
                    "type": "PlotlyFigure",
                    "field": "topic_scatter_spec",
                    "on": {
                        "click_point": [
                            {
                                "set_field": "selected_topic",
                                "from": "customdata.topic",
                            }
                        ]
                    },
                },
            )
        callback = mock_trace.on_click.call_args[0][0]
        parent.set_value.side_effect = RuntimeError("write fail")
        parent._widgets.refresh.side_effect = RuntimeError("refresh fail")
        points = MagicMock()
        points.point_inds = [0]
        points.xs = [0]
        points.ys = [0]
        trace = MagicMock()
        trace.customdata = [{"topic": "A"}]
        callback(trace, points, None)  # must not raise

    def test_on_click_bind_failure_is_soft(self, parent):
        from referia.util.widgets import PlotlyFigureViewer

        mock_fw = ipyw.HTML(value="fig")
        bad_trace = MagicMock()
        bad_trace.on_click.side_effect = RuntimeError("no click")
        _, _, modules = _plotly_modules(mock_fw, traces=[bad_trace])

        with patch.dict(sys.modules, modules):
            w = PlotlyFigureViewer(
                field_name="_v",
                parent=parent,
                viewer_spec={"type": "PlotlyFigure", "field": "topic_scatter_spec"},
            )
        assert w._figure_widget is mock_fw
        bad_trace.on_click.assert_called()
