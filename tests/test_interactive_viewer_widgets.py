"""Tests for CIP-0011 Jupyter PlotlyFigureViewer / StaticImageViewer."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import ipywidgets as ipyw
import pytest


def _plotly_modules(figure_widget):
    """Install fake plotly modules; FigureWidget returns a real Widget."""
    mock_go = MagicMock()
    mock_trace = MagicMock()
    figure_widget.data = [mock_trace]
    mock_go.Figure.return_value = MagicMock()
    mock_go.FigureWidget.return_value = figure_widget
    plotly_pkg = MagicMock()
    plotly_pkg.graph_objects = mock_go
    return mock_go, mock_trace, {
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
        html = w.widget.children[0].value
        assert "Plotly is not installed" in html

    def test_refresh_with_mocked_plotly_and_click(self, parent):
        from referia.util.widgets import PlotlyFigureViewer

        mock_fw = ipyw.HTML(value="fig")
        mock_go, mock_trace, modules = _plotly_modules(mock_fw)

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
        mock_go, mock_trace, modules = _plotly_modules(mock_fw)

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
