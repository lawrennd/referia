"""CIP-0016: document histograms, cost, MDS, tests (no POT required)."""

import numpy as np

from referia.assess.compute import Compute
from referia.assess.compute.distance import (
    axis_correlates,
    classical_mds,
    cosine_ground_cost,
    document_soft_topic_distributions,
    emd_distance_matrix,
    permanova,
    run_document_distance_analysis,
    topic_means_from_responsibilities,
)


def test_soft_histograms_row_stochastic():
    doc_ids = ["A", "A", "B", "B"]
    R = np.array(
        [
            [1.0, 0.0],
            [0.5, 0.5],
            [0.0, 1.0],
            [0.0, 1.0],
        ]
    )
    P, kept, mass = document_soft_topic_distributions(doc_ids, R, min_mass=1.0)
    assert kept == ["A", "B"]
    assert P.shape == (2, 2)
    assert np.allclose(P.sum(axis=1), 1.0)
    assert mass[0] == 2.0
    assert mass[1] == 2.0
    assert np.allclose(P[0], [0.75, 0.25])


def test_min_mass_drops_small_docs():
    P, kept, _ = document_soft_topic_distributions(
        ["A", "B"],
        [[1.0, 0.0], [0.0, 1.0]],
        min_mass=2.0,
    )
    assert kept == []
    assert P.shape == (0, 2)


def test_topic_means_unit_rows():
    X = np.array([[3.0, 0.0], [0.0, 4.0]])
    R = np.array([[1.0, 0.0], [0.0, 1.0]])
    means = topic_means_from_responsibilities(X, R)
    assert means.shape == (2, 2)
    assert np.allclose(np.linalg.norm(means, axis=1), 1.0)


def test_cosine_ground_cost_zero_diagonal():
    means = np.array([[1.0, 0.0], [0.0, 1.0]])
    M = cosine_ground_cost(means)
    assert M.shape == (2, 2)
    assert np.allclose(np.diag(M), 0.0)
    assert np.all(M >= 0)
    assert M[0, 1] > 0.9


def test_classical_mds_hand_built_distance():
    D = np.array(
        [
            [0.0, 1.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 0.0],
        ]
    )
    mds = classical_mds(D, n_components=2)
    assert mds["coords"].shape == (3, 2)
    assert len(mds["explained"]) == 2
    assert mds["negative_ratio"] >= 0.0


def test_permanova_permutation_count():
    D = np.array(
        [
            [0.0, 0.1, 1.0, 1.1],
            [0.1, 0.0, 1.1, 1.0],
            [1.0, 1.1, 0.0, 0.1],
            [1.1, 1.0, 0.1, 0.0],
        ]
    )
    res = permanova(D, ["g1", "g1", "g2", "g2"], n_perm=19, seed=0)
    assert res["n_perm"] == 19
    assert res["n_docs"] == 4
    assert res["n_groups"] == 2
    assert 0.0 <= res["p_value"] <= 1.0


def test_axis_correlates_jsonable():
    coords = np.array([[0.0, 1.0], [1.0, 0.0], [0.5, 0.5]])
    P = np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])
    rows = axis_correlates(coords, P, topic_labels={"T0": "Privacy"}, top=1)
    assert rows
    assert all(set(r) >= {"axis", "end", "label", "r"} for r in rows)


def test_emd_missing_or_runs():
    P = np.array([[1.0, 0.0], [0.0, 1.0]])
    M = np.array([[0.0, 1.0], [1.0, 0.0]])
    try:
        D = emd_distance_matrix(P, M)
    except ImportError as exc:
        assert "referia[distance]" in str(exc)
        return
    assert D.shape == (2, 2)
    assert D[0, 1] == D[1, 0]
    assert D[0, 1] > 0


def test_facade_with_stub_emd(monkeypatch):
    from referia.assess.compute import distance as dist

    monkeypatch.setattr(
        dist,
        "emd_distance_matrix",
        lambda P, M: np.abs(P[:, None, :] - P[None, :, :]).sum(-1),
    )
    packed = run_document_distance_analysis(
        embeddings=[
            [1.0, 0.0],
            [0.9, 0.1],
            [0.8, 0.2],
            [0.7, 0.3],
            [0.2, 0.8],
            [0.1, 0.9],
            [0.0, 1.0],
            [0.15, 0.85],
        ],
        doc_ids=["A", "A", "B", "B", "C", "C", "D", "D"],
        responsibilities=[
            [1.0, 0.0],
            [1.0, 0.0],
            [0.9, 0.1],
            [0.8, 0.2],
            [0.2, 0.8],
            [0.1, 0.9],
            [0.0, 1.0],
            [0.0, 1.0],
        ],
        groups=["g1", "g1", "g1", "g1", "g2", "g2", "g2", "g2"],
        topic_labels={"T0": "Privacy", "T1": "Access"},
        min_mass=1.0,
        n_perm=9,
        seed=0,
    )
    assert len(packed) == 16
    P, means, mass, docs, cost, D, coords, explained, perm, disp, axes, md, mds_spec, heat, emd, bars = packed
    assert docs == ["A", "B", "C", "D"]
    assert np.allclose(np.sum(P, axis=1), 1.0)
    assert "PERMANOVA" in md
    assert mds_spec["data"][0]["customdata"][0]["doc"] in docs
    assert heat["data"][0]["type"] == "heatmap"


def test_distance_functions_registered():
    names = {e["name"] for e in Compute({"input": {}})._compute_functions_list()}
    assert "run_document_distance_analysis" in names
    assert "document_soft_topic_distributions" in names
    assert "emd_distance_matrix" in names
