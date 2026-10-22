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


def test_expand_vq_rejects_empty_and_1d():
    with pytest.raises(ValueError, match="2-D"):
        expand_vq_responsibilities([0], np.arange(3.0))
    with pytest.raises(ValueError, match="non-empty"):
        expand_vq_responsibilities([], np.eye(2))


def test_subject_vq_fit_guards_and_skip(monkeypatch):
    rng = np.random.default_rng(4)
    X = _l2(rng.normal(size=(16, 6)))
    with pytest.raises(ValueError, match="non-empty 2-D"):
        subject_vq_fit(np.zeros((0, 6)), n_vq=2)
    with pytest.raises(ValueError, match="n_vq must be >= 1"):
        subject_vq_fit(X, n_vq=0)
    first = subject_vq_fit(
        X,
        phrases=[f"p{i}" for i in range(16)],
        n_vq=4,
        force_refit=True,
        seed=0,
        kmeans_n_init=2,
        vq_walk_frames=4,
        vq_walk_linger="yes",
    )
    skipped = subject_vq_fit(
        X,
        phrases="only",
        n_vq=4,
        force_refit=False,
        cluster_ids=first[0],
        codebook_embeddings=first[1],
        codebook_phrases=first[2],
        vq_mass=first[3],
        vq_spec=first[4],
        vq_inertia=first[6],
    )
    assert skipped[0] == first[0]
    assert skipped[4] is first[4]

    def _no_centres(embeddings, n_clusters, **_kwargs):
        n = np.asarray(embeddings).shape[0]
        labels = np.zeros(n, dtype=int)
        return {"labels": labels, "centers": np.zeros(3), "inertia": 0.0}

    monkeypatch.setattr(
        "referia.assess.compute.vq.fit_kmeans", _no_centres
    )
    rebuilt = subject_vq_fit(
        X, phrases=[f"p{i}" for i in range(16)], n_vq=3, force_refit=True
    )
    assert rebuilt[2].count("—") == 2
    np.testing.assert_allclose(rebuilt[3], [16.0, 0.0, 0.0])


def test_vq_walk_returns_none_and_covers_edges():
    from referia.util.plotly_figures import (
        _cluster_cov2,
        _ellipse_polyline,
        _qr_stiefel,
    )

    rng = np.random.default_rng(5)
    X = rng.normal(size=(12, 5))
    labels = np.zeros(12, dtype=int)
    centres = X[:2]
    assert vq_projection_walk_plotly_spec(X[:2], labels[:2], centres) is None
    assert vq_projection_walk_plotly_spec(X, labels[:3], centres) is None
    assert vq_projection_walk_plotly_spec(X, labels, np.zeros((2, 3))) is None
    long = "word " * 40
    phrases = [long] * 20
    spec = vq_projection_walk_plotly_spec(
        rng.normal(size=(20, 4)),
        np.concatenate([np.zeros(18, dtype=int), np.ones(2, dtype=int)]),
        rng.normal(size=(3, 4)),
        phrases=phrases,
        masses=np.array([1.0]),
        n_frames=4,
        subspace=3,
        linger=False,
        max_points=8,
        seed=5,
    )
    assert spec is not None
    assert "linger=off" in spec["layout"]["title"]["text"]
    assert "…" in spec["data"][0]["text"][0]
    assert len(spec["data"][0]["x"]) == 8
    floor = _cluster_cov2(np.zeros((1, 2)), 0.1)
    np.testing.assert_allclose(floor, 0.01 * np.eye(2))
    nan_xy = np.array([[0.0, 0.0], [np.nan, 1.0]])
    nan_cov = _cluster_cov2(nan_xy, 0.2)
    np.testing.assert_allclose(nan_cov, 0.04 * np.eye(2))
    assert _ellipse_polyline([0.0], np.eye(2)) is None
    assert _ellipse_polyline([0.0, 0.0], np.zeros((2, 2))) is None
    signed = _qr_stiefel(np.array([[-1.0, 0.0], [0.0, -1.0], [0.0, 0.0]]))
    assert signed[0, 0] >= 0.0 and signed[0, 1] >= 0.0


def test_lens_weight_mass_on_kmeans_and_mppca():
    rng = np.random.default_rng(6)
    X = _l2(rng.normal(size=(14, 5)))
    mass = np.ones(14)
    mass[:4] = 20.0
    with pytest.raises(ValueError, match="uniform or mass"):
        subject_grain_fit(X, cluster_method="kmeans", lens_weight="area")
    with pytest.raises(ValueError, match="requires vq_mass"):
        subject_grain_fit(
            X, cluster_method="kmeans", n_clusters=2, lens_weight="mass"
        )
    with pytest.raises(ValueError, match="vq_mass length"):
        subject_grain_fit(
            X,
            cluster_method="kmeans",
            n_clusters=2,
            lens_weight="mass",
            vq_mass=[1.0],
        )
    kmeans_out = subject_grain_fit(
        X,
        phrases=[f"p{i}" for i in range(14)],
        cluster_method="kmeans",
        n_clusters=2,
        force_refit=True,
        lens_weight="mass",
        vq_mass=mass,
        kmeans_n_init=2,
        seed=0,
    )
    assert np.asarray(kmeans_out[0]).shape == (14, 2)
    mppca_out = subject_grain_fit(
        X,
        phrases=[f"p{i}" for i in range(14)],
        cluster_method="mppca",
        k=2,
        force_refit=True,
        lens_weight="mass",
        vq_mass=mass,
        em_accept=3,
        seed=0,
    )
    R = np.asarray(mppca_out[0], float)
    np.testing.assert_allclose(R.sum(axis=1), 1.0, rtol=1e-5)


def test_kmeans_and_mppca_weight_length_errors():
    from referia.assess.compute.mppca import mppca_fit

    X = _l2(np.random.default_rng(7).normal(size=(8, 4)))
    with pytest.raises(ValueError, match="sample_weight length"):
        fit_kmeans(X, 2, sample_weight=[1.0], n_init=1)
    with pytest.raises(ValueError, match="row_weights length"):
        mppca_fit(X, k=2, sigma2=0.1, seed=0, max_iter=2, n_init=1, row_weights=[1.0])
    with pytest.raises(ValueError, match="positive mass"):
        mppca_fit(
            X, k=1, sigma2=0.1, seed=0, max_iter=1, row_weights=np.zeros(8)
        )
