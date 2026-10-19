"""Tests for soft MPPCA topic fit and related Assess helpers."""

import numpy as np
import pytest

from referia.assess.compute.mppca import (
    DEFAULT_TOPIC_SIGMA2,
    DEFAULT_TOPIC_SIGMA2_GRID,
    fit_weighted_ppca,
    mppca_fit,
    profile_topic_sigma2,
    propose_split,
    rebuild_uq_by_topic,
    responsibilities_to_labels,
    subject_grain_confirm_split,
    subject_grain_propose_split,
    subject_grain_undo_split,
    topic_keys,
)
from referia.assess.compute.topic_naming import (
    subject_grain_apply_focus_label,
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

    monkeypatch.setattr(np.linalg, "svd", boom)
    fit = fit_weighted_ppca(X, w, sigma2=0.1)
    assert fit["q"] == 0
    assert fit["U_q"].shape == (8, 0)
    assert calls["n"] >= 1
    out = mppca_fit(X, k=3, sigma2=0.1, seed=0, max_iter=5, n_init=2)
    assert out["responsibilities"].shape == (30, 3)


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
        seed=3,
    )
    (
        uq_spec,
        uq_by_topic,
        keys,
        R_list,
        focus,
        labels,
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
    assert pending["kind"] == "split" and pending["accepted"] is False
    assert pending["k_before"] == 2 and pending["k_after"] == 3
    assert isinstance(pending.get("planes_after_accept"), dict)
    assert isinstance(undo, dict) and undo["topic_keys"] == ["T0", "T1"]
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
    assert restored[6] is None and restored[7] is None
    # Undo returns 8 catalogue fields — never a sigma2 write slot.
    assert len(restored) == 8


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
    undo = packed[7]
    live_sigma2 = 0.25
    restored = subject_grain_undo_split(
        undo,
        embeddings=X.tolist(),
        phrases=phrases,
        sigma2=live_sigma2,
    )
    uq_spec, uq_by_topic, keys, R, focus, labels, pend, snap = restored
    assert pend is None and snap is None
    assert keys == ["T0", "T1"]
    assert len(R) == len(X)
    assert focus in keys
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
    applied = subject_grain_apply_focus_label({"T0": "old"}, "T0", "Cycle parking")
    assert applied == {"T0": "Cycle parking"}


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
    out = comp._subject_grain_name_focus_topic(
        phrases=phrases,
        responsibilities=R,
        focus_topic="T0",
        topic_labels={"T0": "old", "T1": "other"},
        label_prompt=_TEST_LABEL_PROMPT,
        label_model="stub",
    )
    assert out["T0"] != "old"
    assert out["T1"] == "other"
    assert "label_model" not in out


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
    out = comp._subject_grain_name_focus_topic(
        phrases=phrases,
        responsibilities=[[0.9, 0.1], [0.8, 0.2]],
        focus_topic="T0",
        topic_labels={"T0": "old"},
        label_prompt=_TEST_LABEL_PROMPT,
        label_model="gpt-4o-mini",
    )
    assert out["T0"] == "Municipal cycling"
