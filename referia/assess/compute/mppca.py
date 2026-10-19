"""Mixture of probabilistic PCA for soft phrase→topic geometry.

Pure numpy / scikit-learn model code: fit, responsibilities, propose-split,
and catalogue state updates used by Assess. Figure JSON and LLM prompt text
live elsewhere (``referia.util.plotly_figures``, review config /
``topic_naming``).
"""

from __future__ import annotations

import hashlib
import html
from typing import Any, Optional, Sequence

import numpy as np
from sklearn.cluster import KMeans

__all__ = [
    "DEFAULT_TOPIC_SIGMA2",
    "DEFAULT_TOPIC_SIGMA2_GRID",
    "log_likelihood_ppca",
    "fit_weighted_ppca",
    "mppca_fit",
    "fit_from_responsibilities",
    "propose_split",
    "rebuild_uq_by_topic",
    "subject_grain_propose_split",
    "subject_grain_confirm_split",
    "subject_grain_undo_split",
    "format_topic_tree_markdown",
    "topic_fit_diagnostics",
    "profile_topic_sigma2",
    "responsibilities_to_labels",
    "example_phrases_for_soft_topics",
    "mppca_topics",
    "component_local_plane",
    "topic_keys",
]

def log_likelihood_ppca(
    centroids: np.ndarray, lens_fit: dict, sigma2: float
) -> np.ndarray:
    """Log p(point | PPCA Gaussian), up to a shared constant.

    Uses Σ⁻¹ = U_q diag(1/λ_i) U_qᵀ + (1/σ²)(I − U_q U_qᵀ).
    """
    mu, U_q, lambdas_q, log_det = (
        lens_fit["mu"],
        lens_fit["U_q"],
        lens_fit["lambdas_q"],
        lens_fit["log_det"],
    )
    diff = centroids - mu
    if U_q.size > 0:
        v = diff @ U_q
        projected_sq = (v ** 2 / lambdas_q[None, :]).sum(axis=1)
        residual_sq = (diff ** 2).sum(axis=1) - (v ** 2).sum(axis=1)
    else:
        projected_sq = np.zeros(diff.shape[0])
        residual_sq = (diff ** 2).sum(axis=1)
    mahalanobis_sq = projected_sq + residual_sq / sigma2
    return -0.5 * mahalanobis_sq - 0.5 * log_det

# Fallback single-value floor if profiling is skipped. Prefer
# :func:`profile_topic_sigma2` (short profile grid, then fix).
DEFAULT_TOPIC_SIGMA2: float = 0.01

# Log-spaced candidate floors for one-shot topic σ² profiling.
# Softest non-collapsing value on this grid is selected.
DEFAULT_TOPIC_SIGMA2_GRID: tuple[float, ...] = (
    1e-4,
    3e-4,
    1e-3,
    3e-3,
    1e-2,
    3e-2,
    5e-2,
    1e-1,
    3e-1,
    1.0,
)


def _l2_normalize_rows(X: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    return X / np.clip(norms, eps, None)


def fit_weighted_ppca(
    X: np.ndarray,
    weights: np.ndarray,
    sigma2: float,
) -> dict:
    """PPCA Gaussian for one component under soft (or hard) weights.

    Mean is the responsibility-weighted mean. Covariance uses a weighted
    SVD of centred points (``sqrt(w_i) (x_i - μ)``); eigenvalues are
    ``s² / Σ w``. Factors with eigenvalue > ``sigma2`` are retained.
    """
    X = np.asarray(X, dtype=float)
    w = np.asarray(weights, dtype=float).ravel()
    if X.ndim != 2:
        raise ValueError(f"X must be 2-D, got shape {X.shape}")
    if w.shape[0] != X.shape[0]:
        raise ValueError("weights length must match X rows")
    if sigma2 <= 0:
        raise ValueError(f"sigma2 must be positive, got {sigma2}")

    w_sum = float(w.sum())
    d = X.shape[1]
    if w_sum <= 0:
        mu = np.zeros(d)
        return {
            "mu": mu,
            "U_q": np.zeros((d, 0)),
            "lambdas_q": np.zeros(0),
            "log_det": d * np.log(sigma2),
            "q": 0,
            "weight_sum": 0.0,
        }

    mu = (w[:, None] * X).sum(axis=0) / w_sum
    Xc = X - mu
    # Effective sample size for truncation / empty-component guard
    n_eff = float((w > 0).sum())
    if n_eff < 2:
        return {
            "mu": mu,
            "U_q": np.zeros((d, 0)),
            "lambdas_q": np.zeros(0),
            "log_det": d * np.log(sigma2),
            "q": 0,
            "weight_sum": w_sum,
        }

    sw = np.sqrt(np.clip(w, 0.0, None))
    Xw = sw[:, None] * Xc
    # High-d embeddings + tiny / imbalanced responsibilities can make the
    # weighted matrix ill-conditioned; never let SVD kill the whole EM fit.
    Xw = np.nan_to_num(Xw, nan=0.0, posinf=0.0, neginf=0.0)
    try:
        _, s, Vt = np.linalg.svd(Xw, full_matrices=False)
    except np.linalg.LinAlgError:
        scale = float(np.linalg.norm(Xw)) + 1e-12
        jitter = (1e-8 * scale) * np.random.default_rng(0).standard_normal(Xw.shape)
        try:
            _, s, Vt = np.linalg.svd(Xw + jitter, full_matrices=False)
        except np.linalg.LinAlgError:
            return {
                "mu": mu,
                "U_q": np.zeros((d, 0)),
                "lambdas_q": np.zeros(0),
                "log_det": d * np.log(sigma2),
                "q": 0,
                "weight_sum": w_sum,
            }
    lambdas = (s ** 2) / w_sum
    retain = lambdas > sigma2
    q = int(retain.sum())
    U_q = Vt[retain].T
    lambdas_q = lambdas[retain]
    log_det = float(np.sum(np.log(lambdas_q))) + (d - q) * float(np.log(sigma2))
    return {
        "mu": mu,
        "U_q": U_q,
        "lambdas_q": lambdas_q,
        "log_det": log_det,
        "q": q,
        "weight_sum": w_sum,
    }


def _softmax_rows(log_joint: np.ndarray) -> np.ndarray:
    shifted = log_joint - log_joint.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def mppca_fit(
    X: np.ndarray,
    k: int,
    *,
    sigma2: float = DEFAULT_TOPIC_SIGMA2,
    seed: int = 0,
    max_iter: int = 50,
    tol: float = 1e-5,
    n_init: int = 10,
    normalize_means: bool = True,
) -> dict[str, Any]:
    """Fit a mixture of PPCA components (k-means init, fixed shared σ²).

    Parameters
    ----------
    X :
        ``(n, d)`` phrase embeddings (typically already L2-normalised).
    k :
        Number of topic components.
    sigma2 :
        Shared topic noise floor (fixed for this run).
    seed :
        K-means / reproducibility seed.
    max_iter :
        Maximum EM iterations after initialisation.
    tol :
        Stop when max absolute change in responsibilities falls below this.
    n_init :
        Passed to sklearn ``KMeans``.
    normalize_means :
        If True, L2-normalise returned ``means`` for cosine consumers
        (raw EM means remain in each component fit's ``mu``).

    Returns
    -------
    dict with keys
        ``responsibilities`` : ``(n, k)`` rows sum to 1
        ``means`` : ``(k, d)`` component means (normalised if requested)
        ``pi`` : ``(k,)`` mixing weights
        ``sigma2`` : topic σ² used
        ``n_iter`` : EM iterations performed
        ``component_fits`` : list of per-component PPCA dicts
    """
    X = np.asarray(X, dtype=float)
    if X.ndim != 2:
        raise ValueError(f"X must be 2-D, got shape {X.shape}")
    n, d = X.shape
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if n < k:
        raise ValueError(f"need at least k={k} points, got n={n}")
    if sigma2 <= 0:
        raise ValueError(f"sigma2 must be positive, got {sigma2}")

    # Explicit k-means++ (sklearn default) so topic EM does not silently
    # depend on a library default change.
    km = KMeans(
        n_clusters=k,
        init="k-means++",
        random_state=seed,
        n_init=n_init,
    )
    labels_init = km.fit_predict(X)
    R = np.zeros((n, k), dtype=float)
    R[np.arange(n), labels_init] = 1.0
    pi = R.mean(axis=0)
    R_init = R.copy()

    component_fits: list[dict] = []
    n_iter = 0
    collapsed = False
    for n_iter in range(1, max_iter + 1):
        component_fits = [
            fit_weighted_ppca(X, R[:, j], sigma2) for j in range(k)
        ]
        log_lik = np.column_stack(
            [log_likelihood_ppca(X, fit, sigma2) for fit in component_fits]
        )
        # Empty components: zero prior mass → -inf joint
        log_pi = np.log(np.clip(pi, 1e-300, None))
        for j, fit in enumerate(component_fits):
            if fit.get("weight_sum", 0.0) <= 0:
                log_pi[j] = -np.inf
        log_joint = log_lik + log_pi[None, :]
        R_new = _softmax_rows(log_joint)
        pi = R_new.mean(axis=0)
        delta = float(np.max(np.abs(R_new - R)))
        R = R_new
        if delta < tol:
            break

    # Final M-step so returned fits match responsibilities
    component_fits = [fit_weighted_ppca(X, R[:, j], sigma2) for j in range(k)]
    means = np.vstack([fit["mu"] for fit in component_fits])
    if normalize_means:
        means = _l2_normalize_rows(means)

    # Guard: isotropic collapse (all q=0 + means coincide) leaves one MAP topic.
    # Fall back to k-means init hard responsibilities + member means.
    map_sizes = np.bincount(np.argmax(R, axis=1), minlength=k)
    if normalize_means and k >= 2:
        cos = means @ means.T
        np.fill_diagonal(cos, 0.0)
        max_mean_cos = float(cos.max()) if cos.size else 0.0
    else:
        max_mean_cos = 0.0
    if int((map_sizes > 0).sum()) <= 1 or max_mean_cos > 0.999:
        collapsed = True
        R = R_init
        pi = R.mean(axis=0)
        component_fits = [fit_weighted_ppca(X, R[:, j], sigma2) for j in range(k)]
        means = np.vstack([fit["mu"] for fit in component_fits])
        if normalize_means:
            means = _l2_normalize_rows(means)

    return {
        "responsibilities": R,
        "means": means,
        "pi": pi,
        "sigma2": float(sigma2),
        "n_iter": int(n_iter),
        "component_fits": component_fits,
        "seed": int(seed),
        "k": int(k),
        "collapsed": collapsed,
    }


def topic_fit_diagnostics(fit: dict[str, Any]) -> dict[str, float | int | bool]:
    """Summarise whether an MPPCA fit separated topics or collapsed."""
    R = np.asarray(fit["responsibilities"], dtype=float)
    means = np.asarray(fit["means"], dtype=float)
    k = int(fit.get("k", R.shape[1]))
    labels = np.argmax(R, axis=1)
    map_sizes = np.bincount(labels, minlength=k)
    n_map = int((map_sizes > 0).sum())
    if means.shape[0] >= 2:
        cos = means @ means.T
        np.fill_diagonal(cos, 0.0)
        max_mean_cos = float(cos.max()) if cos.size else 0.0
    else:
        max_mean_cos = 0.0
    # Shannon entropy of each responsibility row
    eps = 1e-12
    ent = -(R * np.log(R + eps)).sum(axis=1)
    q_vals = [int(f.get("q", 0)) for f in fit.get("component_fits", [])]
    # k=1: a single MAP topic is the intended Assess entry, not collapse.
    collapsed = bool(fit.get("collapsed", False)) or (
        (k >= 2 and n_map <= 1) or max_mean_cos > 0.999
    )
    return {
        "n_map": n_map,
        "max_mean_cos": max_mean_cos,
        "mean_max_resp": float(R.max(axis=1).mean()),
        "mean_entropy": float(ent.mean()),
        "mean_q": float(np.mean(q_vals)) if q_vals else 0.0,
        "collapsed": collapsed,
        "sigma2": float(fit["sigma2"]),
    }


def profile_topic_sigma2(
    X: np.ndarray,
    k: int,
    *,
    grid: Optional[Sequence[float]] = None,
    seed: int = 0,
    max_iter: int = 50,
    tol: float = 1e-5,
    n_init: int = 10,
    normalize_means: bool = True,
    min_map_fraction: float = 0.5,
) -> dict[str, Any]:
    r"""Sweep topic σ² and pick the softest floor that does not collapse.

    Topic σ² is profiled once per analysis config, then held fixed. Among
    grid values whose fit keeps enough MAP topics and separated means,
    choose the **largest** σ² (softest / fewest factors).

    Returns
    -------
    dict with ``sigma2``, ``fit`` (full :func:`mppca_fit` at the choice),
    ``curve`` (list of diagnostics per grid point), ``selection``.
    """
    grid_vals = list(grid) if grid is not None else list(DEFAULT_TOPIC_SIGMA2_GRID)
    if not grid_vals:
        raise ValueError("topic σ² grid must be non-empty")
    k = int(k)
    # k=1 (CIP-000A Assess entry): no multi-topic collapse signal — use the
    # package default floor (softest-on-grid would pick ~1.0 and wipe MAP grain).
    if k == 1:
        s2 = float(DEFAULT_TOPIC_SIGMA2)
        fit = mppca_fit(
            X,
            1,
            sigma2=s2,
            seed=seed,
            max_iter=max_iter,
            tol=tol,
            n_init=n_init,
            normalize_means=normalize_means,
        )
        diag = topic_fit_diagnostics(fit)
        return {
            "sigma2": s2,
            "fit": fit,
            "curve": [diag],
            "selection": "k1_default_floor",
            "min_map": 1,
        }

    min_map = max(2, int(np.ceil(min_map_fraction * k)))

    curve: list[dict[str, float | int | bool]] = []
    fits: dict[float, dict[str, Any]] = {}
    for s2 in sorted(float(s) for s in grid_vals):
        fit = mppca_fit(
            X,
            k,
            sigma2=s2,
            seed=seed,
            max_iter=max_iter,
            tol=tol,
            n_init=n_init,
            normalize_means=normalize_means,
        )
        diag = topic_fit_diagnostics(fit)
        curve.append(diag)
        fits[s2] = fit

    viable = [
        d
        for d in curve
        if (not d["collapsed"])
        and int(d["n_map"]) >= min_map
        and float(d["max_mean_cos"]) <= 0.99
    ]
    if viable:
        # Softest non-collapsing: largest σ²
        best = max(viable, key=lambda d: float(d["sigma2"]))
        selection = "softest_noncollapse"
    else:
        # Least-bad: most MAP topics, then lowest mean cosine
        best = max(
            curve,
            key=lambda d: (int(d["n_map"]), -float(d["max_mean_cos"])),
        )
        selection = "fallback_least_collapsed"

    s2_star = float(best["sigma2"])
    return {
        "sigma2": s2_star,
        "fit": fits[s2_star],
        "curve": curve,
        "selection": selection,
        "min_map": min_map,
    }


def responsibilities_to_labels(
    responsibilities: np.ndarray,
    *,
    empty_label: int = -1,
) -> np.ndarray:
    """MAP (hard) topic labels from soft responsibilities.

    **Late view only** — for labelling prompts and human tables. Soft
    responsibilities remain the primary stored state.

    Rows that are all-zero or non-finite receive ``empty_label`` (default
    ``-1``) instead of a spurious argmax onto topic 0.
    """
    R = np.asarray(responsibilities, dtype=float)
    if R.ndim != 2:
        raise ValueError(f"responsibilities must be 2-D, got shape {R.shape}")
    finite = np.isfinite(R)
    R = np.where(finite, R, 0.0)
    row_mass = R.sum(axis=1)
    labels = np.argmax(R, axis=1).astype(int)
    labels[row_mass <= 0] = empty_label
    return labels


def example_phrases_for_soft_topics(
    phrases,
    responsibilities: np.ndarray,
    *,
    n_top: int = 12,
    n_sample: int = 6,
    min_responsibility: float | None = None,
    seed: int = 0,
) -> list[dict]:
    """Membership-threshold exemplars per topic for LLM / report harden views.

    A phrase is eligible for topic ``c`` only when its soft responsibility
    ``R[i, c]`` clears ``min_responsibility``. When that argument is ``None``
    (default), the threshold is ``1/k`` — at least uniform mass under ``k``
    topics. Pass an absolute float to override.

    Among eligible phrases, take the highest-mass ones up to ``n_top`` (a
    *cap*, not a fixed count), then optionally sample up to ``n_sample`` more
    from the remainder (deterministic under ``seed``).

    Topics with no eligible phrases — including near-empty components —
    return an empty example list rather than padding with low-mass text.

    This is a **harden view** for labelling boundaries — not a change to
    the soft topic geometry.
    """
    phrases = list(phrases)
    R = np.asarray(responsibilities, dtype=float)
    if R.ndim != 2:
        raise ValueError(f"responsibilities must be 2-D, got shape {R.shape}")
    if len(phrases) != R.shape[0]:
        raise ValueError(
            f"phrases length {len(phrases)} != responsibilities rows {R.shape[0]}"
        )
    n, k = R.shape
    if k <= 0:
        return []
    if min_responsibility is None:
        thr = 1.0 / float(k)
    else:
        thr = float(min_responsibility)
        if thr < 0 or thr > 1:
            raise ValueError(
                f"min_responsibility must be in [0, 1], got {min_responsibility!r}"
            )
    rng = np.random.default_rng(seed)
    units: list[dict] = []
    for c in range(k):
        mass = R[:, c]
        if float(mass.sum()) <= 0:
            units.append({"cluster": c, "examples": [], "key": f"{c}|empty"})
            continue
        eligible = np.flatnonzero(mass >= thr)
        if eligible.size == 0:
            units.append({"cluster": int(c), "examples": [], "key": f"{c}|below_thr"})
            continue
        # Highest responsibility first among phrases that clear the threshold
        order = eligible[np.argsort(-mass[eligible], kind="mergesort")]
        take_top = min(int(n_top), order.size)
        top_idx = order[:take_top]
        examples = [phrases[i] for i in top_idx]
        rest_idx = order[take_top:]
        if n_sample > 0 and rest_idx.size > 0:
            take = min(int(n_sample), rest_idx.size)
            chosen = rng.choice(rest_idx, size=take, replace=False)
            chosen = chosen[np.argsort(-mass[chosen], kind="mergesort")]
            examples.extend(phrases[i] for i in chosen)
        digest = hashlib.sha256(
            "|".join(str(p) for p in examples).encode("utf-8")
        ).hexdigest()
        key = f"{c}|" + digest[:10]
        units.append({"cluster": int(c), "examples": examples, "key": key})
    return units


def mppca_topics(
    X: np.ndarray,
    k: int,
    seed: int,
    *,
    sigma2: Optional[float] = None,
    profile: bool = True,
) -> dict[str, Any]:
    """Fit soft MPPCA topics; return responsibilities, means, and MAP labels.

    By default (``profile=True``, ``sigma2=None``) runs
    :func:`profile_topic_sigma2` once and uses the softest non-collapsing
    floor. Pass an explicit ``sigma2`` to skip profiling.
    """
    if sigma2 is not None:
        fit = mppca_fit(X, k, sigma2=float(sigma2), seed=seed, n_init=10)
        profile_meta: dict[str, Any] = {"selection": "fixed", "curve": []}
    elif profile:
        prof = profile_topic_sigma2(X, k, seed=seed, n_init=10)
        fit = prof["fit"]
        profile_meta = {
            "selection": prof["selection"],
            "curve": prof["curve"],
            "min_map": prof["min_map"],
        }
    else:
        fit = mppca_fit(X, k, sigma2=DEFAULT_TOPIC_SIGMA2, seed=seed, n_init=10)
        profile_meta = {"selection": "default_constant", "curve": []}
    R = np.asarray(fit["responsibilities"], dtype=float)
    means = np.asarray(fit["means"], dtype=float)
    labels = responsibilities_to_labels(R)
    return {
        "responsibilities": R,
        "means": means,
        "labels": labels,
        "sigma2": float(fit["sigma2"]),
        "pi": np.asarray(fit["pi"], dtype=float),
        "collapsed": bool(fit.get("collapsed", False)),
        "sigma2_selection": profile_meta,
        "component_fits": fit.get("component_fits", []),
        "fit": fit,
    }


def topic_keys(k: int, *, prefix: str = "T") -> list[str]:
    """Stable string keys for soft topics (``T0``, ``T1``, …)."""
    return [f"{prefix}{i}" for i in range(int(k))]


def component_local_plane(
    X: np.ndarray,
    weights: np.ndarray,
    component_fit: dict | None,
    *,
    q_viz: int = 2,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int] | None:
    """Return ``(mu, U, scales, q_model)`` for a Bishop–Tipping local plane.

    ``U`` is ``(d, q_viz)`` orthonormal. ``scales`` are semi-axis lengths in
    that plane (``sqrt(lambda)`` along each column of ``U``). Prefer the
    fitted component's ``U_q``; pad with weighted SVD if model ``q < q_viz``.
    """
    X = np.asarray(X, float)
    w = np.asarray(weights, float).ravel()
    if X.ndim != 2 or w.shape[0] != X.shape[0] or float(w.sum()) <= 0:
        return None
    mu = None
    U_model = None
    lam_model = None
    q_model = 0
    if component_fit is not None:
        mu = np.asarray(component_fit.get("mu"), float).ravel()
        U_model = np.asarray(component_fit.get("U_q"), float)
        lam_model = np.asarray(component_fit.get("lambdas_q"), float).ravel()
        q_model = int(
            component_fit.get(
                "q", U_model.shape[1] if U_model.ndim == 2 else 0
            )
        )
        if mu.shape[0] != X.shape[1]:
            mu = None
            U_model = None
            lam_model = None
            q_model = 0
    if mu is None:
        mu = (w[:, None] * X).sum(axis=0) / float(w.sum())
    Xc = X - mu
    need = int(q_viz)
    cols: list[np.ndarray] = []
    lams: list[float] = []
    if U_model is not None and U_model.ndim == 2 and U_model.shape[0] == X.shape[1]:
        for j in range(min(U_model.shape[1], need)):
            cols.append(U_model[:, j])
            if lam_model is not None and j < len(lam_model):
                lams.append(float(max(lam_model[j], 0.0)))
            else:
                lams.append(0.0)
    if len(cols) < need:
        sw = np.sqrt(np.clip(w, 0.0, None))
        Xw = sw[:, None] * Xc
        _, s, Vt = np.linalg.svd(Xw, full_matrices=False)
        w_sum = float(w.sum())
        eig = (s ** 2) / w_sum if w_sum > 0 else s ** 2
        for i, row in enumerate(Vt):
            if len(cols) >= need:
                break
            v = row.astype(float)
            if any(abs(float(np.dot(v, c))) > 0.99 for c in cols):
                continue
            cols.append(v)
            lams.append(float(max(eig[i], 0.0)) if i < len(eig) else 0.0)
    if not cols:
        return None
    while len(cols) < need:
        cols.append(np.zeros(X.shape[1]))
        lams.append(0.0)
    U = np.column_stack(cols[:need])
    Q, _ = np.linalg.qr(U)
    sw = np.sqrt(np.clip(w, 0.0, None))
    Xw = sw[:, None] * Xc
    scales = np.zeros(need, dtype=float)
    w_sum = float(w.sum())
    for j in range(need):
        proj = Xw @ Q[:, j]
        var = float((proj ** 2).sum() / w_sum) if w_sum > 0 else 0.0
        if j < len(lams) and lams[j] > 0 and U_model is not None and j < U_model.shape[1]:
            if abs(float(np.dot(Q[:, j], U_model[:, j]))) > 0.9:
                var = max(var, lams[j])
        scales[j] = float(np.sqrt(max(var, 0.0)))
    return mu, Q[:, :need], scales, q_model


def fit_from_responsibilities(
    X: np.ndarray,
    R: np.ndarray,
    sigma2: float,
    *,
    seed: int = 0,
    max_iter: int = 30,
    tol: float = 1e-5,
    normalize_means: bool = True,
) -> dict[str, Any]:
    """Run EM M-/E-steps starting from given responsibilities (fixed σ²)."""
    X = np.asarray(X, dtype=float)
    R = np.asarray(R, dtype=float)
    n, k = R.shape
    pi = R.mean(axis=0)
    n_iter = 0
    max_iter = max(0, int(max_iter))
    if max_iter == 0:
        component_fits = [fit_weighted_ppca(X, R[:, j], sigma2) for j in range(k)]
        means = np.vstack([fit["mu"] for fit in component_fits])
        if normalize_means:
            means = _l2_normalize_rows(means)
        return {
            "responsibilities": R,
            "means": means,
            "pi": pi,
            "sigma2": float(sigma2),
            "n_iter": 0,
            "component_fits": component_fits,
            "seed": int(seed),
            "k": int(k),
            "collapsed": bool(topic_fit_diagnostics(
                {
                    "responsibilities": R,
                    "means": means,
                    "sigma2": sigma2,
                    "k": k,
                    "component_fits": component_fits,
                }
            )["collapsed"]),
        }
    for n_iter in range(1, max_iter + 1):
        component_fits = [fit_weighted_ppca(X, R[:, j], sigma2) for j in range(k)]
        log_lik = np.column_stack(
            [log_likelihood_ppca(X, fit, sigma2) for fit in component_fits]
        )
        log_pi = np.log(np.clip(pi, 1e-300, None))
        for j, fit in enumerate(component_fits):
            if fit.get("weight_sum", 0.0) <= 0:
                log_pi[j] = -np.inf
        R_new = _softmax_rows(log_lik + log_pi[None, :])
        pi = R_new.mean(axis=0)
        delta = float(np.max(np.abs(R_new - R)))
        R = R_new
        if delta < tol:
            break
    component_fits = [fit_weighted_ppca(X, R[:, j], sigma2) for j in range(k)]
    means = np.vstack([fit["mu"] for fit in component_fits])
    if normalize_means:
        means = _l2_normalize_rows(means)
    return {
        "responsibilities": R,
        "means": means,
        "pi": pi,
        "sigma2": float(sigma2),
        "n_iter": int(n_iter),
        "component_fits": component_fits,
        "seed": int(seed),
        "k": int(k),
        "collapsed": bool(topic_fit_diagnostics(
            {
                "responsibilities": R,
                "means": means,
                "sigma2": sigma2,
                "k": k,
                "component_fits": component_fits,
            }
        )["collapsed"]),
    }


def _child_mass_balance(child_cols: np.ndarray) -> tuple[float, int]:
    """Return ``(min_fraction, n_map)`` for soft child columns (higher is better)."""
    cols = np.asarray(child_cols, dtype=float)
    sums = cols.sum(axis=0)
    total = float(sums.sum())
    if total <= 0 or cols.shape[1] < 1:
        return 0.0, 0
    min_frac = float(sums.min() / total)
    n_map = int((np.bincount(cols.argmax(axis=1), minlength=cols.shape[1]) > 0).sum())
    return min_frac, n_map


def propose_split(
    X: np.ndarray,
    fit: dict[str, Any],
    topic_id: int,
    *,
    n_children: int = 2,
    seed: int = 0,
    mass_threshold: float = 0.05,
    max_iter: int = 40,
    n_restarts: int = 8,
) -> dict[str, Any]:
    """Split one topic via a local mixture of PPCA on its soft mass.

    Child responsibilities are parent mass × local posterior. Does not call
    an LLM; children are returned as ``dirty`` indices for naming.

    A single k-means seed often collapses the local 2-fit on tightly clustered
    embeddings (one child keeps almost all mass). We try ``n_restarts`` seeds
    and keep the soft split with the best balance. Post-split EM reassignment
    is skipped (``fit_from_responsibilities(..., max_iter=0)``) so a later
    M-step cannot wipe MAP membership off the minority child.
    """
    if n_children < 2:
        raise ValueError(f"n_children must be >= 2, got {n_children}")
    R = np.asarray(fit["responsibilities"], dtype=float)
    X = np.asarray(X, dtype=float)
    i = int(topic_id)
    k = R.shape[1]
    if i < 0 or i >= k:
        raise ValueError(f"topic_id {i} out of range for k={k}")
    mass = R[:, i]
    mask = mass >= float(mass_threshold)
    if int(mask.sum()) < n_children:
        order = np.argsort(-mass)
        take = max(n_children, min(len(order), max(n_children * 5, n_children)))
        mask = np.zeros(len(mass), dtype=bool)
        mask[order[:take]] = True
    X_sub = X[mask]
    if X_sub.shape[0] < n_children:
        raise ValueError(
            f"not enough mass on topic {i} to split into {n_children} "
            f"(got {X_sub.shape[0]} points)"
        )
    sigma2 = float(fit["sigma2"])
    parent_cf = None
    cfs = fit.get("component_fits") or []
    if 0 <= i < len(cfs):
        parent_cf = dict(cfs[i])

    n_restarts = max(1, int(n_restarts))
    best: dict[str, Any] | None = None
    best_key: tuple[int, float] = (-1, -1.0)
    for r_i in range(n_restarts):
        trial_seed = int(seed) + r_i
        local_trial = mppca_fit(
            X_sub,
            n_children,
            sigma2=sigma2,
            seed=trial_seed,
            max_iter=max_iter,
        )
        log_lik = np.column_stack(
            [
                log_likelihood_ppca(X, cf, sigma2)
                for cf in local_trial["component_fits"]
            ]
        )
        log_pi = np.log(np.clip(local_trial["pi"], 1e-300, None))
        r_local = _softmax_rows(log_lik + log_pi[None, :])
        child_trial = mass[:, None] * r_local
        min_frac, n_map = _child_mass_balance(child_trial)
        key = (n_map, min_frac)
        if key > best_key:
            best_key = key
            best = {
                "local": local_trial,
                "child_cols": child_trial,
                "seed": trial_seed,
            }
            # Ideal 2-way split is near 0.5; stop early if clearly balanced.
            if n_map >= n_children and min_frac >= 0.35:
                break
    assert best is not None
    local = dict(best["local"])
    child_cols = np.asarray(best["child_cols"], dtype=float)
    chosen_seed = int(best["seed"])

    child_order = np.argsort(-child_cols.sum(axis=0))
    child_cols = child_cols[:, child_order]
    local["component_fits"] = [
        local["component_fits"][int(j)] for j in child_order
    ]
    local["pi"] = np.asarray(local["pi"], float)[child_order]
    if "means" in local:
        local["means"] = np.asarray(local["means"], float)[child_order]
    parts = []
    if i > 0:
        parts.append(R[:, :i])
    parts.append(child_cols)
    if i + 1 < k:
        parts.append(R[:, i + 1 :])
    R_new = np.hstack(parts)
    R_new = R_new / np.clip(R_new.sum(axis=1, keepdims=True), 1e-12, None)
    # Lock soft child mass: refine planes only. Full EM often collapses MAP
    # onto one child even when soft mass is balanced (CIMT / k=1 entry).
    new_fit = fit_from_responsibilities(
        X, R_new, sigma2, seed=chosen_seed, max_iter=0
    )
    R_f = np.asarray(new_fit["responsibilities"], float)
    child_slice = R_f[:, i : i + n_children]
    post_order = np.argsort(-child_slice.sum(axis=0))
    if not np.array_equal(post_order, np.arange(n_children)):
        R_f[:, i : i + n_children] = child_slice[:, post_order]
        new_fit["responsibilities"] = R_f
        cfs2 = list(new_fit.get("component_fits") or [])
        if len(cfs2) >= i + n_children:
            block = [cfs2[i + int(j)] for j in post_order]
            for t, cf in enumerate(block):
                cfs2[i + t] = cf
            new_fit["component_fits"] = cfs2
        if "means" in new_fit and new_fit["means"] is not None:
            means = np.asarray(new_fit["means"], float)
            means[i : i + n_children] = means[i : i + n_children][post_order]
            new_fit["means"] = means
        if "pi" in new_fit and new_fit["pi"] is not None:
            pi = np.asarray(new_fit["pi"], float)
            pi[i : i + n_children] = pi[i : i + n_children][post_order]
            new_fit["pi"] = pi
        child_cols = child_cols[:, post_order]
        local["component_fits"] = [
            local["component_fits"][int(j)] for j in post_order
        ]
        local["pi"] = np.asarray(local["pi"], float)[post_order]
        child_order = child_order[post_order]
    child_ids = list(range(i, i + n_children))
    history_entry = {
        "action": "split",
        "topic": i,
        "children": child_ids,
        "n_children": n_children,
        "child_order_by_mass": [int(j) for j in child_order],
        "kl": 0.0,
        "had_parent_fit": parent_cf is not None,
        "local_seed": chosen_seed,
        "child_mass_min_frac": float(best_key[1]),
    }
    return {
        "fit": new_fit,
        "dirty": child_ids,
        "history_entry": history_entry,
        "local_fit": local,
        "parent_id": i,
        "parent_mass": mass.copy(),
        "parent_component_fit": parent_cf,
        "child_responsibilities": child_cols,
        "kl": 0.0,
    }


def rebuild_uq_by_topic(
    embeddings: np.ndarray,
    responsibilities: np.ndarray,
    *,
    phrases: Sequence[Any] | None = None,
    sigma2: float | None = None,
    component_fits: Sequence[dict] | None = None,
    topic_prefix: str = "T",
) -> dict[str, dict[str, Any]]:
    """Build ``{Tj: local_uq_plotly_spec(...)}`` for every component."""
    from referia.util.plotly_figures import local_uq_plotly_spec

    R = np.asarray(responsibilities, float)
    keys = topic_keys(R.shape[1], prefix=topic_prefix)
    out: dict[str, dict[str, Any]] = {}
    for j, key in enumerate(keys):
        spec = local_uq_plotly_spec(
            embeddings,
            R,
            focus=j,
            component_fits=component_fits,
            phrases=phrases,
            sigma2=sigma2,
            title=f"Focus {key} — local U_q (Bishop–Tipping)",
            topic_prefix=topic_prefix,
        )
        if spec is not None:
            out[key] = spec
    return out


def _topic_index(keys: Sequence[str], focus_topic: Any) -> int:
    key = str(focus_topic) if focus_topic is not None else ""
    if key in keys:
        return list(keys).index(key)
    # Accept bare integers / "0"
    try:
        idx = int(key.replace("T", ""))
        if 0 <= idx < len(keys):
            return idx
    except ValueError:
        pass
    return 0


# Propose / confirm / undo: controls (σ², em_*) are inputs only; catalogue
# fields (responsibilities, topic_keys, topic_parent, uq_*, pending_*,
# split_undo) are writes.  ``topic_parent`` is the living genealogy map
# (multilogue ``parent_of``) — not an ephemeral return scrap.


def _phrase_list(phrases: Any, n: int) -> list[str]:
    if phrases is None:
        return [f"phrase {i}" for i in range(n)]
    if isinstance(phrases, str):
        return [phrases]
    out = [str(p) for p in phrases]
    if len(out) != n:
        return (out + ["—"] * n)[:n]
    return out


def _topic_parent_map(raw: Any, keys: Sequence[str]) -> dict[str, str | None]:
    """Normalise living genealogy: topic key → parent label (or None for roots)."""
    out: dict[str, str | None] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if v in (None, "", "null"):
                out[str(k)] = None
            else:
                out[str(k)] = str(v)
    for key in keys:
        out.setdefault(str(key), None)
    return out


def _remap_topic_parent(
    old_map: dict[str, str | None],
    keys_old: Sequence[str],
    keys_new: Sequence[str],
    focus_idx: int,
    child_keys: Sequence[str],
    parent_label: str,
) -> dict[str, str | None]:
    """Remap ``topic_parent`` after a split (same index shift as multilogue)."""
    n_ch = len(child_keys)
    new_map: dict[str, str | None] = {}
    for old_i, old_key in enumerate(keys_old):
        if old_i == focus_idx:
            continue
        if old_i < focus_idx:
            new_key = keys_new[old_i]
        else:
            new_key = keys_new[old_i + n_ch - 1]
        new_map[str(new_key)] = old_map.get(str(old_key))
    for ck in child_keys:
        new_map[str(ck)] = parent_label
    return new_map


def _soft_association_counts(
    responsibilities: Any,
    n_topics: int,
    mass_threshold: float = 0.05,
) -> tuple[list[int], list[float]]:
    """Per-topic soft counts: ``(R > τ).sum(axis=0)`` and ``R.sum(axis=0)``."""
    R = np.asarray(responsibilities, dtype=float)
    if R.ndim != 2 or R.shape[1] != n_topics:
        return [0] * n_topics, [0.0] * n_topics
    tau = float(mass_threshold)
    n_soft = (R > tau).sum(axis=0).astype(int).tolist()
    mass = R.sum(axis=0).astype(float).tolist()
    return n_soft, mass


def format_topic_tree_markdown(
    topic_keys: Any = None,
    topic_labels: Any = None,
    topic_parent: Any = None,
    focus_topic: Any = None,
    responsibilities: Any = None,
    mass_threshold: float = 0.05,
) -> str:
    """Render genealogy tree plus a soft-association table.

    Pure view of catalogue state — does not mutate inputs.  Children are
    matched by parent *label* (``topic_parent`` values) with a key fallback.

    Soft-associated count for topic *j* is the number of phrases with
    ``R[i, j] > mass_threshold``; soft mass is ``Σ_i R[i, j]``.

    The soft-association block is an HTML ``<table>`` so it renders under
    lynguine ``markdown2html`` without requiring the Markdown tables
    extension (pipe tables otherwise collapse to a literal paragraph).
    """
    keys = [str(k) for k in (topic_keys or [])]
    if not keys:
        return "_No topics yet._"
    labels: dict[str, str] = {}
    if isinstance(topic_labels, dict):
        labels = {str(k): str(v) for k, v in topic_labels.items()}
    parent = _topic_parent_map(topic_parent, keys)
    focus = str(focus_topic) if focus_topic not in (None, "") else None
    n_soft, soft_mass = _soft_association_counts(
        responsibilities, len(keys), mass_threshold=mass_threshold
    )

    # parent_label_or_key → child keys (stable key order)
    children: dict[str, list[str]] = {}
    roots: list[str] = []
    for key in keys:
        p = parent.get(key)
        if p in (None, ""):
            roots.append(key)
            continue
        children.setdefault(str(p), []).append(key)

    def _label(key: str) -> str:
        return labels.get(key) or key

    def _child_keys(key: str) -> list[str]:
        lab = _label(key)
        seen: list[str] = []
        for token in (lab, key):
            for ck in children.get(token, []):
                if ck not in seen:
                    seen.append(ck)
        return seen

    # HTML table: survives markdown→HTML without the ``tables`` extension.
    rows = [
        "<table>",
        "<thead><tr><th>Topic</th><th>Soft n</th><th>Mass</th></tr></thead>",
        "<tbody>",
    ]
    for i, key in enumerate(keys):
        mark = " ← focus" if focus and key == focus else ""
        # Show the human label; keep the catalogue key as a title for hover.
        topic_cell = (
            f'<span title="{html.escape(key)}">'
            f"{html.escape(_label(key))}</span>{html.escape(mark)}"
        )
        rows.append(
            "<tr>"
            f"<td>{topic_cell}</td>"
            f'<td style="text-align:right">{n_soft[i]}</td>'
            f'<td style="text-align:right">{soft_mass[i]:.1f}</td>'
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    table = rows

    tree_lines: list[str] = []
    claimed: set[str] = set()

    def _walk(key: str, depth: int, stack: set[str]) -> None:
        if key in stack or key in claimed:
            return
        stack.add(key)
        claimed.add(key)
        mark = " ← focus" if focus and key == focus else ""
        indent = "  " * depth
        tree_lines.append(f"{indent}- **{_label(key)}**{mark}")
        for ck in _child_keys(key):
            _walk(ck, depth + 1, stack)
        stack.discard(key)

    for r in roots:
        _walk(r, 0, set())
    # Children whose parent label is no longer a live topic (parent was
    # replaced by the split): group under a virtual ancestry header.
    orphan_groups: dict[str, list[str]] = {}
    for key in keys:
        if key in claimed:
            continue
        p = parent.get(key)
        orphan_groups.setdefault("" if p in (None, "") else str(p), []).append(key)
    for p, child_list in orphan_groups.items():
        if p:
            tree_lines.append(f"- _{p}_")
            for key in child_list:
                mark = " ← focus" if focus and key == focus else ""
                tree_lines.append(f"  - **{_label(key)}**{mark}")
                claimed.add(key)
        else:
            for key in child_list:
                mark = " ← focus" if focus and key == focus else ""
                tree_lines.append(f"- **{_label(key)}**{mark}")
                claimed.add(key)

    parts = ["\n".join(table)]
    if tree_lines:
        parts.append("\n".join(tree_lines))
    return "\n\n".join(parts)


def subject_grain_propose_split(
    embeddings: Any,
    responsibilities: Any,
    phrases: Any = None,
    focus_topic: Any = "T0",
    sigma2: float = 0.05,
    em_accept: int = 40,
    mass_threshold: float = 0.05,
    n_children: int = 2,
    topic_labels: Any = None,
    topic_parent: Any = None,
    seed: int = 0,
) -> tuple:
    """Propose a soft split: apply geometry + overlay; leave Confirm/Undo open.

    Reads ``sigma2`` / ``em_accept`` as EM *controls* (does not write them).
    Writes catalogue geometry (including ``topic_parent`` genealogy and a
    derived ``topic_tree`` Markdown view) plus ``pending_proposal`` /
    ``split_undo``.

    Returns
    -------
    tuple
        ``(uq_spec, uq_by_topic, topic_keys, responsibilities, focus_topic,
        topic_labels, topic_parent, topic_tree, pending_proposal, split_undo)``.
    """
    X = np.asarray(embeddings, dtype=float)
    R = np.asarray(responsibilities, dtype=float)
    s2 = float(sigma2)
    phrase_list = _phrase_list(phrases, len(X))
    keys = topic_keys(R.shape[1])
    focus_idx = _topic_index(keys, focus_topic)
    parent_key = keys[focus_idx]
    labels_in: dict[str, str] = {}
    if isinstance(topic_labels, dict):
        labels_in = {str(k): str(v) for k, v in topic_labels.items()}
    parent_in = _topic_parent_map(topic_parent, keys)

    # Snapshot catalogue only (no controls) so Undo cannot clobber σ² etc.
    cfs = [fit_weighted_ppca(X, R[:, j], s2) for j in range(R.shape[1])]
    uq_before = rebuild_uq_by_topic(
        X, R, phrases=phrase_list, sigma2=s2, component_fits=cfs
    )
    focus_before = parent_key if parent_key in uq_before else next(
        iter(uq_before), parent_key
    )
    split_undo = {
        "topic_keys": list(keys),
        "responsibilities": R.tolist(),
        "focus_topic": focus_before,
        "topic_labels": dict(labels_in),
        "topic_parent": dict(parent_in),
        "uq_spec": uq_before.get(focus_before),
        "uq_by_topic": uq_before,
    }

    out = propose_split(
        X,
        {"responsibilities": R, "sigma2": s2, "component_fits": cfs},
        focus_idx,
        n_children=int(n_children),
        seed=int(seed),
        mass_threshold=float(mass_threshold),
        max_iter=max(1, int(em_accept)),
    )
    new_fit = out["fit"]
    R_new = np.asarray(new_fit["responsibilities"], float)
    keys_new = topic_keys(R_new.shape[1])
    n_ch = int(n_children)
    labels_out: dict[str, str] = {}
    for old_i, old_key in enumerate(keys):
        if old_i < focus_idx:
            labels_out[keys_new[old_i]] = labels_in.get(
                old_key, f"Topic {old_i}"
            )
        elif old_i > focus_idx:
            labels_out[keys_new[old_i + n_ch - 1]] = labels_in.get(
                old_key, f"Topic {old_i}"
            )
    parent_label = labels_in.get(parent_key, parent_key)
    # Soft split replaces the parent topic with its children, so the parent
    # label is no longer a live topic. Drop provisional seeds (``Topic N``)
    # immediately; keep named parents for a virtual tree header.
    from referia.assess.compute.topic_naming import (
        _is_provisional_label,
        _prune_ghost_parents,
        _short_parent_for_placeholder,
    )

    # Never nest «…» → (unnamed N) into another Propose placeholder.
    parent_display = _short_parent_for_placeholder(parent_label, parent_key)
    child_keys = [keys_new[int(c)] for c in out["dirty"]]
    child_labels = []
    for t, child_id in enumerate(out["dirty"]):
        lab = f"«{parent_display}» → (unnamed {t})"
        labels_out[keys_new[child_id]] = lab
        child_labels.append(lab)
    # Genealogy keeps the full named parent when available; provisional
    # parents are cleared below rather than stored as nested placeholders.
    parent_for_tree = (
        parent_label
        if not _is_provisional_label(parent_label, parent_key)
        else parent_display
    )
    parent_out = _remap_topic_parent(
        parent_in, keys, keys_new, focus_idx, child_keys, parent_for_tree
    )

    if _is_provisional_label(parent_label, parent_key):
        for ck in child_keys:
            parent_out[str(ck)] = None
    else:
        parent_out = _prune_ghost_parents(parent_out, labels_out)

    # Per-topic planes for Confirm; overlay shown while pending.
    planes_after_accept = rebuild_uq_by_topic(
        X,
        R_new,
        phrases=phrase_list,
        sigma2=s2,
        component_fits=new_fit.get("component_fits"),
    )
    parent_cf = out.get("parent_component_fit")
    child_cfs = list((out.get("local_fit") or {}).get("component_fits") or [])
    focus_new = child_keys[0]
    proposed = None
    if parent_cf is not None and child_cfs:
        from referia.util.plotly_figures import proposed_split_plotly_spec
        proposed = proposed_split_plotly_spec(
            X,
            parent_mass=out["parent_mass"],
            parent_component_fit=parent_cf,
            child_component_fits=child_cfs,
            responsibilities=R_new,
            phrases=phrase_list,
            child_labels=child_labels,
            parent_label=parent_display,
            sigma2=s2,
        )
    if proposed is None:
        proposed = planes_after_accept.get(focus_new) or next(
            iter(planes_after_accept.values()), {}
        )
    # figure_source(key=child) must show overlay while pending.
    uq_by_topic = dict(planes_after_accept)
    for ck in child_keys:
        uq_by_topic[ck] = proposed
    # Seal metadata for Confirm; genealogy already applied in topic_parent.
    he = out.get("history_entry") if isinstance(out.get("history_entry"), dict) else {}
    pending_proposal = {
        "kind": "split",
        "accepted": False,
        "parent": parent_key,
        "parent_label": parent_display,
        "children": child_keys,
        "k_before": len(keys),
        "k_after": len(keys_new),
        "focus": focus_new,
        "planes_after_accept": planes_after_accept,
        "history_entry": {
            "action": "split",
            "parent": parent_key,
            "parent_label": parent_display,
            "children": list(child_keys),
            "k_before": len(keys),
            "k_after": len(keys_new),
            **{k: he[k] for k in (
                "n_children",
                "child_order_by_mass",
                "local_seed",
                "child_mass_min_frac",
            ) if k in he},
        },
    }
    tree = format_topic_tree_markdown(
        keys_new,
        labels_out,
        parent_out,
        focus_new,
        responsibilities=R_new,
        mass_threshold=float(mass_threshold),
    )
    return (
        proposed,
        uq_by_topic,
        keys_new,
        R_new.tolist(),
        focus_new,
        labels_out,
        parent_out,
        tree,
        pending_proposal,
        split_undo,
    )


def subject_grain_confirm_split(
    pending_proposal: Any = None,
) -> tuple:
    """Seal a proposed split: overlay → per-topic planes; clear pending/undo.

    Does not touch EM controls.

    Returns
    -------
    tuple
        ``(uq_spec, uq_by_topic, pending_proposal, split_undo)``.
    """
    if not isinstance(pending_proposal, dict) or not pending_proposal:
        return (None, None, None, None)
    planes = pending_proposal.get("planes_after_accept")
    focus = pending_proposal.get("focus")
    if not isinstance(planes, dict) or not planes:
        return (None, None, None, None)
    uq_spec = planes.get(focus) if focus is not None else None
    if uq_spec is None:
        uq_spec = next(iter(planes.values()), {})
    return (uq_spec, planes, None, None)


def subject_grain_undo_split(
    split_undo: Any = None,
    embeddings: Any = None,
    phrases: Any = None,
    sigma2: Any = None,
) -> tuple:
    """Reject a proposed split: restore catalogue geometry; clear pending/undo.

    Restores responsibilities / keys / labels / focus / ``topic_parent`` from
    ``split_undo``.  Redraws planes with the *live* ``sigma2`` control when
    embeddings are supplied — never writes ``sigma2`` itself.  Regenerates
    the derived ``topic_tree`` view.

    Returns
    -------
    tuple
        ``(uq_spec, uq_by_topic, topic_keys, responsibilities, focus_topic,
        topic_labels, topic_parent, topic_tree, pending_proposal, split_undo)``
        — last two cleared.
    """
    if not isinstance(split_undo, dict) or not split_undo:
        raise ValueError("No split_undo snapshot — nothing to reject.")
    keys = list(split_undo.get("topic_keys") or [])
    R = split_undo.get("responsibilities")
    focus = split_undo.get("focus_topic") or (keys[0] if keys else "T0")
    labels = split_undo.get("topic_labels") or {}
    parent_map = _topic_parent_map(split_undo.get("topic_parent"), keys)

    uq_by_topic = split_undo.get("uq_by_topic") or {}
    uq_spec = split_undo.get("uq_spec")
    # Prefer a fresh redraw at the live control σ² when we have embeddings.
    if embeddings is not None and R is not None and sigma2 is not None:
        try:
            X = np.asarray(embeddings, dtype=float)
            R_arr = np.asarray(R, dtype=float)
            s2 = float(sigma2)
            if X.ndim == 2 and R_arr.ndim == 2 and R_arr.shape[0] == len(X):
                phrase_list = _phrase_list(phrases, len(X))
                uq_by_topic = rebuild_uq_by_topic(
                    X, R_arr, phrases=phrase_list, sigma2=s2
                )
                uq_spec = uq_by_topic.get(focus) or next(
                    iter(uq_by_topic.values()), {}
                )
        except (TypeError, ValueError):
            pass
    if uq_spec is None and isinstance(uq_by_topic, dict) and uq_by_topic:
        uq_spec = uq_by_topic.get(focus) or next(iter(uq_by_topic.values()), {})
    tree = format_topic_tree_markdown(
        keys, labels, parent_map, focus, responsibilities=R
    )
    return (
        uq_spec,
        uq_by_topic,
        keys,
        R,
        focus,
        labels,
        parent_map,
        tree,
        None,
        None,
    )
