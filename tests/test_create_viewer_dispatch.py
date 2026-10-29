"""CIP-0011: Reviewer._create_viewer type dispatch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def reviewer_stub():
    from referia.assess.review import Reviewer

    r = Reviewer.__new__(Reviewer)
    r._widgets = MagicMock()
    return r


def _assert_create_viewer_dispatch(module_path: str, reviewer_stub):
    from referia.util.widgets import Markdown, PlotlyFigureViewer, StaticImageViewer

    views = [
        {"liquid": "## Doc"},
        {
            "type": "PlotlyFigure",
            "field": "fig",
            "on": {"click_point": [{"set_field": "t", "from": "customdata.t"}]},
        },
        {"type": "StaticImage", "field": "photo"},
        "plain-string-view",
    ]

    captured = {}

    def fake_add(**kwargs):
        captured.update(kwargs)

    with patch(f"{module_path}.WidgetCluster") as WC, patch(
        f"{module_path}.PlotlyFigureViewer"
    ) as PF, patch(
        f"{module_path}.StaticImageViewer"
    ) as SI, patch(
        f"{module_path}.Markdown"
    ) as MD:
        cluster = MagicMock()
        cluster.add.side_effect = fake_add
        WC.return_value = cluster
        PF.side_effect = lambda **kw: MagicMock(spec=PlotlyFigureViewer)
        SI.side_effect = lambda **kw: MagicMock(spec=StaticImageViewer)
        MD.side_effect = lambda **kw: MagicMock(spec=Markdown)

        out = reviewer_stub._create_viewer(views)
        assert out is cluster
        assert "_viewer_label0" in captured
        assert "_viewer_label1" in captured
        assert "_viewer_label2" in captured
        assert "_viewer_label3" in captured
        PF.assert_called_once()
        SI.assert_called_once()
        assert MD.call_count == 2
        md_kwargs = MD.call_args_list[0].kwargs
        assert "on" not in md_kwargs
        assert "highlight" not in md_kwargs


def test_create_viewer_dispatches_plotly_static_and_markdown(reviewer_stub):
    _assert_create_viewer_dispatch("referia.assess.review", reviewer_stub)


def test_create_viewer_dispatches_in_review_new():
    from referia.assess.review_new import Reviewer

    r = Reviewer.__new__(Reviewer)
    r._widgets = MagicMock()
    _assert_create_viewer_dispatch("referia.assess.review_new", r)


def test_create_viewer_binds_visible_if(reviewer_stub):
    from referia.assess.review import Reviewer

    reviewer_stub.get_index = lambda: "a"
    reviewer_stub._data = MagicMock()
    reviewer_stub._data.at.__getitem__ = lambda _self, key: False

    captured = {}

    def fake_add(**kwargs):
        captured.update(kwargs)

    with patch("referia.assess.review.WidgetCluster") as WC, patch(
        "referia.assess.review.Markdown"
    ) as MD:
        cluster = MagicMock()
        cluster.add.side_effect = fake_add
        WC.return_value = cluster
        widget = MagicMock()
        MD.return_value = widget

        Reviewer._create_viewer(
            reviewer_stub,
            [{"liquid": "## Ch8", "visible_if": "ch8Present"}],
        )

    assert "visible_if" not in MD.call_args.kwargs
    assert widget._visible_if_condition == "ch8Present"
    inner = widget.widget
    assert inner.layout.display == "none"


def test_create_viewer_binds_visible_if_in_review_new():
    from referia.assess.review_new import Reviewer

    r = Reviewer.__new__(Reviewer)
    r._widgets = MagicMock()
    r.get_index = lambda: "a"
    r._data = MagicMock()
    r._data.at.__getitem__ = lambda _self, key: False

    widget = MagicMock()
    with patch("referia.assess.review_new.WidgetCluster") as WC, patch(
        "referia.assess.review_new.Markdown"
    ) as MD:
        cluster = MagicMock()
        WC.return_value = cluster
        MD.return_value = widget
        Reviewer._create_viewer(
            r, [{"liquid": "## Ch8", "visible_if": "ch8Present"}]
        )

    assert "visible_if" not in MD.call_args.kwargs
    assert widget._visible_if_condition == "ch8Present"
    assert widget.widget.layout.display == "none"


def test_create_viewer_binds_visible_if_on_plotly_image_and_section(reviewer_stub):
    from referia.assess.review import Reviewer

    reviewer_stub.get_index = lambda: "a"
    reviewer_stub._data = MagicMock()
    reviewer_stub._data.at.__getitem__ = lambda _self, key: False

    heading = MagicMock()
    plotly = MagicMock()
    image = MagicMock()
    md_calls = []

    def fake_markdown(**kwargs):
        widget = MagicMock()
        md_calls.append((kwargs, widget))
        if kwargs.get("liquid") == "### Chapter 8":
            return heading
        return widget

    with patch("referia.assess.review.WidgetCluster") as WC, patch(
        "referia.assess.review.PlotlyFigureViewer"
    ) as PF, patch(
        "referia.assess.review.StaticImageViewer"
    ) as SI, patch(
        "referia.assess.review.Markdown", side_effect=fake_markdown
    ):
        cluster = MagicMock()
        WC.return_value = cluster
        PF.return_value = plotly
        SI.return_value = image
        Reviewer._create_viewer(
            reviewer_stub,
            [
                {
                    "type": "Section",
                    "title": "Chapter 8",
                    "visible_if": "ch8Present",
                    "entries": [{"liquid": "notes"}],
                },
                {
                    "type": "PlotlyFigure",
                    "field": "fig",
                    "visible_if": "ch8Present",
                },
                {
                    "type": "StaticImage",
                    "field": "photo",
                    "visible_if": "ch8Present",
                },
            ],
        )

    assert PF.call_args.kwargs.get("visible_if") is None
    assert SI.call_args.kwargs.get("visible_if") is None
    assert heading._visible_if_condition == "ch8Present"
    assert heading.widget.layout.display == "none"
    assert plotly._visible_if_condition == "ch8Present"
    assert image._visible_if_condition == "ch8Present"
    assert plotly.widget.layout.display == "none"
    assert image.widget.layout.display == "none"


def test_apply_jupyter_visible_if_none_and_refresh():
    from referia.assess.review import _apply_jupyter_visible_if

    class Bare:
        pass

    reviewer = MagicMock()
    reviewer.get_index.return_value = "a"
    reviewer._data.at.__getitem__ = lambda _self, key: False

    untouched = Bare()
    _apply_jupyter_visible_if(untouched, None, reviewer)
    assert not hasattr(untouched, "_visible_if_condition")

    missing_layout = Bare()
    missing_layout.widget = Bare()
    _apply_jupyter_visible_if(missing_layout, "ch8Present", reviewer)
    assert missing_layout._visible_if_condition == "ch8Present"

    widget = MagicMock()
    widget.widget.layout.display = ""
    widget.widget.layout.height = ""
    widget.widget.layout.margin = ""
    widget.widget.layout.padding = ""
    _apply_jupyter_visible_if(widget, "ch8Present", reviewer)
    assert widget.widget.layout.display == "none"

    reviewer._data.at.__getitem__ = lambda _self, key: True
    _apply_jupyter_visible_if(widget, widget._visible_if_condition, reviewer)
    assert widget.widget.layout.display == ""
