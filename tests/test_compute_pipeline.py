"""CIP-0023: pipeline manifest, axis selection, DAG helpers."""

from __future__ import annotations

import pytest
import yaml

from referia.assess.compute.multiverse import run_analysis_multiverse
from referia.assess.compute.pipeline import (
    expand_stage_selection,
    load_pipeline_manifest,
    pipeline_dag_figure,
    pipeline_stage_params_md,
    resolve_active_paper_axes,
    selection_cost_gate,
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
