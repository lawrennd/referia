"""Unit tests for CIP-0011 interactive viewer binding helpers."""

from referia.assess.viewer_bindings import (
    apply_highlight,
    apply_plotly_size,
    click_point_actions,
    field_updates_from_click,
    figure_source_binding,
    highlight_binding,
    is_interactive_viewer_type,
    is_liquid_viewer,
    is_viewer_chrome_type,
    normalize_viewer_entry,
    parse_figure_spec,
    plotly_size_options,
    resolve_figure_payload,
    resolve_path,
    viewer_entry_type,
    viewers_highlighting_field,
    viewers_watching_field,
)


def test_default_type_is_markdown():
    assert viewer_entry_type({}) == "Markdown"
    assert viewer_entry_type(None) == "Markdown"
    assert viewer_entry_type("not-a-mapping") == "Markdown"
    assert viewer_entry_type({"type": ""}) == "Markdown"
    assert is_liquid_viewer({"liquid": "hi"})
    assert not is_interactive_viewer_type({"liquid": "hi"})


def test_plotly_and_static_types_detected():
    assert viewer_entry_type({"type": "PlotlyFigure"}) == "PlotlyFigure"
    assert viewer_entry_type({"type": "StaticImage"}) == "StaticImage"
    assert is_interactive_viewer_type({"type": "PlotlyFigure", "field": "fig"})
    assert is_interactive_viewer_type({"type": "StaticImage"})
    assert not is_liquid_viewer({"type": "PlotlyFigure"})


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


def test_click_point_actions_skips_invalid():
    assert click_point_actions(None) == []
    assert click_point_actions({}) == []
    assert click_point_actions({"on": "bad"}) == []
    assert click_point_actions({"on": {}}) == []
    assert click_point_actions({"on": {"click_point": "bad"}}) == []
    assert click_point_actions(
        {"on": {"click_point": [{"set_field": "x"}, "skip", {"from": "a"}]}}
    ) == []
    assert click_point_actions(
        {"on": {"click_point": [{"set_field": "x", "from": ""}]}}
    ) == []


def test_normalize_viewer_entry_yaml_on_boolean_key():
    """PyYAML 1.1 turns bare ``on:`` into boolean ``True`` keys."""
    raw = {
        "type": "PlotlyFigure",
        True: {
            "click_point": [{"set_field": "t", "from": "customdata.topic"}],
        },
        "highlight": {"from_field": "t"},
    }
    fixed = normalize_viewer_entry(raw)
    assert "on" in fixed and True not in fixed
    assert click_point_actions(raw) == [
        {"set_field": "t", "from": "customdata.topic"}
    ]
    assert highlight_binding(raw)["from_field"] == "t"


def test_plotly_size_options_and_apply():
    assert plotly_size_options({}) == {
        "mode": "figure",
        "observe": True,
        "aspect_ratio": None,
    }
    assert plotly_size_options({"size": "container"}) == {
        "mode": "container",
        "observe": True,
        "aspect_ratio": "4/3",
    }
    assert plotly_size_options(
        {"size": {"mode": "container", "observe": False, "aspect_ratio": "16/9"}}
    ) == {"mode": "container", "observe": False, "aspect_ratio": "16/9"}
    assert plotly_size_options({"size": {"fit": "figure"}})["mode"] == "figure"

    fig = {"data": [], "layout": {"height": 420, "width": 800, "title": "t"}}
    kept = apply_plotly_size(fig, mode="figure")
    assert kept["layout"]["height"] == 420
    filled = apply_plotly_size(fig, mode="container")
    assert filled["layout"].get("autosize") is True
    assert "height" not in filled["layout"]
    assert "width" not in filled["layout"]
    assert apply_plotly_size(None, mode="container") is None


def test_resolve_path_mapping_sequence_and_attr():
    payload = {"customdata": {"phrase": "hello", "topic": 2}}
    assert resolve_path(payload, "customdata.phrase") == "hello"
    assert resolve_path(None, "a") is None
    assert resolve_path(payload, "") is None
    assert resolve_path(payload, None) is None
    assert resolve_path({"items": [{"topic": "A"}, {"topic": "B"}]}, "items.1.topic") == "B"
    assert resolve_path({"items": [{"topic": "A"}]}, "items.bad") is None
    assert resolve_path({"items": [{"topic": "A"}]}, "items.5.topic") is None
    assert resolve_path({"items": [{"topic": "A"}]}, "items.-1.topic") is None

    class Obj:
        def __init__(self):
            self.x = 9

    assert resolve_path(Obj(), "x") == 9
    assert resolve_path(Obj(), "missing") is None
    assert resolve_path({"a": None}, "a.b") is None


def test_field_updates_from_click():
    payload = {"customdata": {"phrase": "hello", "topic": 2}}
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
    assert field_updates_from_click(spec, None) == {}
    assert field_updates_from_click(spec, "bad") == {}


def test_highlight_binding_and_viewers_highlighting_field():
    spec = {
        "type": "PlotlyFigure",
        "highlight": {"from_field": "selected_topic", "mode": "responsibility_ink"},
    }
    assert highlight_binding(spec) == {
        "from_field": "selected_topic",
        "mode": "responsibility_ink",
    }
    assert highlight_binding(None) is None
    assert highlight_binding({}) is None
    assert highlight_binding({"highlight": "bad"}) is None
    assert highlight_binding({"highlight": {}}) is None
    assert highlight_binding({"highlight": {"from_field": "t"}})["mode"] == "default"

    matched = viewers_highlighting_field(
        [spec, {"type": "Markdown", "liquid": "x"}, {"type": "PlotlyFigure"}],
        "selected_topic",
    )
    assert len(matched) == 1
    assert viewers_highlighting_field(None, "x") == []
    assert viewers_highlighting_field([], "x") == []


def test_figure_source_binding_and_resolve():
    spec = {
        "type": "PlotlyFigure",
        "field": "uq_spec",
        "figure_source": {
            "map_field": "uq_by_topic",
            "key_field": "focus_topic",
        },
    }
    assert figure_source_binding(spec) == {
        "map_field": "uq_by_topic",
        "key_field": "focus_topic",
    }
    assert figure_source_binding({}) is None
    store = {
        "focus_topic": "T1",
        "uq_by_topic": {
            "T0": {"data": [{"name": "t0"}], "layout": {}},
            "T1": {"data": [{"name": "t1"}], "layout": {}},
        },
        "uq_spec": {"data": [{"name": "fallback"}], "layout": {}},
    }
    raw = resolve_figure_payload(store.__getitem__, spec)
    assert raw["data"][0]["name"] == "t1"
    store["focus_topic"] = "missing"
    raw2 = resolve_figure_payload(store.__getitem__, spec)
    assert raw2["data"][0]["name"] in {"t0", "t1"}
    watching = viewers_watching_field([spec], "focus_topic")
    assert len(watching) == 1
    assert is_viewer_chrome_type({"type": "Dropdown", "field": "focus_topic"})
    assert is_interactive_viewer_type({"type": "PopulateButton"})


def test_parse_figure_spec_variants():
    fig = {"data": [], "layout": {}}
    assert parse_figure_spec(fig) == {"data": [], "layout": {}}
    assert parse_figure_spec('{"data": [], "layout": {}}') == {
        "data": [],
        "layout": {},
    }
    assert parse_figure_spec(None) is None
    assert parse_figure_spec("") is None
    assert parse_figure_spec("   ") is None
    assert parse_figure_spec("not-json") is None
    assert parse_figure_spec(42) is None
    assert parse_figure_spec({"title": "only"}) is None
    # bare trace list
    traces = [{"type": "scatter", "x": [1], "y": [2]}]
    assert parse_figure_spec(traces) == {"data": traces, "layout": {}}
    # mapping with only data
    assert parse_figure_spec({"data": traces})["layout"] == {}
    assert parse_figure_spec({"layout": {}})["data"] == []


def test_apply_highlight_default_and_responsibility_ink():
    fig = {
        "data": [
            {
                "type": "scatter",
                "x": [0, 1],
                "y": [0, 1],
                "customdata": [{"topic": "A"}, {"topic": "B"}],
                "marker": {},
            },
            "not-a-trace",
            {"type": "scatter", "x": [0], "y": [0]},
        ],
        "layout": {"title": "t"},
    }
    assert apply_highlight(None, selected="B") is None
    highlighted = apply_highlight(fig, selected="B", mode="default")
    assert highlighted["data"][0]["marker"]["opacity"] == [0.25, 1.0]
    assert highlighted["data"][1] == "not-a-trace"
    assert "opacity" not in (highlighted["data"][2].get("marker") or {})

    ink = apply_highlight(
        {
            "data": [
                {
                    "customdata": [
                        {"topic": "A", "responsibilities": {"A": 0.9, "B": 0.1}},
                        {"topic": "B", "responsibilities": {"A": 0.2, "B": 0.8}},
                    ]
                }
            ],
            "layout": {},
        },
        selected="B",
        mode="responsibility_ink",
    )
    assert ink["data"][0]["marker"]["opacity"][0] == 0.15  # clamped low
    assert ink["data"][0]["marker"]["opacity"][1] == 0.8

    # scalar customdata + direct equality
    scalar = apply_highlight(
        {"data": [{"customdata": "B"}], "layout": {}},
        selected="B",
    )
    assert scalar["data"][0]["marker"]["opacity"] == [1.0]

    # selected None leaves traces alone
    left = apply_highlight(fig, selected=None)
    assert "opacity" not in (left["data"][0].get("marker") or {})


def test_customdata_match_keys():
    fig = {
        "data": [
            {
                "customdata": [
                    {"id": "x1"},
                    {"phrase": "hello"},
                    {"selected_topic": 3},
                ]
            }
        ],
        "layout": {},
    }
    assert apply_highlight(fig, selected="x1")["data"][0]["marker"]["opacity"][0] == 1.0
    assert apply_highlight(fig, selected="hello")["data"][0]["marker"]["opacity"][1] == 1.0
    assert apply_highlight(fig, selected=3)["data"][0]["marker"]["opacity"][2] == 1.0
    assert apply_highlight(fig, selected="nope")["data"][0]["marker"]["opacity"] == [
        0.25,
        0.25,
        0.25,
    ]


def test_responsibility_ink_bad_mass_falls_back():
    fig = {
        "data": [
            {
                "customdata": [
                    {"topic": "A", "responsibilities": {"A": "bad"}},
                ]
            }
        ],
        "layout": {},
    }
    out = apply_highlight(fig, selected="A", mode="responsibility_ink")
    assert out["data"][0]["marker"]["opacity"] == [1.0]
