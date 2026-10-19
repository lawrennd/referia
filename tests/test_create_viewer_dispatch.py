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
