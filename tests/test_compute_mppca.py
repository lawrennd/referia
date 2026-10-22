"""Tests for soft MPPCA topic fit and related Assess helpers."""

import numpy as np
import pytest

from referia.assess.compute.mppca import (
    DEFAULT_TOPIC_SIGMA2,
    DEFAULT_TOPIC_SIGMA2_GRID,
    DENSE_CHEAP_SIDE_MAX,
    component_local_plane,
    fit_weighted_ppca,
    mppca_fit,
    profile_topic_sigma2,
    propose_split,
    rebuild_uq_by_topic,
    responsibilities_to_labels,
    subject_grain_confirm_split,
    subject_grain_propose_split,
    subject_grain_seed_fit,
    subject_grain_undo_split,
    topic_keys,
    weighted_leading_ppca,
)
from referia.assess.compute.topic_naming import (
    subject_grain_apply_focus_label,
    subject_grain_keys_needing_names,
    subject_grain_parse_label_reply,
    subject_grain_prepare_label,
    subject_grain_stub_label,
)
from referia.util.plotly_figures import (
    local_uq_plotly_spec,
    proposed_split_plotly_spec,
)

_TEST_LABEL_PROMPT = (
    "Summarise this soft topic.\n"
    "Return JSON with keys label and description.\n"
    "Phrases:\n<<PHRASES>>"
)


def _planted_subspace_mixture(
    *,
    n_per: int = 40,
    d: int = 16,
    seed: int = 0,
    overlap: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Three elongated Gaussians in orthogonal 2-D subspaces of R^d.

    ``overlap`` shifts means toward the origin so components mix.
    """
    rng = np.random.default_rng(seed)
    means = np.zeros((3, d))
    means[0, 0] = 3.0 - overlap
    means[1, 2] = 3.0 - overlap
    means[2, 4] = 3.0 - overlap
    Xs = []
    labels = []
    for j in range(3):
        # elongate along two axes starting at 2*j
        axis_a, axis_b = 2 * j, 2 * j + 1
        cov = np.eye(d) * 0.05
        cov[axis_a, axis_a] = 0.8
        cov[axis_b, axis_b] = 0.5
        Xj = rng.multivariate_normal(means[j], cov, size=n_per)
        Xs.append(Xj)
        labels.append(np.full(n_per, j, dtype=int))
    X = np.vstack(Xs)
    y = np.concatenate(labels)
    # shuffle
    perm = rng.permutation(len(X))
    return X[perm], y[perm]


def test_default_topic_sigma2_positive():
    assert DEFAULT_TOPIC_SIGMA2 > 0


def test_fit_weighted_ppca_matches_unweighted_mean():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(20, 5))
    w = np.ones(20)
    fit = fit_weighted_ppca(X, w, sigma2=0.1)
    np.testing.assert_allclose(fit["mu"], X.mean(axis=0), rtol=1e-10)


def test_fit_weighted_ppca_survives_svd_failure(monkeypatch):
    """Ill-conditioned weighted SVD must not raise (CIP-0008)."""
    rng = np.random.default_rng(0)
    X = rng.normal(size=(30, 8))
    w = np.ones(30)
    calls = {"n": 0}

    def boom(*_a, **_k):
        calls["n"] += 1
        raise np.linalg.LinAlgError("SVD did not converge")

    monkeypatch.setattr(
        "referia.assess.compute.mppca._leading_singular_vectors", boom
    )
    fit = fit_weighted_ppca(X, w, sigma2=0.1)
    assert fit["q"] == 0
    assert fit["U_q"].shape == (8, 0)
    assert calls["n"] >= 1
    out = mppca_fit(X, k=3, sigma2=0.1, seed=0, max_iter=5, n_init=2)
    assert out["responsibilities"].shape == (30, 3)


def _subspace_principal_cosines(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    if A.size == 0 and B.size == 0:
        return np.zeros(0)
    if A.size == 0 or B.size == 0:
        return np.zeros(1)
    qa, _ = np.linalg.qr(A)
    qb, _ = np.linalg.qr(B)
    k = min(qa.shape[1], qb.shape[1])
    return np.linalg.svd(qa[:, :k].T @ qb[:, :k], compute_uv=False)


def test_weighted_leading_ppca_matches_full_on_small_dense():
    """Randomized helper agrees with cheap-side eigh on (n, d) ≤ (40, 20)."""
    rng = np.random.default_rng(7)
    n, d, q_true = 40, 20, 4
    W = rng.normal(size=(d, q_true))
    X = rng.normal(size=(n, q_true)) @ W.T + 0.05 * rng.normal(size=(n, d))
    w = np.ones(n)
    w_sum = float(w.sum())
    mu = X.mean(axis=0)
    Xw = X - mu
    full_U, full_lam = weighted_leading_ppca(
        Xw, w_sum, sigma2=0.08, max_q=12, algorithm="full", seed=0
    )
    rand_U, rand_lam = weighted_leading_ppca(
        Xw, w_sum, sigma2=0.08, max_q=12, algorithm="randomized", seed=0
    )
    assert abs(full_U.shape[1] - rand_U.shape[1]) <= 1
    q = min(full_U.shape[1], rand_U.shape[1])
    if q:
        cos = _subspace_principal_cosines(full_U[:, :q], rand_U[:, :q])
        np.testing.assert_allclose(cos, 1.0, atol=0.05)
        np.testing.assert_allclose(full_lam[:q], rand_lam[:q], rtol=0.1, atol=0.05)


def test_fit_weighted_ppca_hot_path_skips_full_numpy_svd(monkeypatch):
    rng = np.random.default_rng(1)
    X = rng.normal(size=(80, 90))
    w = np.ones(len(X))
    assert min(X.shape) > DENSE_CHEAP_SIDE_MAX
    real_svd = np.linalg.svd

    def guarded(a, *args, **kwargs):
        arr = np.asarray(a)
        if min(arr.shape) > DENSE_CHEAP_SIDE_MAX:
            raise AssertionError(
                "np.linalg.svd must not run on the M-step hot path"
            )
        return real_svd(arr, *args, **kwargs)

    monkeypatch.setattr(np.linalg, "svd", guarded)
    fit = fit_weighted_ppca(X, w, sigma2=0.5, max_q=8, algorithm="randomized")
    assert fit["U_q"].shape[0] == 90
    assert fit["q"] <= 8


def test_k1_skips_kmeans(monkeypatch):
    rng = np.random.default_rng(2)
    X = rng.normal(size=(20, 6))

    def boom(*_a, **_k):
        raise AssertionError("k=1 must not run KMeans")

    monkeypatch.setattr("referia.assess.compute.mppca.KMeans", boom)
    out = mppca_fit(X, k=1, sigma2=0.1, seed=0, max_iter=5)
    assert out["responsibilities"].shape == (20, 1)
    np.testing.assert_allclose(out["responsibilities"], 1.0)


def test_object_list_embeddings_stack_to_float_matrix():
    rng = np.random.default_rng(3)
    X = rng.normal(size=(12, 5))
    packed = np.empty(len(X), dtype=object)
    packed[:] = [row.tolist() for row in X]
    fit = mppca_fit(packed, k=1, sigma2=0.2, seed=0)
    assert fit["responsibilities"].shape == (12, 1)
    np.testing.assert_allclose(fit["means"][0], X.mean(axis=0) / np.linalg.norm(X.mean(axis=0)), atol=1e-6)


def test_component_local_plane_skips_full_svd(monkeypatch):
    rng = np.random.default_rng(4)
    X = rng.normal(size=(25, 8))
    w = np.ones(len(X))
    fit = fit_weighted_ppca(X, w, sigma2=10.0)  # q=0 so the plane pads
    assert fit["q"] == 0

    real_svd = np.linalg.svd

    def guarded(a, *args, **kwargs):
        arr = np.asarray(a)
        if min(arr.shape) > 2:
            raise AssertionError(
                "component_local_plane must not call np.linalg.svd"
            )
        return real_svd(arr, *args, **kwargs)

    monkeypatch.setattr(np.linalg, "svd", guarded)
    plane = component_local_plane(X, w, fit, q_viz=2)
    assert plane is not None
    mu, U, scales, q_model = plane
    assert U.shape == (8, 2)
    assert q_model == 0


def test_draghi_shaped_k1_mstep_is_fast():
    """One k=1 M-step on a 1028 × 3072 low-rank corpus stays on CPU budget."""
    rng = np.random.default_rng(5)
    n, d, q_true = 1028, 3072, 12
    factors = rng.normal(size=(n, q_true))
    loading = rng.normal(size=(q_true, d))
    X = factors @ loading + 0.01 * rng.normal(size=(n, d))
    w = np.ones(n)
    import time

    t0 = time.perf_counter()
    fit = fit_weighted_ppca(
        X, w, sigma2=0.05, max_q=24, algorithm="randomized", seed=0
    )
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0, f"k=1 M-step took {elapsed:.3f}s"
    assert fit["U_q"].shape[0] == d
    assert 1 <= fit["q"] <= 24
    out = mppca_fit(
        X, k=1, sigma2=0.05, seed=0, max_iter=5, max_q=24, algorithm="randomized"
    )
    assert out["n_iter"] == 0
    assert out["responsibilities"].shape == (n, 1)


def test_mppca_responsibilities_row_stochastic():
    X, _ = _planted_subspace_mixture(seed=2)
    out = mppca_fit(X, k=3, sigma2=0.1, seed=2, max_iter=30)
    R = out["responsibilities"]
    assert R.shape == (X.shape[0], 3)
    assert np.all(R >= 0)
    np.testing.assert_allclose(R.sum(axis=1), 1.0, atol=1e-8)
    assert out["sigma2"] == pytest.approx(0.1)
    assert out["means"].shape == (3, X.shape[1])
    # L2-normalised means by default
    norms = np.linalg.norm(out["means"], axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-8)


def test_mppca_deterministic_given_seed():
    X, _ = _planted_subspace_mixture(seed=3)
    a = mppca_fit(X, k=3, sigma2=0.1, seed=3, max_iter=20)
    b = mppca_fit(X, k=3, sigma2=0.1, seed=3, max_iter=20)
    np.testing.assert_allclose(a["responsibilities"], b["responsibilities"], atol=1e-10)
    np.testing.assert_allclose(a["means"], b["means"], atol=1e-10)


def test_mppca_recovers_separated_components():
    X, y_true = _planted_subspace_mixture(seed=4, overlap=0.0)
    out = mppca_fit(X, k=3, sigma2=0.15, seed=4, max_iter=40)
    pred = responsibilities_to_labels(out["responsibilities"])
    # Hungarian-free: majority label per true class should be unique
    major = []
    for j in range(3):
        votes = pred[y_true == j]
        major.append(int(np.bincount(votes).argmax()))
    assert len(set(major)) == 3
    # Soft max responsibility high on average when well separated
    assert float(out["responsibilities"].max(axis=1).mean()) > 0.7


def test_mppca_softer_than_hard_under_overlap():
    """Under overlap, mean max-responsibility should be < 1 (soft mass shared)."""
    X, _ = _planted_subspace_mixture(seed=5, overlap=2.2, n_per=50)
    out = mppca_fit(X, k=3, sigma2=0.5, seed=5, max_iter=40)
    mean_max = float(out["responsibilities"].max(axis=1).mean())
    assert mean_max < 0.999
    assert mean_max > 1.0 / 3.0


def test_responsibilities_to_labels_argmax():
    R = np.array([[0.1, 0.7, 0.2], [0.9, 0.05, 0.05]])
    assert list(responsibilities_to_labels(R)) == [1, 0]


def test_responsibilities_to_labels_zero_row():
    R = np.array([[0.0, 0.0], [0.6, 0.4]])
    assert list(responsibilities_to_labels(R)) == [-1, 0]


def test_mppca_rejects_bad_sigma2():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(12, 4))
    with pytest.raises(ValueError, match="sigma2"):
        mppca_fit(X, k=2, sigma2=0.0, seed=0)


def _unit_sphere_topics(*, n_per: int = 20, d: int = 64, k: int = 5, seed: int = 0):
    """L2-normalised clusters mimicking embedding geometry."""
    rng = np.random.default_rng(seed)
    centres = rng.normal(size=(k, d))
    centres /= np.linalg.norm(centres, axis=1, keepdims=True)
    Xs = []
    for j in range(k):
        noise = rng.normal(scale=0.08, size=(n_per, d))
        Xj = centres[j] + noise
        Xj /= np.linalg.norm(Xj, axis=1, keepdims=True)
        Xs.append(Xj)
    X = np.vstack(Xs)
    return X[rng.permutation(len(X))]


def test_default_sigma2_keeps_multiple_map_topics_on_sphere():
    """DEFAULT_TOPIC_SIGMA2 must not collapse MAP to one topic on unit sphere."""
    X = _unit_sphere_topics(seed=11)
    out = mppca_fit(X, k=5, seed=11, max_iter=40)  # uses DEFAULT
    labels = responsibilities_to_labels(out["responsibilities"])
    n_nonempty = int(np.bincount(labels, minlength=5).astype(bool).sum())
    assert n_nonempty >= 4
    assert out["sigma2"] == pytest.approx(DEFAULT_TOPIC_SIGMA2)


def test_high_sigma2_collapse_falls_back_to_kmeans_init():
    """When σ² is far above local eigenvalues, recover k-means init (not 1 MAP)."""
    X = _unit_sphere_topics(seed=12, n_per=25, k=6)
    out = mppca_fit(X, k=6, sigma2=1.0, seed=12, max_iter=40)
    assert out.get("collapsed") is True
    labels = responsibilities_to_labels(out["responsibilities"])
    n_nonempty = int(np.bincount(labels, minlength=6).astype(bool).sum())
    assert n_nonempty >= 5
    # Hard init responsibilities are one-hot
    assert np.allclose(out["responsibilities"].max(axis=1), 1.0)


def test_profile_topic_sigma2_avoids_collapse_and_prefers_soft():
    """Profile grid must reject collapsing floors and pick a soft viable σ²."""
    X = _unit_sphere_topics(seed=13, n_per=30, k=5, d=48)
    # Grid includes a known-collapsing high value and safer lower ones
    grid = [1e-3, 1e-2, 5e-2, 1.0]
    prof = profile_topic_sigma2(X, k=5, grid=grid, seed=13, max_iter=30)
    assert prof["selection"] == "softest_noncollapse"
    assert prof["sigma2"] < 1.0
    assert len(prof["curve"]) == len(grid)
    # Chosen fit must keep multiple MAP topics
    labels = responsibilities_to_labels(prof["fit"]["responsibilities"])
    assert int(np.bincount(labels, minlength=5).astype(bool).sum()) >= 3
    # And the chosen σ² should be the largest non-collapsing on the curve
    viable = [
        float(d["sigma2"])
        for d in prof["curve"]
        if (not d["collapsed"]) and int(d["n_map"]) >= 3 and float(d["max_mean_cos"]) <= 0.99
    ]
    assert prof["sigma2"] == max(viable)


def test_default_grid_nonempty():
    assert len(DEFAULT_TOPIC_SIGMA2_GRID) >= 5
    assert min(DEFAULT_TOPIC_SIGMA2_GRID) < DEFAULT_TOPIC_SIGMA2 < max(
        DEFAULT_TOPIC_SIGMA2_GRID
    )


def test_topic_keys():
    assert topic_keys(3) == ["T0", "T1", "T2"]


def test_local_uq_plotly_spec_has_click_customdata():
    """Local U_q figure JSON must carry phrase / topic / responsibilities."""
    X, _ = _planted_subspace_mixture(n_per=25, d=12, seed=21)
    fit = mppca_fit(X, k=3, sigma2=0.05, seed=21, max_iter=40)
    phrases = [f"phrase about topic cluster {i % 3}" for i in range(len(X))]
    spec = local_uq_plotly_spec(
        X,
        fit["responsibilities"],
        focus=0,
        component_fits=fit["component_fits"],
        phrases=phrases,
        sigma2=float(fit["sigma2"]),
    )
    assert spec is not None
    assert "data" in spec and "layout" in spec
    phrase_trace = next(t for t in spec["data"] if t.get("name") == "phrases")
    assert len(phrase_trace["x"]) == len(X)
    # Focus view: uniform solid dark markers (no soft-mass size/opacity).
    assert phrase_trace["marker"]["color"] == "#0b0b0b"
    assert phrase_trace["marker"]["size"] == 5
    assert float(phrase_trace["marker"].get("opacity", 1.0)) == 1.0
    cd0 = phrase_trace["customdata"][0]
    assert "phrase" in cd0 and "topic" in cd0 and "responsibilities" in cd0
    assert set(cd0["responsibilities"]) == {"T0", "T1", "T2"}
    assert abs(sum(cd0["responsibilities"].values()) - 1.0) < 1e-6


def test_propose_split_from_k1_keeps_both_children_populated():
    """Default seed must not leave the second child empty (CIMT-style collapse)."""
    X, _ = _planted_subspace_mixture(n_per=25, d=12, seed=0)
    fit = mppca_fit(X, k=1, sigma2=0.05, seed=0, max_iter=30)
    out = propose_split(X, fit, 0, n_children=2, seed=0, max_iter=20)
    R_new = np.asarray(out["fit"]["responsibilities"], float)
    assert R_new.shape == (len(X), 2)
    sums = R_new.sum(axis=0)
    assert float(sums.min() / sums.sum()) >= 0.15
    n_map = int((np.bincount(R_new.argmax(axis=1), minlength=2) > 0).sum())
    assert n_map == 2
    # Focus on minority child: enough markers above ghost floor.
    minority = int(np.argmin(sums))
    mass = R_new[:, minority]
    assert int((mass > 0.2).sum()) >= 5


def test_propose_split_grows_k_and_rebuilds_planes():
    X, _ = _planted_subspace_mixture(n_per=20, d=12, seed=3)
    fit = mppca_fit(X, k=2, sigma2=0.05, seed=3, max_iter=30)
    out = propose_split(X, fit, 0, n_children=2, seed=3, max_iter=20)
    R_new = out["fit"]["responsibilities"]
    assert R_new.shape[1] == 3
    assert out["dirty"] == [0, 1]
    phrases = [f"p{i}" for i in range(len(X))]
    views = rebuild_uq_by_topic(
        X, R_new, phrases=phrases, sigma2=float(out["fit"]["sigma2"])
    )
    assert set(views) == {"T0", "T1", "T2"}
    packed = subject_grain_propose_split(
        X.tolist(),
        fit["responsibilities"].tolist(),
        phrases=phrases,
        focus_topic="T0",
        sigma2=0.05,
        em_accept=15,
        topic_labels={"T0": "Parent", "T1": "Other"},
        topic_parent={"T0": None, "T1": None},
        seed=3,
    )
    (
        uq_spec,
        uq_by_topic,
        keys,
        R_list,
        focus,
        labels,
        parent_map,
        tree,
        pending,
        undo,
    ) = packed
    assert keys == ["T0", "T1", "T2"]
    assert focus in keys
    assert uq_spec is not None and "data" in uq_spec
    # Overlay: parent (solid) + two child (dashed) ellipse traces.
    line_traces = [
        t for t in uq_spec["data"]
        if t.get("mode") == "lines" and t.get("type") == "scatter"
    ]
    assert len(line_traces) >= 3
    dashes = [t.get("line", {}).get("dash") for t in line_traces]
    assert "solid" in dashes
    assert dashes.count("dash") >= 2
    assert "parent local PC1" in (uq_spec.get("layout") or {}).get("xaxis", {}).get(
        "title", ""
    )
    assert set(uq_by_topic) == set(keys)
    # Pending: figure_source on a child key must still show the overlay.
    assert uq_by_topic[focus] is uq_spec or uq_by_topic[focus] == uq_spec
    assert len(R_list) == len(X)
    assert "«Parent»" in labels[focus] or focus in labels
    # Genealogy: children point at parent label; remapped siblings keep None.
    assert parent_map["T0"] == "Parent" and parent_map["T1"] == "Parent"
    assert parent_map.get("T2") is None
    assert "Other" in tree and "← focus" in tree
    assert pending["kind"] == "split" and pending["accepted"] is False
    assert pending["k_before"] == 2 and pending["k_after"] == 3
    assert isinstance(pending.get("planes_after_accept"), dict)
    assert isinstance(pending.get("history_entry"), dict)
    assert pending["history_entry"]["parent"] == "T0"
    assert isinstance(undo, dict) and undo["topic_keys"] == ["T0", "T1"]
    assert undo.get("topic_parent") == {"T0": None, "T1": None}
    assert "sigma2" not in undo  # controls must not live in the undo snap
    sealed_spec, sealed_map, cleared_pending, cleared_undo = (
        subject_grain_confirm_split(pending)
    )
    assert cleared_pending is None and cleared_undo is None
    assert sealed_spec is not None and "data" in sealed_spec
    # After confirm, child planes are single-topic (one solid ellipse), not overlay.
    sealed_lines = [
        t for t in sealed_spec["data"]
        if t.get("mode") == "lines" and t.get("type") == "scatter"
    ]
    assert len(sealed_lines) == 1
    assert sealed_map[focus] == sealed_spec
    restored = subject_grain_undo_split(
        undo, embeddings=X.tolist(), phrases=phrases, sigma2=0.12
    )
    assert restored[2] == ["T0", "T1"]
    assert restored[6] == {"T0": None, "T1": None}
    assert isinstance(restored[7], str) and "T0" in restored[7]
    assert restored[8] is None and restored[9] is None
    # Undo returns 10 catalogue fields — never a sigma2 write slot.
    assert len(restored) == 10


def test_format_topic_tree_markdown_nests_children():
    from referia.assess.compute.mppca import format_topic_tree_markdown

    R = [
        [0.9, 0.05, 0.05],
        [0.1, 0.8, 0.1],
        [0.1, 0.1, 0.8],
        [0.4, 0.4, 0.2],
    ]
    md = format_topic_tree_markdown(
        ["T0", "T1", "T2"],
        {"T0": "Root", "T1": "Child A", "T2": "Child B"},
        {"T0": None, "T1": "Root", "T2": "Root"},
        focus_topic="T1",
        responsibilities=R,
        mass_threshold=0.05,
    )
    assert "<table>" in md and "<th>Soft n</th>" in md
    # Soft n: T0=4 (all rows > 0.05 on col0); T1=3; T2=3 (0.05 not > τ)
    assert "Root" in md and 'title="T0"' in md
    assert "(<code>T0</code>)" not in md
    assert "**Root**" in md and "(`T0`)" not in md
    assert "<td style=\"text-align:right\">4</td>" in md
    assert "  - **Child A**" in md and "← focus" in md
    assert "  - **Child B**" in md


def test_undo_split_does_not_return_sigma2_and_redraws_at_live_sigma2():
    """Changing σ² then Undo must keep the control; planes use live σ²."""
    X, _ = _planted_subspace_mixture(n_per=18, d=12, seed=5)
    fit = mppca_fit(X, k=2, sigma2=0.05, seed=5, max_iter=25)
    phrases = [f"p{i}" for i in range(len(X))]
    packed = subject_grain_propose_split(
        X.tolist(),
        fit["responsibilities"].tolist(),
        phrases=phrases,
        focus_topic="T0",
        sigma2=0.05,
        em_accept=12,
        seed=5,
    )
    undo = packed[9]
    live_sigma2 = 0.25
    restored = subject_grain_undo_split(
        undo,
        embeddings=X.tolist(),
        phrases=phrases,
        sigma2=live_sigma2,
    )
    (
        uq_spec,
        uq_by_topic,
        keys,
        R,
        focus,
        labels,
        parent_map,
        tree,
        pend,
        snap,
    ) = restored
    assert pend is None and snap is None
    assert keys == ["T0", "T1"]
    assert len(R) == len(X)
    assert focus in keys
    assert set(parent_map) == set(keys)
    assert isinstance(tree, str)
    assert uq_spec is not None and focus in uq_by_topic
    # No sigma2 in the return tuple (would have been index 6 under old API).
    assert not isinstance(pend, float)


def test_proposed_split_plotly_spec_parent_and_children():
    X, _ = _planted_subspace_mixture(n_per=20, d=12, seed=9)
    fit = mppca_fit(X, k=1, sigma2=0.05, seed=9, max_iter=30)
    out = propose_split(X, fit, 0, n_children=2, seed=9, max_iter=20)
    spec = proposed_split_plotly_spec(
        X,
        parent_mass=out["parent_mass"],
        parent_component_fit=out["parent_component_fit"],
        child_component_fits=out["local_fit"]["component_fits"],
        responsibilities=out["fit"]["responsibilities"],
        phrases=[f"p{i}" for i in range(len(X))],
        child_labels=["a", "b"],
        parent_label="Root",
        sigma2=float(out["fit"]["sigma2"]),
    )
    assert spec is not None
    phrase_trace = next(t for t in spec["data"] if t.get("name") == "phrases")
    # Proposal ink is the child ellipses — markers stay uniform solid dark.
    assert phrase_trace["marker"]["color"] == "#0b0b0b"
    assert phrase_trace["marker"]["size"] == 5
    assert float(phrase_trace["marker"].get("opacity", 1.0)) == 1.0
    lines = [t for t in spec["data"] if t.get("mode") == "lines"]
    assert any("parent" in str(t.get("name", "")).lower() for t in lines)
    assert sum(1 for t in lines if t.get("line", {}).get("dash") == "dash") == 2


def test_name_relabels_pending_plotly_overlay(monkeypatch):
    """Name must rewrite baked (unnamed…) labels on the pending plot overlay."""
    from referia.assess import compute as compute_mod
    from referia.util.plotly_figures import relabel_proposed_split_plotly_spec

    X, _ = _planted_subspace_mixture(n_per=20, d=12, seed=11)
    fit = mppca_fit(X, k=1, sigma2=0.05, seed=11, max_iter=30)
    out = propose_split(X, fit, 0, n_children=2, seed=11, max_iter=20)
    unnamed = ["«Topic 0» → (unnamed 0)", "«Topic 0» → (unnamed 1)"]
    spec = proposed_split_plotly_spec(
        X,
        parent_mass=out["parent_mass"],
        parent_component_fit=out["parent_component_fit"],
        child_component_fits=out["local_fit"]["component_fits"],
        child_labels=unnamed,
        parent_label="Topic 0",
        sigma2=float(out["fit"]["sigma2"]),
    )
    assert spec is not None
    assert any("(unnamed" in str(t.get("name", "")) for t in spec["data"])

    replies = [
        '{"label": "Cycle lanes", "description": "Infra."}',
        '{"label": "Bike parking", "description": "Secure."}',
    ]

    class _Mgr:
        def call(self, **kwargs):
            return replies.pop(0)

    monkeypatch.setattr(compute_mod, "LLM_AVAILABLE", True)
    monkeypatch.setattr(compute_mod, "get_llm_manager", lambda _cfg=None: _Mgr())

    comp = compute_mod.Compute(type("Iface", (dict,), {})(llm={}))
    labels, parent, tree, uq, uq_map, pending = (
        comp._subject_grain_name_focus_topic(
            phrases=[f"p{i}" for i in range(len(X))],
            responsibilities=out["fit"]["responsibilities"],
            focus_topic="T0",
            topic_labels={"T0": unnamed[0], "T1": unnamed[1]},
            topic_parent={"T0": "Topic 0", "T1": "Topic 0"},
            topic_keys=["T0", "T1"],
            label_prompt=_TEST_LABEL_PROMPT,
            label_model="gpt-4o-mini",
            pending_proposal={
                "kind": "split",
                "parent": "T0",
                "parent_label": "Topic 0",
                "children": ["T0", "T1"],
                "focus": "T0",
            },
            uq_spec=spec,
            uq_by_topic={"T0": spec, "T1": spec},
        )
    )
    assert labels["T0"] == "Cycle lanes"
    assert labels["T1"] == "Bike parking"
    assert isinstance(uq, dict)
    names = [str(t.get("name", "")) for t in uq["data"]]
    assert any("Cycle lanes" in n for n in names)
    assert any("Bike parking" in n for n in names)
    assert not any("(unnamed" in n for n in names)
    assert uq_map["T0"] is uq and uq_map["T1"] is uq
    # Direct helper also rewrites title.
    relabelled = relabel_proposed_split_plotly_spec(
        spec, child_labels=["A", "B"], parent_label="Root"
    )
    title = relabelled["layout"]["title"]["text"]
    assert "Root" in title and "(unnamed" not in title


def test_prepare_label_fills_phrases_placeholder():
    phrases = [
        "Safe cycle lanes near schools reduce conflict with cars.",
        "Secure bike parking at stations encourages commuting.",
        "Narrow paths leave cargo bikes nowhere to pass.",
    ]
    R = np.array(
        [
            [0.9, 0.1],
            [0.85, 0.15],
            [0.2, 0.8],
        ],
        dtype=float,
    )
    prompt, exemplars, focus = subject_grain_prepare_label(
        phrases,
        R,
        focus_topic="T0",
        label_prompt=_TEST_LABEL_PROMPT,
        n_exemplars=2,
    )
    assert focus == "T0"
    assert "<<PHRASES>>" not in prompt
    assert any("cycle lanes" in e for e in exemplars)
    assert "- Safe cycle lanes" in prompt


def test_parse_label_reply_json_and_stub_fallback():
    assert (
        subject_grain_parse_label_reply(
            '{"label": "Cycle parking", "description": "Stations."}',
            ["Secure bike parking at stations"],
        )
        == "Cycle parking"
    )
    stub = subject_grain_stub_label(
        ["Secure bike parking at stations encourages commuting."]
    )
    assert "Secure" in stub or "bike" in stub.lower()
    labels, parent, tree = subject_grain_apply_focus_label(
        {"T0": "old", "T1": "kid"},
        "T0",
        "Cycle parking",
        topic_parent={"T0": None, "T1": "old"},
        topic_keys=["T0", "T1"],
    )
    assert labels == {"T0": "Cycle parking", "T1": "kid"}
    assert parent["T1"] == "Cycle parking"
    assert "Cycle parking" in tree and "kid" in tree


def test_parse_label_reply_alternate_keys_and_plaintext():
    """Accept title/name keys, embedded JSON, and first-line plaintext."""
    assert (
        subject_grain_parse_label_reply(
            'Here: {"title": "Station parking", "description": "x"}',
            ["Secure bike parking"],
        )
        == "Station parking"
    )
    assert (
        subject_grain_parse_label_reply(
            '{"name": "School lanes"}',
            ["Safe cycle lanes"],
        )
        == "School lanes"
    )
    assert (
        subject_grain_parse_label_reply(
            "Plain topic title\nmore prose",
            ["Secure bike parking"],
        )
        == "Plain topic title"
    )
    # Empty / unusable → stub from exemplars
    stubbed = subject_grain_parse_label_reply("", ["Secure bike parking at stations"])
    assert stubbed
    assert stubbed != ""


def test_provisional_label_edge_cases():
    from referia.assess.compute.topic_naming import (
        _is_provisional_label,
        _short_parent_for_placeholder,
    )

    assert _is_provisional_label("", "T0") is True
    assert _is_provisional_label("T0", "T0") is True  # bare catalogue key
    assert _is_provisional_label("T3") is True
    assert _is_provisional_label("Named topic", "T0") is False
    assert _short_parent_for_placeholder("", None) == "parent"
    assert _short_parent_for_placeholder("«?» → (unnamed 0)", None) == "parent"


def test_clip_label_falls_back_when_suffix_too_long():
    """If (unnamed N) alone nearly fills the budget, clip the whole string."""
    from referia.util.plotly_figures import _clip_label

    long = "«Very Long Parent Name That Will Not Fit» → (unnamed 0)"
    out = _clip_label(long, n=12)
    assert out.endswith("…")
    assert len(out) <= 12


def test_name_focus_topic_stub_via_compute(monkeypatch):
    """Populate path: stub model must not require an API key."""
    from referia.assess import compute as compute_mod

    class _Iface(dict):
        pass

    iface = _Iface(llm={})
    comp = compute_mod.Compute(iface)
    phrases = [
        "Safe cycle lanes near schools reduce conflict with cars.",
        "Secure bike parking at stations encourages commuting.",
    ]
    R = [[0.9, 0.1], [0.8, 0.2]]
    labels, parent, tree, uq, uq_map, pending = (
        comp._subject_grain_name_focus_topic(
            phrases=phrases,
            responsibilities=R,
            focus_topic="T0",
            topic_labels={"T0": "old", "T1": "other"},
            topic_parent={"T0": None, "T1": None},
            topic_keys=["T0", "T1"],
            label_prompt=_TEST_LABEL_PROMPT,
            label_model="stub",
        )
    )
    assert labels["T0"] != "old"
    assert labels["T1"] == "other"
    assert set(parent) == {"T0", "T1"}
    assert isinstance(tree, str) and "T0" in tree
    assert uq is None and uq_map is None and pending is None


def test_name_focus_topic_uses_llm_when_model_set(monkeypatch):
    from referia.assess import compute as compute_mod

    class _Mgr:
        def call(self, **kwargs):
            assert "gpt" in kwargs["model"]
            assert "<<PHRASES>>" not in kwargs["prompt"]
            return '{"label": "Municipal cycling", "description": "Infrastructure."}'

    monkeypatch.setattr(compute_mod, "LLM_AVAILABLE", True)
    monkeypatch.setattr(compute_mod, "get_llm_manager", lambda _cfg=None: _Mgr())

    class _Iface(dict):
        pass

    comp = compute_mod.Compute(_Iface(llm={}))
    phrases = [
        "Safe cycle lanes near schools reduce conflict with cars.",
        "Secure bike parking at stations encourages commuting.",
    ]
    labels, parent, tree, *_ = comp._subject_grain_name_focus_topic(
        phrases=phrases,
        responsibilities=[[0.9, 0.1], [0.8, 0.2]],
        focus_topic="T0",
        topic_labels={"T0": "old"},
        topic_parent={"T0": None},
        topic_keys=["T0"],
        label_prompt=_TEST_LABEL_PROMPT,
        label_model="gpt-4o-mini",
    )
    assert labels["T0"] == "Municipal cycling"
    assert "Municipal cycling" in tree


def test_keys_needing_names_includes_unnamed_placeholders():
    keys = subject_grain_keys_needing_names(
        {
            "T0": "Parent",
            "T1": "«Parent» → (unnamed 0)",
            "T2": "«Parent» → (unnamed 1)",
            "T3": "Already named",
        },
        "T1",
        ["T0", "T1", "T2", "T3"],
    )
    assert keys == ["T1", "T2"]


def test_keys_needing_names_includes_topic_n_seeds():
    keys = subject_grain_keys_needing_names(
        {"T0": "Topic 0", "T1": "Already named"},
        "T1",
        ["T0", "T1"],
    )
    # Named focus is skipped; only the provisional seed is queued.
    assert keys == ["T0"]


def test_clip_label_keeps_unnamed_suffix():
    from referia.util.plotly_figures import _clip_label

    a = _clip_label("«Urban Infrastructure and Safety» → (unnamed 0)", 28)
    b = _clip_label("«Urban Infrastructure and Safety» → (unnamed 1)", 28)
    assert a != b
    assert a.endswith("(unnamed 0)")
    assert b.endswith("(unnamed 1)")


def test_short_parent_for_placeholder_does_not_nest():
    from referia.assess.compute.topic_naming import _short_parent_for_placeholder

    assert _short_parent_for_placeholder("Topic 0", "T0") == "Topic 0"
    assert (
        _short_parent_for_placeholder("«Topic 0» → (unnamed 0)", "T0")
        == "Topic 0"
    )
    assert (
        _short_parent_for_placeholder(
            "««Topic 0» → (unnamed 0)» → (unnamed 1)", "T1"
        )
        == "Topic 0"
    )
    assert (
        _short_parent_for_placeholder("Urban bike lanes", "T0")
        == "Urban bike lanes"
    )


def test_propose_does_not_nest_provisional_parent():
    """Splitting an already-provisional child must not nest «…» → (unnamed)."""
    X, _ = _planted_subspace_mixture(n_per=20, d=12, seed=17)
    fit = mppca_fit(X, k=1, sigma2=0.05, seed=17, max_iter=30)
    phrases = [f"p{i}" for i in range(len(X))]
    packed = subject_grain_propose_split(
        X.tolist(),
        fit["responsibilities"].tolist(),
        phrases=phrases,
        focus_topic="T0",
        sigma2=0.05,
        em_accept=15,
        topic_labels={"T0": "«Topic 0» → (unnamed 0)"},
        topic_parent={"T0": None},
        seed=17,
    )
    labels = packed[5]
    pending = packed[8]
    uq_spec = packed[0]
    for lab in labels.values():
        assert "««" not in str(lab)
        # Exactly one arrow-unnamed suffix per child placeholder.
        assert str(lab).count("(unnamed") <= 1
    assert pending["parent_label"] == "Topic 0"
    title = (uq_spec.get("layout") or {}).get("title") or {}
    title_text = title.get("text", "") if isinstance(title, dict) else str(title)
    assert "«Topic 0»" in title_text
    assert "««" not in title_text


def test_propose_via_compute_names_children_when_not_stub(monkeypatch):
    """Propose with a live label_model must not leave (unnamed) children."""
    from referia.assess import compute as compute_mod

    replies = [
        '{"label": "Cycle lanes", "description": "Infra."}',
        '{"label": "Bike parking", "description": "Secure."}',
    ]

    class _Mgr:
        def call(self, **kwargs):
            return replies.pop(0)

    monkeypatch.setattr(compute_mod, "LLM_AVAILABLE", True)
    monkeypatch.setattr(compute_mod, "get_llm_manager", lambda _cfg=None: _Mgr())

    X, _ = _planted_subspace_mixture(n_per=20, d=12, seed=21)
    fit = mppca_fit(X, k=1, sigma2=0.05, seed=21, max_iter=30)
    phrases = [f"p{i}" for i in range(len(X))]
    comp = compute_mod.Compute(type("Iface", (dict,), {})(llm={}))
    packed = comp._subject_grain_propose_split(
        X.tolist(),
        fit["responsibilities"].tolist(),
        phrases=phrases,
        focus_topic="T0",
        sigma2=0.05,
        em_accept=15,
        topic_labels={"T0": "Topic 0"},
        topic_parent={"T0": None},
        seed=21,
        label_model="gpt-4o-mini",
        label_prompt=_TEST_LABEL_PROMPT,
    )
    labels = packed[5]
    uq_spec = packed[0]
    assert labels["T0"] == "Cycle lanes"
    assert labels["T1"] == "Bike parking"
    assert not any("(unnamed" in str(v) for v in labels.values())
    title = (uq_spec.get("layout") or {}).get("title") or {}
    title_text = title.get("text", "") if isinstance(title, dict) else str(title)
    assert "(unnamed" not in title_text
    names = [str(t.get("name", "")) for t in uq_spec["data"]]
    assert not any("(unnamed" in n for n in names)


def test_propose_via_compute_stub_keeps_unnamed():
    """stub label_model keeps Propose placeholders (offline / bake)."""
    from referia.assess import compute as compute_mod

    X, _ = _planted_subspace_mixture(n_per=16, d=12, seed=23)
    fit = mppca_fit(X, k=1, sigma2=0.05, seed=23, max_iter=25)
    comp = compute_mod.Compute(type("Iface", (dict,), {})(llm={}))
    packed = comp._subject_grain_propose_split(
        X.tolist(),
        fit["responsibilities"].tolist(),
        phrases=[f"p{i}" for i in range(len(X))],
        focus_topic="T0",
        sigma2=0.05,
        em_accept=12,
        topic_labels={"T0": "Topic 0"},
        topic_parent={"T0": None},
        seed=23,
        label_model="stub",
    )
    labels = packed[5]
    assert any("(unnamed" in str(v) for v in labels.values())


def test_name_sanitizes_nested_overlay_parent(monkeypatch):
    """Name must strip nested provisional parents from the plot title."""
    from referia.assess import compute as compute_mod

    X, _ = _planted_subspace_mixture(n_per=20, d=12, seed=19)
    fit = mppca_fit(X, k=1, sigma2=0.05, seed=19, max_iter=30)
    out = propose_split(X, fit, 0, n_children=2, seed=19, max_iter=20)
    nested_parent = "«Topic 0» → (unnamed 0)"
    children = [
        f"«{nested_parent}» → (unnamed 0)",
        f"«{nested_parent}» → (unnamed 1)",
    ]
    spec = proposed_split_plotly_spec(
        X,
        parent_mass=out["parent_mass"],
        parent_component_fit=out["parent_component_fit"],
        child_component_fits=out["local_fit"]["component_fits"],
        child_labels=children,
        parent_label=nested_parent,
        sigma2=float(out["fit"]["sigma2"]),
    )
    replies = [
        '{"label": "Cycle lanes", "description": "Infra."}',
        '{"label": "Bike parking", "description": "Secure."}',
    ]

    class _Mgr:
        def call(self, **kwargs):
            return replies.pop(0)

    monkeypatch.setattr(compute_mod, "LLM_AVAILABLE", True)
    monkeypatch.setattr(compute_mod, "get_llm_manager", lambda _cfg=None: _Mgr())

    comp = compute_mod.Compute(type("Iface", (dict,), {})(llm={}))
    *_, uq, uq_map, pending = comp._subject_grain_name_focus_topic(
        phrases=[f"p{i}" for i in range(len(X))],
        responsibilities=out["fit"]["responsibilities"],
        focus_topic="T0",
        topic_labels={"T0": children[0], "T1": children[1]},
        topic_parent={"T0": None, "T1": None},
        topic_keys=["T0", "T1"],
        label_prompt=_TEST_LABEL_PROMPT,
        label_model="gpt-4o-mini",
        pending_proposal={
            "kind": "split",
            "parent": "T0",
            "parent_label": nested_parent,
            "children": ["T0", "T1"],
            "focus": "T0",
        },
        uq_spec=spec,
        uq_by_topic={"T0": spec, "T1": spec},
    )
    title = uq["layout"]["title"]["text"]
    assert "(unnamed" not in title
    assert "««" not in title
    assert pending["parent_label"] == "Topic 0"
    names = [str(t.get("name", "")) for t in uq["data"]]
    assert not any("(unnamed" in n for n in names)
    assert uq_map["T0"] is uq


def test_name_focus_also_names_unnamed_siblings(monkeypatch):
    """Propose leaves (unnamed) children; Name should fill them in one pass."""
    from referia.assess import compute as compute_mod

    replies_list = [
        '{"label": "Child A", "description": "First."}',
        '{"label": "Child B", "description": "Second."}',
    ]

    class _Mgr:
        def call(self, **kwargs):
            assert "gpt" in kwargs["model"]
            return replies_list.pop(0)
    monkeypatch.setattr(compute_mod, "LLM_AVAILABLE", True)
    monkeypatch.setattr(compute_mod, "get_llm_manager", lambda _cfg=None: _Mgr())

    comp = compute_mod.Compute(type("Iface", (dict,), {})(llm={}))
    phrases = [
        "Safe cycle lanes near schools reduce conflict with cars.",
        "Secure bike parking at stations encourages commuting.",
        "Narrow paths leave cargo bikes nowhere to pass.",
    ]
    R = [[0.1, 0.8, 0.1], [0.1, 0.1, 0.8], [0.1, 0.7, 0.2]]
    labels, parent, tree, *_ = comp._subject_grain_name_focus_topic(
        phrases=phrases,
        responsibilities=R,
        focus_topic="T1",
        topic_labels={
            "T0": "Parent",
            "T1": "«Parent» → (unnamed 0)",
            "T2": "«Parent» → (unnamed 1)",
        },
        topic_parent={"T0": None, "T1": "Parent", "T2": "Parent"},
        topic_keys=["T0", "T1", "T2"],
        label_prompt=_TEST_LABEL_PROMPT,
        label_model="gpt-4o-mini",
    )
    assert labels["T0"] == "Parent"
    assert labels["T1"] == "Child A"
    assert labels["T2"] == "Child B"
    assert "(unnamed" not in tree
    assert "(orphaned)" not in tree
    assert parent["T1"] == "Parent"


def test_name_clears_seed_ghost_parent(monkeypatch):
    """After splitting Topic 0, Name must not leave ← Topic 0 in the tree."""
    from referia.assess import compute as compute_mod

    class _Mgr:
        def call(self, **kwargs):
            return '{"label": "Bike lanes", "description": "Infra."}'

    monkeypatch.setattr(compute_mod, "LLM_AVAILABLE", True)
    monkeypatch.setattr(compute_mod, "get_llm_manager", lambda _cfg=None: _Mgr())

    comp = compute_mod.Compute(type("Iface", (dict,), {})(llm={}))
    labels, parent, tree, *_ = comp._subject_grain_name_focus_topic(
        phrases=["Safe cycle lanes near schools."],
        responsibilities=[[0.6, 0.4]],
        focus_topic="T0",
        topic_labels={
            "T0": "«Topic 0» → (unnamed 0)",
            "T1": "«Topic 0» → (unnamed 1)",
        },
        topic_parent={"T0": "Topic 0", "T1": "Topic 0"},
        topic_keys=["T0", "T1"],
        label_prompt=_TEST_LABEL_PROMPT,
        label_model="gpt-4o-mini",
    )
    assert "Topic 0" not in (parent.get("T0"), parent.get("T1"))
    assert parent["T0"] is None and parent["T1"] is None
    assert "Bike lanes" in labels["T0"] or labels["T0"] == "Bike lanes"
    assert "(orphaned)" not in tree
    assert "← Topic 0" not in tree


def test_ensure_seed_names_titles_provisional_topic_zero(monkeypatch):
    """On open, provisional Topic 0 is named from cluster phrases."""
    from referia.assess import compute as compute_mod

    calls = []

    class _Mgr:
        def call(self, **kwargs):
            calls.append(kwargs)
            return '{"label": "Cycling safety", "description": "Infra."}'

    monkeypatch.setattr(compute_mod, "LLM_AVAILABLE", True)
    monkeypatch.setattr(compute_mod, "get_llm_manager", lambda _cfg=None: _Mgr())

    comp = compute_mod.Compute(type("Iface", (dict,), {})(llm={}))
    labels, parent, tree = comp._subject_grain_ensure_seed_names(
        phrases=[
            "Safe cycle lanes near schools reduce conflict with cars.",
            "Secure bike parking at stations encourages commuting.",
        ],
        responsibilities=[[1.0], [1.0]],
        focus_topic="T0",
        topic_labels={"T0": "Topic 0"},
        topic_parent={"T0": None},
        topic_keys=["T0"],
        label_prompt=_TEST_LABEL_PROMPT,
        label_model="gpt-4.1-mini",
    )
    assert len(calls) == 1
    assert labels["T0"] == "Cycling safety"
    assert "Topic 0" not in tree
    assert parent["T0"] is None


def test_ensure_seed_names_skips_when_already_titled(monkeypatch):
    """Already-named seed must not call the LLM again on open."""
    from referia.assess import compute as compute_mod

    class _Mgr:
        def call(self, **kwargs):
            raise AssertionError("LLM must not run for an already-named seed")

    monkeypatch.setattr(compute_mod, "LLM_AVAILABLE", True)
    monkeypatch.setattr(compute_mod, "get_llm_manager", lambda _cfg=None: _Mgr())

    comp = compute_mod.Compute(type("Iface", (dict,), {})(llm={}))
    labels, parent, tree = comp._subject_grain_ensure_seed_names(
        phrases=["Safe cycle lanes near schools."],
        responsibilities=[[1.0]],
        focus_topic="T0",
        topic_labels={"T0": "Cycling safety"},
        topic_parent={"T0": None},
        topic_keys=["T0"],
        label_prompt=_TEST_LABEL_PROMPT,
        label_model="gpt-4.1-mini",
    )
    assert labels["T0"] == "Cycling safety"
    assert "Cycling safety" in tree
    assert parent["T0"] is None


def test_ensure_seed_names_stub_leaves_topic_zero():
    """stub model keeps Topic 0 — no offline hallucinated title."""
    from referia.assess import compute as compute_mod

    comp = compute_mod.Compute(type("Iface", (dict,), {})(llm={}))
    labels, parent, tree = comp._subject_grain_ensure_seed_names(
        phrases=["Safe cycle lanes near schools."],
        responsibilities=[[1.0]],
        focus_topic="T0",
        topic_labels={"T0": "Topic 0"},
        topic_parent={"T0": None},
        topic_keys=["T0"],
        label_prompt=_TEST_LABEL_PROMPT,
        label_model="stub",
    )
    assert labels["T0"] == "Topic 0"
    assert parent["T0"] is None
    assert "Topic 0" in tree


def test_name_one_topic_surfaces_llm_failure(monkeypatch):
    """LLM exceptions become ComputeError so the populate button can show them."""
    from referia.assess import compute as compute_mod
    from referia.exceptions import ComputeError

    class _Mgr:
        def call(self, **kwargs):
            raise RuntimeError("api down")

    monkeypatch.setattr(compute_mod, "LLM_AVAILABLE", True)
    monkeypatch.setattr(compute_mod, "get_llm_manager", lambda _cfg=None: _Mgr())

    comp = compute_mod.Compute(type("Iface", (dict,), {})(llm={}))
    with pytest.raises(ComputeError, match="LLM naming failed for T0"):
        comp._subject_grain_name_one_topic(
            phrases=["Safe cycle lanes near schools."],
            responsibilities=[[1.0]],
            focus_topic="T0",
            label_prompt=_TEST_LABEL_PROMPT,
            label_model="gpt-4.1-mini",
            n_exemplars=1,
            temperature=0.0,
        )


def test_subject_grain_seed_fit_k1_rows_sum_to_one():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(12, 6))
    X /= np.clip(np.linalg.norm(X, axis=1, keepdims=True), 1e-12, None)
    phrases = [f"phrase {i} about scoring" for i in range(12)]
    packed = subject_grain_seed_fit(
        embeddings=X.tolist(),
        phrases=phrases,
        sigma2=0.05,
        sigma2_mode="fixed",
        k=1,
        em_accept=20,
        force_refit=True,
        seed=0,
    )
    R, uq_by_topic, uq_spec, keys, labels, parent, tree, focus = packed
    R = np.asarray(R, float)
    assert R.shape == (12, 1)
    assert np.allclose(R.sum(axis=1), 1.0)
    assert keys == ["T0"]
    assert focus == "T0"
    assert "T0" in labels
    assert parent["T0"] is None
    assert isinstance(tree, str) and tree
    assert isinstance(uq_by_topic, dict)
    assert isinstance(uq_spec, dict)


def test_subject_grain_seed_fit_skips_when_already_fit():
    existing_R = [[1.0], [1.0]]
    packed = subject_grain_seed_fit(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        phrases=["a", "b"],
        responsibilities=existing_R,
        topic_keys=["T0"],
        topic_labels={"T0": "Privacy"},
        force_refit=False,
    )
    R, _, _, keys, labels, _, _, focus = packed
    assert R == existing_R
    assert keys == ["T0"]
    assert labels["T0"] == "Privacy"
    assert focus == "T0"


def test_subject_grain_seed_fit_registered():
    from referia.assess.compute import Compute

    names = {e["name"] for e in Compute({"input": {}})._compute_functions_list()}
    assert "subject_grain_seed_fit" in names


def test_subject_grain_seed_fit_skip_generates_keys():
    packed = subject_grain_seed_fit(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        responsibilities=[[1.0], [1.0]],
        topic_labels="not-a-dict",
        topic_parent={"T0": None},
        uq_by_topic={"T0": {"ok": True}},
        force_refit=False,
        focus_topic="T0",
    )
    _, uq_map, spec, keys, labels, parent, tree, focus = packed
    assert keys == ["T0"]
    assert labels["T0"] == "Topic 0"
    assert parent["T0"] is None
    assert spec == {"ok": True}
    assert focus == "T0"
    assert isinstance(tree, str)


def test_subject_grain_seed_fit_rejects_1d():
    with pytest.raises(ValueError, match="2-D"):
        subject_grain_seed_fit(embeddings=[1.0, 0.0], force_refit=True)


def test_subject_grain_seed_fit_profile_and_defaults(monkeypatch):
    monkeypatch.setattr(
        "referia.assess.compute.mppca.profile_topic_sigma2",
        lambda *a, **k: {
            "fit": {
                "responsibilities": [[1.0], [1.0]],
                "sigma2": 0.2,
                "component_fits": None,
            },
            "sigma2": 0.2,
        },
    )
    monkeypatch.setattr(
        "referia.assess.compute.mppca.rebuild_uq_by_topic",
        lambda *a, **k: {"T0": {"sigma2": 0.2}},
    )
    packed = subject_grain_seed_fit(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        phrases="one string for both",
        sigma2_mode="profile",
        force_refit=True,
        k=None,
    )
    R, uq_map, spec, keys, *_ = packed
    assert np.asarray(R).shape == (2, 1)
    assert keys == ["T0"]
    assert spec["sigma2"] == 0.2

    monkeypatch.setattr(
        "referia.assess.compute.mppca.mppca_fit",
        lambda *a, **k: {
            "responsibilities": [[1.0], [1.0]],
            "sigma2": 0.01,
            "component_fits": None,
        },
    )
    packed = subject_grain_seed_fit(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        phrases=["only-one"],
        sigma2=None,
        sigma2_mode="fixed",
        force_refit=True,
        k=1,
    )
    assert packed[3] == ["T0"]


def test_subject_grain_seed_fit_invalid_responsibilities_refits(monkeypatch):
    monkeypatch.setattr(
        "referia.assess.compute.mppca.mppca_fit",
        lambda *a, **k: {
            "responsibilities": [[1.0], [1.0]],
            "sigma2": 0.05,
            "component_fits": None,
        },
    )
    monkeypatch.setattr(
        "referia.assess.compute.mppca.rebuild_uq_by_topic",
        lambda *a, **k: {"T0": {"ok": True}},
    )
    packed = subject_grain_seed_fit(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        responsibilities=None,
        force_refit=False,
        k=1,
        sigma2=0.05,
    )
    assert packed[3] == ["T0"]
    packed = subject_grain_seed_fit(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        responsibilities="not-an-array",
        force_refit=False,
        k=1,
        sigma2=0.05,
    )
    assert packed[3] == ["T0"]
    assert packed[2] == {"ok": True}


def test_subject_grain_seed_fit_skip_uses_existing_tree():
    packed = subject_grain_seed_fit(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        responsibilities=[[1.0], [1.0]],
        topic_keys_existing=["T0"],
        topic_tree="kept-tree",
        uq_by_topic={"T0": {"from": "map"}},
        uq_spec="not-a-dict",
        force_refit=False,
    )
    assert packed[6] == "kept-tree"
    assert packed[2] == {"from": "map"}
    empty_map = subject_grain_seed_fit(
        embeddings=[[1.0, 0.0]],
        responsibilities=[[1.0]],
        force_refit=False,
        uq_by_topic=None,
        uq_spec=None,
        topic_tree="t",
    )
    assert empty_map[2] == {}
