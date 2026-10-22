"""CIP-001A: VQ codebook, mass weights, QR expand, projection walk."""

import numpy as np
import pytest

from referia.assess.compute.grain_fit import subject_grain_fit
from referia.assess.compute.kmeans import fit_kmeans
from referia.assess.compute.vq import expand_vq_responsibilities, subject_vq_fit
from referia.assess.viewer_bindings import parse_figure_spec
from referia.util.plotly_figures import (
    stiefel_step_scale,
    vq_projection_walk_plotly_spec,
)


def _l2(X: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(X, axis=1, keepdims=True)
    return X / np.clip(n, 1e-12, None)


def test_expand_vq_responsibilities_is_qr():
    R = np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])
    ids = [0, 0, 2, 1]
    QR = expand_vq_responsibilities(ids, R)
    assert QR.shape == (4, 2)
    np.testing.assert_allclose(QR[0], R[0])
    np.testing.assert_allclose(QR[2], R[2])
    np.testing.assert_allclose(QR[3], R[1])


def test_expand_vq_out_of_range_raises():
    with pytest.raises(ValueError, match="outside codebook"):
        expand_vq_responsibilities([0, 3], np.eye(2))


def test_subject_vq_fit_codebook_shapes():
    rng = np.random.default_rng(0)
    X = _l2(rng.normal(size=(40, 12)))
    phrases = [f"p{i}" for i in range(40)]
    out = subject_vq_fit(
        X,
        phrases=phrases,
        n_vq=5,
        force_refit=True,
        seed=0,
        kmeans_n_init=2,
        vq_walk_frames=6,
        vq_walk_subspace=4,
    )
    ids, cents, exemplars, mass, spec, m, inertia, n = out
    assert n == 40
    assert m == 5
    assert len(ids) == 40
    assert np.asarray(cents).shape == (5, 12)
    assert len(exemplars) == 5
    np.testing.assert_allclose(np.sum(mass), 40)
    assert spec["frames"]
    labels = [b["label"] for b in spec["layout"]["updatemenus"][0]["buttons"]]
    assert labels == ["Play", "Pause"]


def test_vq_walk_spec_frames_and_ellipses():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(30, 8))
    labels = np.repeat(np.arange(3), 10)
    centres = np.vstack([X[labels == j].mean(axis=0) for j in range(3)])
    spec = vq_projection_walk_plotly_spec(
        X,
        labels,
        centres,
        phrases=[f"p{i}" for i in range(30)],
        masses=np.array([10.0, 10.0, 10.0]),
        n_frames=8,
        subspace=4,
        linger=True,
        seed=1,
    )
    assert spec is not None
    assert len(spec["frames"]) == 8
    assert len(spec["data"]) == 3
    assert None in spec["data"][2]["x"]
    parsed = parse_figure_spec(spec)
    assert parsed is not None
    assert "frames" in parsed
    assert len(parsed["frames"]) == 8


def test_linger_scales_step_by_plane_variance():
    fast = stiefel_step_scale(0.1, 0.25, True)
    slow = stiefel_step_scale(0.1, 4.0, True)
    assert slow < fast
    assert stiefel_step_scale(0.1, 4.0, False) == stiefel_step_scale(
        0.1, 0.25, False
    )


def test_kmeans_sample_weight_shifts_centre():
    X = np.array(
        [
            [0.0, 0.0],
            [0.0, 0.0],
            [10.0, 0.0],
        ],
        dtype=float,
    )
    unif = fit_kmeans(X, 1, n_init=1, seed=0)
    heavy = fit_kmeans(X, 1, n_init=1, seed=0, sample_weight=[1.0, 1.0, 50.0])
    assert unif["centers"][0, 0] < heavy["centers"][0, 0]


def test_agglomerative_mass_raises():
    rng = np.random.default_rng(2)
    X = _l2(rng.normal(size=(12, 6)))
    with pytest.raises(ValueError, match="lens_weight=mass"):
        subject_grain_fit(
            X,
            phrases=[f"p{i}" for i in range(12)],
            cluster_method="agglomerative",
            n_clusters=3,
            force_refit=True,
            lens_weight="mass",
            vq_mass=np.ones(12),
        )


def test_grain_skip_requires_matching_row_count():
    rng = np.random.default_rng(3)
    X = _l2(rng.normal(size=(10, 6)))
    leftover = np.ones((40, 2)) / 2.0
    out = subject_grain_fit(
        X,
        phrases=[f"p{i}" for i in range(10)],
        cluster_method="kmeans",
        n_clusters=2,
        force_refit=False,
        responsibilities=leftover,
        kmeans_n_init=2,
        seed=0,
    )
    R = np.asarray(out[0], float)
    assert R.shape[0] == 10
    assert R.shape[1] == 2


def test_reactplot_template_adds_frames():
    from pathlib import Path

    html = (
        Path(__file__).resolve().parents[1]
        / "referia"
        / "web"
        / "templates"
        / "base.html"
    ).read_text()
    assert "Plotly.addFrames" in html
    assert "Plotly.deleteFrames" in html


def test_document_distance_expands_qr():
    from referia.assess.compute.distance import document_soft_topic_distributions
    from referia.assess.compute.vq import expand_vq_responsibilities

    R = np.eye(3)
    ids = [0, 0, 1, 2, 2]
    QR = expand_vq_responsibilities(ids, R)
    P, docs, mass = document_soft_topic_distributions(
        ["a", "a", "b", "b", "b"], QR, min_mass=1.0
    )
    assert docs == ["a", "b"]
    np.testing.assert_allclose(P[0], [1.0, 0.0, 0.0])
    np.testing.assert_allclose(P[1], [0.0, 1 / 3, 2 / 3])
    np.testing.assert_allclose(mass, [2.0, 3.0])
