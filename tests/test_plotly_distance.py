"""CIP-0016 Plotly builders: keys and customdata.doc."""

from referia.util.plotly_figures import (
    axis_correlate_bars_spec,
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
