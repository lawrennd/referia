"""CIP-0016 Plotly builders: keys and customdata.doc."""

import numpy as np

from referia.util.plotly_figures import (
    _leaf_order,
    _seriate_share_matrix,
    axis_correlate_bars_spec,
    chapter_lens_radar_spec,
    doc_mds_plotly_spec,
    emd_heatmap_spec,
    topic_document_heatmap_spec,
)


def test_mds_customdata_aligned_with_docs():
    spec = doc_mds_plotly_spec(
        [[0.0, 1.0], [1.0, 0.0]],
        ["docA", "docB"],
        groups=["survey", "dialogue"],
    )
    docs = [pt["doc"] for tr in spec["data"] for pt in tr["customdata"]]
    assert set(docs) == {"docA", "docB"}
    assert spec["data"][0]["type"] == "scatter"


def test_topic_heatmap_uses_labels():
    spec = topic_document_heatmap_spec(
        [[0.8, 0.2], [0.1, 0.9]],
        ["docA", "docB"],
        topic_labels={"T0": "Privacy", "T1": "Access"},
    )
    assert spec["data"][0]["x"] == ["Privacy", "Access"]
    assert spec["data"][0]["y"] == ["docA", "docB"]
    assert spec["data"][0]["customdata"][0][0]["doc"] == "docA"


def test_emd_heatmap_square():
    spec = emd_heatmap_spec([[0.0, 0.4], [0.4, 0.0]], ["docA", "docB"])
    assert spec["data"][0]["x"] == ["docA", "docB"]
    assert spec["data"][0]["y"] == ["docA", "docB"]


def test_axis_bars_from_correlates():
    spec = axis_correlate_bars_spec(
        [
            {"axis": 1, "end": "positive", "label": "Privacy", "r": 0.8},
            {"axis": 1, "end": "negative", "label": "Access", "r": -0.6},
        ]
    )
    assert spec["data"][0]["type"] == "bar"
    assert "Privacy" in spec["data"][0]["x"]


def test_mds_pads_one_component_and_rejects_mismatch():
    padded = doc_mds_plotly_spec([[0.5], [1.5]], ["docA", "docB"])
    assert padded["data"][0]["y"] == [0.0, 0.0]
    empty = doc_mds_plotly_spec([[0.0, 1.0]], ["docA", "docB"])
    assert empty["data"] == []
    regrouped = doc_mds_plotly_spec(
        [[0.0, 1.0], [1.0, 0.0]],
        ["docA", "docB"],
        groups=["only-one"],
    )
    assert len(regrouped["data"]) == 1


def test_axis_bars_empty_and_duplicate_labels():
    empty = axis_correlate_bars_spec(None)
    assert empty["data"]
    spec = axis_correlate_bars_spec(
        [
            {"axis": 1, "end": "positive", "label": "Privacy", "r": 0.8},
            {"axis": 1, "end": "positive", "label": "Privacy", "r": 0.4},
        ]
    )
    assert spec["data"][0]["x"].count("Privacy") == 1


def test_plotly_titles_and_topic_id_fallback():
    titled = doc_mds_plotly_spec(
        [[0.0, 1.0]],
        ["docA"],
        title="Custom MDS",
    )
    assert titled["layout"]["title"]["text"] == "Custom MDS"
    heat = topic_document_heatmap_spec(
        [[0.8, 0.2]],
        ["docA"],
        topic_labels={0: "Privacy", "1": "Access"},
        title="Shares",
    )
    assert heat["layout"]["title"]["text"] == "Shares"
    assert heat["data"][0]["x"] == ["Privacy", "Access"]
    empty_heat = topic_document_heatmap_spec([0.5], ["docA"])
    assert empty_heat["data"][0]["z"] == []
    emd = emd_heatmap_spec([0.0], ["docA"], title="EMD")
    assert emd["layout"]["title"]["text"] == "EMD"
    assert emd["data"][0]["z"] == []
    bars = axis_correlate_bars_spec(
        [{"axis": 2, "end": "positive", "topic_id": "T3", "r": 0.2}],
        title="Bars",
    )
    assert bars["layout"]["title"]["text"] == "Bars"
    assert "T3" in bars["data"][0]["x"]


def test_chapter_lens_radar_and_heatmap_labels():
    radar = chapter_lens_radar_spec(
        [[0.8, 0.2], [0.1, 0.9]],
        ["chapter_1.pdf", "chapter_2.pdf"],
        topic_labels={"T0": "Privacy", "T1": "Access"},
        doc_labels=["Chapter 1", "Chapter 2"],
    )
    assert radar["data"][0]["type"] == "scatterpolar"
    assert radar["data"][0]["name"] == "Chapter 1"
    assert radar["data"][0]["theta"][0] == "Privacy"
    empty = chapter_lens_radar_spec([0.5], ["docA"])
    assert empty["data"] == []
    heat = topic_document_heatmap_spec(
        [[0.8, 0.2]],
        ["chapter_1.pdf"],
        doc_labels=["1. The starting point"],
    )
    assert heat["layout"]["title"]["text"] == "Lens share by chapter"
    assert heat["data"][0]["y"] == ["1. The starting point"]
    assert heat["data"][0]["customdata"][0][0]["doc"] == "chapter_1.pdf"


def _adjacent(a, b, seq) -> bool:
    return abs(seq.index(a) - seq.index(b)) == 1


def test_heatmap_leaf_order_groups_similar_rows_and_columns():
    # Interleaved block structure: A≈C on lenses 0–1, B≈D on lenses 2–3.
    P = [
        [0.9, 0.1, 0.0, 0.0],
        [0.0, 0.0, 0.9, 0.1],
        [0.8, 0.2, 0.0, 0.0],
        [0.0, 0.0, 0.8, 0.2],
    ]
    docs = ["A", "B", "C", "D"]
    topics = {"T0": "L0", "T1": "L1", "T2": "L2", "T3": "L3"}
    heat = topic_document_heatmap_spec(P, docs, topic_labels=topics)
    y = heat["data"][0]["y"]
    x = heat["data"][0]["x"]
    assert _adjacent("A", "C", y)
    assert _adjacent("B", "D", y)
    assert _adjacent("L0", "L1", x)
    assert _adjacent("L2", "L3", x)
    raw = topic_document_heatmap_spec(
        P, docs, topic_labels=topics, reorder=False
    )
    assert raw["data"][0]["y"] == docs
    radar = chapter_lens_radar_spec(P, docs, topic_labels=topics)
    assert radar["data"][0]["theta"][:-1] == x
    # Seriation is Bar-Joseph leaf order on both axes: chapters (rows) and
    # lenses (columns). Heatmap x must match radar spokes.
    arr, ser_docs, _, ser_x = _seriate_share_matrix(P, docs, topic_labels=topics)
    assert ser_docs == y
    assert ser_x == x
    assert list(_leaf_order(np.asarray(P, float))) != list(range(4))
    assert list(_leaf_order(np.asarray(P, float).T)) != list(range(4))


def test_leaf_order_fallbacks(monkeypatch):
    assert list(_leaf_order(np.array([1.0, 2.0, 3.0]))) == []
    assert list(_leaf_order(np.zeros((2, 4)))) == [0, 1]
    identical = np.ones((4, 3))
    assert list(_leaf_order(identical)) == [0, 1, 2, 3]

    import sys
    import types

    monkeypatch.setitem(sys.modules, "scipy.cluster.hierarchy", types.ModuleType("scipy.cluster.hierarchy"))
    assert list(_leaf_order(np.eye(4))) == [0, 1, 2, 3]


def test_leaf_order_optimal_ordering_exception(monkeypatch):
    import scipy.cluster.hierarchy as sch

    monkeypatch.setattr(
        sch,
        "optimal_leaf_ordering",
        lambda Z, y: (_ for _ in ()).throw(ValueError("degenerate")),
    )
    order = _leaf_order(
        np.array(
            [
                [1.0, 0.0, 0.0],
                [0.9, 0.1, 0.0],
                [0.0, 0.0, 1.0],
                [0.0, 0.1, 0.9],
            ]
        )
    )
    assert sorted(order.tolist()) == [0, 1, 2, 3]


def test_seriate_share_matrix_skips_when_shape_mismatch():
    arr, docs, labels, x = _seriate_share_matrix(
        np.array([0.5, 0.5]),
        ["a.pdf", "b.pdf"],
        topic_labels={"T0": "L0"},
    )
    assert arr.ndim == 1
    assert docs == ["a.pdf", "b.pdf"]
    assert x == []
    arr2, docs2, labels2, x2 = _seriate_share_matrix(
        [[0.8, 0.2], [0.1, 0.9], [0.5, 0.5]],
        ["only-one"],
        topic_labels={"T0": "L0", "T1": "L1"},
        doc_labels=["too", "many"],
        reorder=True,
    )
    assert docs2 == ["only-one"]
    assert labels2 == ["only-one"]
    assert x2 == ["L0", "L1"]
