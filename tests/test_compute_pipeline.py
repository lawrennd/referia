"""CIP-0023: pipeline manifest, axis selection, DAG helpers."""

from __future__ import annotations

import pytest
import yaml

from referia.assess.compute.multiverse import run_analysis_multiverse
from referia.assess.compute.pipeline import (
    compose_pipeline_manifest,
    expand_stage_selection,
    load_pipeline_manifest,
    pipeline_dag_figure,
    pipeline_stage_params_md,
    resolve_active_paper_axes,
    selection_cost_gate,
    study_root_from_info_dir,
)


MINI = {
    "nodes": [
        {
            "id": "07_grounds",
            "permalink": "/07_grounds/",
            "title": "Grounds",
            "parameters": [
                {
                    "key": "grounds_model",
                    "cost_class": "llm",
                    "multiverse_eligible": True,
                }
            ],
        },
        {
            "id": "07_part_b",
            "permalink": "/07_part_b/",
            "title": "Part B",
            "parameters": [
                {
                    "key": "n_boot",
                    "cost_class": "aggregate",
                    "multiverse_eligible": True,
                    "paper_axis": None,
                },
                {
                    "key": "seed",
                    "cost_class": "display",
                    "multiverse_eligible": False,
                },
            ],
        },
        {
            "id": "11_multiverse",
            "permalink": "/11_multiverse/",
            "title": "Multiverse",
            "parameters": [
                {
                    "key": "axis_definitions",
                    "cost_class": "aggregate",
                    "multiverse_eligible": True,
                    "paper_axis": "definitions",
                }
            ],
        },
    ],
    "edges": [
        {"from": "07_grounds", "to": "07_part_b", "via": "grounds.yml"},
        {"from": "07_part_b", "to": "11_multiverse", "via": "part_b.yml"},
    ],
}


def test_load_pipeline_manifest_ok():
    m = load_pipeline_manifest(data=MINI)
    assert len(m["nodes"]) == 3
    assert len(m["edges"]) == 2


def test_load_pipeline_rejects_cycle(tmp_path):
    bad = {
        "nodes": [{"id": "a"}, {"id": "b"}],
        "edges": [
            {"from": "a", "to": "b"},
            {"from": "b", "to": "a"},
        ],
    }
    path = tmp_path / "pipeline.yml"
    path.write_text(yaml.safe_dump(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="cycle"):
        load_pipeline_manifest(path)


def test_load_pipeline_rejects_bad_cost_class():
    bad = {
        "nodes": [
            {
                "id": "a",
                "parameters": [
                    {"key": "x", "cost_class": "magic", "multiverse_eligible": True}
                ],
            }
        ],
        "edges": [],
    }
    with pytest.raises(ValueError, match="cost_class"):
        load_pipeline_manifest(data=bad)


def test_expand_stage_selection_aggregate_only():
    m = load_pipeline_manifest(data=MINI)
    got = expand_stage_selection(m, ["07_part_b", "07_grounds"])
    keys = {(g["stage"], g["key"]) for g in got}
    assert ("07_part_b", "n_boot") in keys
    assert ("07_grounds", "grounds_model") not in keys  # llm


def test_selection_cost_gate_refuses_llm():
    gate = selection_cost_gate(
        [
            {
                "key": "n_boot",
                "cost_class": "aggregate",
                "multiverse_eligible": True,
            },
            {
                "key": "grounds_model",
                "cost_class": "llm",
                "multiverse_eligible": True,
            },
        ]
    )
    assert len(gate["executable"]) == 1
    assert len(gate["refused"]) == 1
    assert "grounds_model" in gate["message"]


def test_pipeline_dag_figure_has_nodes():
    fig = pipeline_dag_figure(load_pipeline_manifest(data=MINI))
    assert fig["data"]
    assert any(t.get("mode") == "markers+text" for t in fig["data"])


def test_pipeline_stage_params_md():
    md = pipeline_stage_params_md(
        load_pipeline_manifest(data=MINI), "07_part_b", values={"n_boot": 2000}
    )
    assert "n_boot" in md
    assert "aggregate" in md
    assert "2000" in md


def test_resolve_active_paper_axes_subset():
    axes = resolve_active_paper_axes(
        axis_definitions=True,
        axis_weightings=False,
        axis_exclusions=False,
        axis_thresholds=False,
        axis_rounds=False,
    )
    assert axes["definitions"] is True
    assert axes["weightings"] is False


def _points():
    return [
        {
            "format": "chatbot",
            "doc_id": "c1",
            "basis": "principle",
            "round": "spring_2026",
            "session_type": "chatbot",
            "quote_support": 1.0,
            "unit_id": "c1::c0003",
            "extract_text": "Speaker 2: x",
            "lens": "T1",
        },
        {
            "format": "chatbot",
            "doc_id": "c2",
            "basis": "principle",
            "round": "autumn_2025",
            "session_type": "chatbot",
            "quote_support": 1.0,
            "unit_id": "c2::c0003",
            "extract_text": "Speaker 2: y",
            "lens": "T1",
        },
        {
            "format": "workshop",
            "doc_id": "w1",
            "basis": "personal_experience",
            "round": "spring_2026",
            "session_type": "breakout",
            "quote_support": 1.0,
            "unit_id": "w1::c0003",
            "extract_text": "Speaker 2: z",
            "lens": "T0",
        },
        {
            "format": "workshop",
            "doc_id": "w2",
            "basis": "others_experience",
            "round": "autumn_2025",
            "session_type": "breakout",
            "quote_support": 1.0,
            "unit_id": "w2::c0003",
            "extract_text": "Speaker 2: w",
            "lens": "T0",
        },
    ]


def test_multiverse_all_axes_default_matches_full_product():
    _summary, _md, n_full = run_analysis_multiverse(
        _points(), n_jsd_shuffles=0, seed=0
    )
    _s2, _m2, n2 = run_analysis_multiverse(
        _points(),
        n_jsd_shuffles=0,
        seed=0,
        axis_definitions=True,
        axis_weightings=True,
        axis_exclusions=True,
        axis_thresholds=True,
        axis_rounds=True,
    )
    assert n_full == n2
    assert n_full > 1


def test_multiverse_definitions_only_smaller_product():
    _s, md_full, n_full = run_analysis_multiverse(
        _points(), n_jsd_shuffles=0, seed=0
    )
    _s2, md, n = run_analysis_multiverse(
        _points(),
        n_jsd_shuffles=0,
        seed=0,
        axis_definitions=True,
        axis_weightings=False,
        axis_exclusions=False,
        axis_thresholds=False,
        axis_rounds=False,
    )
    assert n < n_full
    assert n == 3  # three definitions × canonical others
    assert "definitions" in md
    assert "CIP-0023" in md


def test_load_pipeline_requires_path_or_data():
    with pytest.raises(ValueError, match="path or data"):
        load_pipeline_manifest()


def test_load_pipeline_rejects_non_mapping_root():
    with pytest.raises(ValueError, match="mapping"):
        load_pipeline_manifest(data=["not", "a", "map"])


def test_load_pipeline_rejects_empty_nodes_and_bad_edges():
    with pytest.raises(ValueError, match="non-empty"):
        load_pipeline_manifest(data={"nodes": [], "edges": []})
    with pytest.raises(ValueError, match="edges must be a list"):
        load_pipeline_manifest(data={"nodes": [{"id": "a"}], "edges": "nope"})


def test_load_pipeline_rejects_bad_nodes_and_edges():
    with pytest.raises(ValueError, match="each node must be a mapping"):
        load_pipeline_manifest(data={"nodes": ["a"], "edges": []})
    with pytest.raises(ValueError, match="node.id is required"):
        load_pipeline_manifest(data={"nodes": [{"id": "  "}], "edges": []})
    with pytest.raises(ValueError, match="duplicate node id"):
        load_pipeline_manifest(
            data={"nodes": [{"id": "a"}, {"id": "a"}], "edges": []}
        )
    with pytest.raises(ValueError, match="parameter entries must be maps"):
        load_pipeline_manifest(
            data={
                "nodes": [{"id": "a", "parameters": [1]}],
                "edges": [],
            }
        )
    with pytest.raises(ValueError, match="parameter key required"):
        load_pipeline_manifest(
            data={
                "nodes": [{"id": "a", "parameters": [{"key": ""}]}],
                "edges": [],
            }
        )
    with pytest.raises(ValueError, match="each edge must be a mapping"):
        load_pipeline_manifest(
            data={"nodes": [{"id": "a"}], "edges": ["bad"]}
        )
    with pytest.raises(ValueError, match="unknown node"):
        load_pipeline_manifest(
            data={
                "nodes": [{"id": "a"}],
                "edges": [{"from": "a", "to": "missing"}],
            }
        )


def test_load_pipeline_string_knob_defaults_to_display():
    m = load_pipeline_manifest(
        data={
            "nodes": [{"id": "a", "parameters": ["seed", {"key": "n_boot"}]}],
            "edges": [],
        }
    )
    knobs = {k["key"]: k for k in m["nodes"][0]["parameters"]}
    assert knobs["seed"]["cost_class"] == "display"
    assert knobs["seed"]["multiverse_eligible"] is False
    assert knobs["n_boot"]["cost_class"] == "display"
    assert knobs["n_boot"]["label"] == "n_boot"
    assert m["nodes"][0]["permalink"] == "/a/"
    assert m["nodes"][0]["title"] == "a"


def test_expand_stage_selection_all_eligible_and_skips_unknown():
    m = load_pipeline_manifest(data=MINI)
    all_elig = expand_stage_selection(
        m, ["07_part_b", "07_grounds", "missing"], executable_only=False
    )
    keys = {(g["stage"], g["key"]) for g in all_elig}
    assert ("07_part_b", "n_boot") in keys
    assert ("07_grounds", "grounds_model") in keys
    assert ("07_part_b", "seed") not in keys  # not eligible


def test_selection_cost_gate_ignores_display_and_non_maps():
    gate = selection_cost_gate(
        [
            "skip-me",
            {"key": "seed", "cost_class": "display"},
            {
                "key": "n_boot",
                "cost_class": "aggregate",
                "multiverse_eligible": False,
            },
            {"key": "refit_x", "cost_class": "refit"},
        ]
    )
    assert gate["executable"] == []
    assert len(gate["refused"]) == 1
    assert gate["ok"] is False
    assert "refit_x" in gate["message"]
    empty = selection_cost_gate(
        [{"key": "n_boot", "cost_class": "aggregate"}]
    )
    assert empty["ok"] is True
    assert empty["message"] == ""


def test_resolve_active_paper_axes_strings_and_active_axes():
    axes = resolve_active_paper_axes(
        axis_definitions="yes",
        axis_weightings="0",
        axis_exclusions="",
        axis_thresholds=None,
        axis_rounds="off",
        active_axes={"weightings": "on", "rounds": False},
    )
    assert axes["definitions"] is True
    assert axes["weightings"] is True
    assert axes["exclusions"] is True  # blank → default True
    assert axes["thresholds"] is True
    assert axes["rounds"] is False
    all_off = resolve_active_paper_axes(
        axis_definitions=False,
        axis_weightings=False,
        axis_exclusions=False,
        axis_thresholds=False,
        axis_rounds=False,
    )
    assert not any(all_off.values())


def test_pipeline_dag_figure_empty():
    fig = pipeline_dag_figure({"nodes": [], "edges": []})
    assert fig["data"] == []
    assert "Empty" in fig["layout"]["title"]


def test_study_root_from_info_dir(tmp_path):
    corpus = tmp_path / "_data" / "corpus"
    corpus.mkdir(parents=True)
    assert study_root_from_info_dir(corpus) == tmp_path
    assert study_root_from_info_dir(
        corpus, iface_directory=tmp_path / "study"
    ) == tmp_path / "study"
    assert study_root_from_info_dir(None) is None
    # Non-corpus info dir → parent is study root.
    info = tmp_path / "info"
    info.mkdir()
    assert study_root_from_info_dir(info) == tmp_path


def test_compose_pipeline_manifest_discovers_edges(tmp_path):
    (tmp_path / "producer.md").write_text(
        "---\nlayout: referia\ntitle: Producer\npermalink: /producer/\n"
        "output:\n  directory: _data/corpus\n  filename: grounds.yml\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "consumer.md").write_text(
        "---\nlayout: referia\ntitle: Consumer\npermalink: /consumer/\n"
        "grounds:\n  directory: _data/corpus\n  filename: grounds.yml\n---\n",
        encoding="utf-8",
    )
    overlay = {
        "nodes": [
            {
                "id": "consumer",
                "title": "Part B overlay",
                "parameters": [
                    {
                        "key": "n_boot",
                        "cost_class": "aggregate",
                        "multiverse_eligible": True,
                    }
                ],
            }
        ],
        "edges": [],
    }
    m = compose_pipeline_manifest(tmp_path, overlay=overlay)
    assert m["source"] == "discovered"
    assert {n["id"] for n in m["nodes"]} >= {"producer", "consumer"}
    assert any(
        e["from"] == "producer" and e["to"] == "consumer" for e in m["edges"]
    )
    consumer = next(n for n in m["nodes"] if n["id"] == "consumer")
    assert consumer["title"] == "Part B overlay"
    assert consumer["parameters"][0]["key"] == "n_boot"


def test_compose_falls_back_to_overlay_when_no_stages(tmp_path):
    m = compose_pipeline_manifest(tmp_path, overlay=MINI)
    assert m["source"] == "manifest"
    assert len(m["edges"]) == 2


def test_compose_empty_without_discovery_or_overlay():
    assert compose_pipeline_manifest() == {
        "nodes": [],
        "edges": [],
        "source": "empty",
    }


def test_compose_overlay_only_node_and_string_knobs(tmp_path):
    """Overlay stage absent from discovery + string parameter knobs."""
    (tmp_path / "only.md").write_text(
        "---\nlayout: referia\ntitle: Only\n"
        "output:\n  directory: d\n  filename: a.yml\n---\n",
        encoding="utf-8",
    )
    overlay = {
        "nodes": [
            {
                "id": "only",
                "title": "",  # fall back to discovered title
                "parameters": ["seed"],  # string knob → display
            },
            {
                "id": "chrome_only",
                "title": "Chrome Only",
                "parameters": [
                    {
                        "key": "axis_definitions",
                        "cost_class": "aggregate",
                        "multiverse_eligible": True,
                        "paper_axis": "definitions",
                    }
                ],
            },
        ],
        "edges": [],
    }
    m = compose_pipeline_manifest(tmp_path, overlay=overlay)
    assert m["source"] == "discovered"
    ids = {n["id"] for n in m["nodes"]}
    assert "only" in ids and "chrome_only" in ids
    only = next(n for n in m["nodes"] if n["id"] == "only")
    # Empty overlay title normalises to id before merge.
    assert only["title"] == "only"
    assert only["parameters"][0]["key"] == "seed"
    assert only["parameters"][0]["cost_class"] == "display"
    chrome = next(n for n in m["nodes"] if n["id"] == "chrome_only")
    assert chrome["title"] == "Chrome Only"


def test_compose_adds_edge_endpoints_missing_from_stages(tmp_path):
    from unittest.mock import patch

    stages = [
        {
            "id": "a",
            "meta": {"layout": "referia", "title": "A", "permalink": "/a/"},
        }
    ]
    fake = {
        "stages": ["a"],
        "edges": [{"from": "a", "to": "ghost", "via": "x.yml"}],
        "orphans": [],
    }
    with patch(
        "referia.assess.compute.pipeline.discover_pipeline_edges",
        return_value=fake,
    ):
        m = compose_pipeline_manifest(tmp_path, stages=stages)
    assert m["source"] == "discovered"
    assert {n["id"] for n in m["nodes"]} == {"a", "ghost"}
    assert m["edges"][0]["to"] == "ghost"


def test_load_pipeline_allows_empty_nodes_for_overlay():
    m = load_pipeline_manifest(
        data={"nodes": [], "edges": []}, allow_empty_nodes=True
    )
    assert m["nodes"] == []
    assert m["edges"] == []


def test_pipeline_stage_params_md_branches():
    m = load_pipeline_manifest(data=MINI)
    assert "Select a stage" in pipeline_stage_params_md(m, None)
    assert "Unknown stage" in pipeline_stage_params_md(m, "nope")
    bare = load_pipeline_manifest(
        data={"nodes": [{"id": "bare"}], "edges": []}
    )
    assert "No declared parameters" in pipeline_stage_params_md(bare, "bare")
    md = pipeline_stage_params_md(
        m,
        "07_part_b",
        values={"n_boot": [1, 2], "seed": {"a": 1}},
    )
    assert "n_boot" in md
    assert "[" in md or "1" in md
