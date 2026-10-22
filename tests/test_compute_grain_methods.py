"""CIP-0019: sklearn grain methods vs soft MPPCA dispatch."""

import numpy as np
import pytest

from referia.assess.compute.agglomerative import fit_agglomerative
from referia.assess.compute.grain_catalogue import (
    format_topic_tree_markdown,
    one_hot_from_labels,
    topic_keys,
)
from referia.assess.compute.grain_fit import subject_grain_fit
from referia.assess.compute.kmeans import fit_kmeans
from referia.assess.compute.mppca import (
    example_phrases_for_soft_topics,
    mppca_fit,
    subject_grain_propose_split,
    subject_grain_seed_fit,
)
from referia.util.plotly_figures import (
    cluster_dendrogram_plotly_spec,
    cluster_pca_plotly_spec,
)


def _l2(X: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(X, axis=1, keepdims=True)
    return X / np.clip(n, 1e-12, None)


def test_one_hot_from_labels_rows_sum_to_one():
    R = one_hot_from_labels([0, 2, 1, 2], n_clusters=3)
    assert R.shape == (4, 3)
    np.testing.assert_array_equal(R.sum(axis=1), np.ones(4))
    assert set(np.unique(R)) <= {0.0, 1.0}


def test_format_topic_tree_markdown_flat_parents():
    keys = topic_keys(2)
    md = format_topic_tree_markdown(
        keys,
        {keys[0]: "A", keys[1]: "B"},
        {keys[0]: None, keys[1]: None},
        keys[0],
        responsibilities=np.eye(2),
    )
    assert "A" in md and "B" in md
    assert "<table>" in md


def test_kmeans_one_hot_catalogue_shape():
    rng = np.random.default_rng(0)
    X = _l2(rng.normal(size=(20, 8)))
    packed = fit_kmeans(X, n_clusters=3, seed=0, n_init=2)
    R = packed["responsibilities"]
    assert R.shape == (20, 3)
    np.testing.assert_allclose(R.sum(axis=1), 1.0)
    assert set(np.unique(np.round(R))) <= {0.0, 1.0}
    assert packed["means"].shape == (3, 8)


def test_agglomerative_average_cosine_one_hot():
    rng = np.random.default_rng(1)
    X = _l2(rng.normal(size=(16, 6)))
    packed = fit_agglomerative(X, n_clusters=4, linkage="average", metric="cosine")
    R = packed["responsibilities"]
    assert R.shape == (16, 4)
    np.testing.assert_allclose(R.sum(axis=1), 1.0)
    assert packed["children"].shape == (15, 2)
    assert packed["distances"].shape == (15,)


def test_agglomerative_ward_cosine_raises():
    rng = np.random.default_rng(2)
    X = _l2(rng.normal(size=(10, 4)))
    with pytest.raises(ValueError, match="Ward linkage requires euclidean"):
        fit_agglomerative(X, n_clusters=2, linkage="ward", metric="cosine")


def test_dispatch_mppca_stays_soft():
    rng = np.random.default_rng(3)
    # Overlapping blobs in ambient space (not L2) so EM keeps fractional R.
    a = rng.normal(loc=0.0, scale=0.4, size=(12, 8))
    b = rng.normal(loc=0.0, scale=0.4, size=(12, 8))
    a[:, 0] += 0.6
    b[:, 0] -= 0.6
    X = np.vstack([a, b])
    out = subject_grain_fit(
        X,
        phrases=[f"p{i}" for i in range(len(X))],
        cluster_method="mppca",
        k=2,
        force_refit=True,
        em_accept=8,
        seed=0,
        sigma2=0.2,
    )
    R = np.asarray(out[0], float)
    assert R.shape == (24, 2)
    np.testing.assert_allclose(R.sum(axis=1), 1.0, rtol=1e-5)
    assert np.any((R > 0.05) & (R < 0.95))


def test_dispatch_kmeans_writes_one_hot_r():
    rng = np.random.default_rng(4)
    X = _l2(rng.normal(size=(18, 5)))
    out = subject_grain_fit(
        X,
        phrases=[f"p{i}" for i in range(18)],
        cluster_method="kmeans",
        n_clusters=3,
        force_refit=True,
        seed=0,
        kmeans_n_init=2,
    )
    R = np.asarray(out[0], float)
    assert R.shape[1] == 3
    assert set(np.unique(np.round(R))) <= {0.0, 1.0}
    spec = out[2]
    assert spec and "data" in spec
    assert any("phrase" in (pt.get("customdata") or [{}])[0] for pt in spec["data"] if pt.get("customdata"))


def test_propose_on_kmeans_raises():
    rng = np.random.default_rng(5)
    X = _l2(rng.normal(size=(12, 4)))
    packed = fit_kmeans(X, n_clusters=2, seed=0, n_init=1)
    with pytest.raises(ValueError, match="MPPCA-only"):
        subject_grain_propose_split(
            X,
            packed["responsibilities"],
            phrases=[f"p{i}" for i in range(12)],
            cluster_method="kmeans",
        )


def test_cluster_pca_customdata_phrase():
    rng = np.random.default_rng(6)
    X = _l2(rng.normal(size=(10, 5)))
    R = one_hot_from_labels(np.arange(10) % 2, n_clusters=2)
    spec = cluster_pca_plotly_spec(X, R, focus=0, phrases=[f"ph {i}" for i in range(10)])
    assert spec is not None
    phrases = [cd["phrase"] for tr in spec["data"] for cd in tr["customdata"]]
    assert any(p.startswith("ph ") for p in phrases)


def test_dendrogram_has_n_minus_one_joins():
    rng = np.random.default_rng(7)
    X = _l2(rng.normal(size=(9, 4)))
    packed = fit_agglomerative(X, n_clusters=3, linkage="ward", metric="euclidean")
    spec = cluster_dendrogram_plotly_spec(
        packed["children"],
        packed["distances"],
        n=9,
    )
    assert spec is not None
    xs = spec["data"][0]["x"]
    n_joins = sum(1 for v in xs if v is None)
    assert n_joins == 8


def test_unknown_method_raises():
    rng = np.random.default_rng(8)
    X = _l2(rng.normal(size=(6, 3)))
    with pytest.raises(ValueError, match="cluster_method"):
        subject_grain_fit(X, cluster_method="gmm", force_refit=True)


def test_seed_fit_still_skips_when_r_present():
    R = np.ones((5, 1))
    out = subject_grain_seed_fit(
        np.zeros((5, 3)),
        responsibilities=R,
        force_refit=False,
    )
    np.testing.assert_array_equal(out[0], R)


def test_one_hot_exemplars_cap_at_n_top():
    phrases = [f"p{i}" for i in range(12)]
    R = one_hot_from_labels([0] * 6 + [1] * 6, n_clusters=2)
    units = example_phrases_for_soft_topics(phrases, R, n_top=3, n_sample=0)
    assert len(units) == 2
    for unit in units:
        assert len(unit["examples"]) == 3


def test_mppca_fit_still_returns_soft_rows():
    rng = np.random.default_rng(9)
    X = _l2(rng.normal(size=(15, 6)))
    fit = mppca_fit(X, k=2, sigma2=0.1, seed=0, max_iter=5, n_init=1)
    R = fit["responsibilities"]
    np.testing.assert_allclose(R.sum(axis=1), 1.0, rtol=1e-5)
