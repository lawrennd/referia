"""Unit tests for CIP-0011 interactive viewer binding helpers."""

from referia.assess.viewer_bindings import (
    apply_highlight,
    click_point_actions,
    field_updates_from_click,
    highlight_binding,
    is_interactive_viewer_type,
    is_liquid_viewer,
    parse_figure_spec,
    resolve_path,
    viewer_entry_type,
    viewers_highlighting_field,
)


def test_default_type_is_markdown():
    assert viewer_entry_type({}) == "Markdown"
    assert viewer_entry_type(None) == "Markdown"
    assert is_liquid_viewer({"liquid": "hi"})
    assert not is_interactive_viewer_type({"liquid": "hi"})


def test_plotly_type_detected():
    spec = {"type": "PlotlyFigure", "field": "fig"}
    assert viewer_entry_type(spec) == "PlotlyFigure"
    assert is_interactive_viewer_type(spec)
    assert not is_liquid_viewer(spec)


def test_click_point_actions_normalise_list_and_dict():
    spec = {
        "on": {
            "click_point": [
                {"set_field": "selected_phrase", "from": "customdata.phrase"},
                {"set_field": "selected_topic", "from": "customdata.topic"},
            ]
        }
    }
    actions = click_point_actions(spec)
    assert len(actions) == 2
    assert actions[0]["set_field"] == "selected_phrase"
    single = click_point_actions(
        {"on": {"click_point": {"set_field": "a", "from": "customdata.x"}}}
    )
    assert single == [{"set_field": "a", "from": "customdata.x"}]


def test_resolve_path_and_field_updates():
    payload = {"customdata": {"phrase": "hello", "topic": 2}}
    assert resolve_path(payload, "customdata.phrase") == "hello"
    spec = {
        "on": {
            "click_point": [
                {"set_field": "selected_phrase", "from": "customdata.phrase"},
                {"set_field": "selected_topic", "from": "customdata.topic"},
                {"set_field": "missing", "from": "customdata.nope"},
            ]
        }
    }
    assert field_updates_from_click(spec, payload) == {
        "selected_phrase": "hello",
        "selected_topic": 2,
    }


def test_highlight_binding_and_viewers_highlighting_field():
    spec = {
        "type": "PlotlyFigure",
        "highlight": {"from_field": "selected_topic", "mode": "responsibility_ink"},
    }
    assert highlight_binding(spec) == {
        "from_field": "selected_topic",
        "mode": "responsibility_ink",
    }
    matched = viewers_highlighting_field(
        [spec, {"type": "Markdown", "liquid": "x"}], "selected_topic"
    )
    assert len(matched) == 1


def test_parse_figure_spec_and_apply_highlight():
    fig = {
        "data": [
            {
                "type": "scatter",
                "x": [0, 1],
                "y": [0, 1],
                "customdata": [{"topic": "A"}, {"topic": "B"}],
                "marker": {},
            }
        ],
        "layout": {},
    }
    assert parse_figure_spec(fig)["data"]
    assert parse_figure_spec('{"data": [], "layout": {}}') == {
        "data": [],
        "layout": {},
    }
    highlighted = apply_highlight(fig, selected="B", mode="default")
    assert highlighted["data"][0]["marker"]["opacity"] == [0.25, 1.0]
