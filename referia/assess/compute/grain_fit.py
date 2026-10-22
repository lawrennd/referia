"""Dispatch subject-grain fit across MPPCA and sklearn partitions (CIP-0019)."""

from __future__ import annotations

from typing import Any

import numpy as np

from .agglomerative import fit_agglomerative
from .grain_catalogue import (
    as_embedding_matrix,
    format_topic_tree_markdown,
    phrase_list,
    responsibilities_present,
    topic_keys,
    topic_parent_map,
)
from .kmeans import fit_kmeans

__all__ = [
    "SOFT_METHODS",
    "HARD_METHODS",
    "require_soft_method",
    "subject_grain_fit",
    "subject_grain_reset",
]

SOFT_METHODS = frozenset({"mppca"})
HARD_METHODS = frozenset({"kmeans", "agglomerative"})


def _lens_row_weights(n: int, lens_weight: Any, vq_mass: Any, method: str):
    mode = str(lens_weight or "uniform").strip().lower()
    if mode in ("", "uniform"):
        return None
    if mode != "mass":
        raise ValueError(
            f"lens_weight must be uniform or mass, got {lens_weight!r}"
        )
    if method == "agglomerative":
        raise ValueError(
            "lens_weight=mass is not supported with agglomerative clustering "
            "(sklearn AgglomerativeClustering has no sample_weight); "
            "use cluster_method=kmeans or mppca, or lens_weight=uniform"
        )
    if vq_mass is None:
        raise ValueError(
            "lens_weight=mass requires vq_mass from the VQ codebook"
        )
    w = np.asarray(vq_mass, dtype=float).ravel()
    if w.shape[0] != n:
        raise ValueError(
            f"vq_mass length {w.shape[0]} != codebook n={n}"
        )
    return w


def require_soft_method(cluster_method: Any = None) -> None:
    """Raise if Propose / Confirm / Undo is called on a hard partition."""
    method = str(cluster_method or "mppca").strip().lower()
    if method in SOFT_METHODS:
        return
    raise ValueError(
        f"Propose split is MPPCA-only; cluster_method={method!r}"
    )


def _empty_pending() -> tuple[None, None]:
    return None, None


def _pack_catalogue(
    X: np.ndarray,
    R: np.ndarray,
    phrases: Any,
    *,
    figure_map: dict[str, dict[str, Any]],
    topic_labels: Any = None,
    topic_parent: Any = None,
    focus_topic: Any = None,
) -> tuple:
    keys = topic_keys(R.shape[1])
    labels = (
        dict(topic_labels)
        if isinstance(topic_labels, dict)
        else {key: f"Topic {i}" for i, key in enumerate(keys)}
    )
    for i, key in enumerate(keys):
        labels.setdefault(key, f"Topic {i}")
    parent = topic_parent_map(topic_parent, keys)
    focus = str(focus_topic) if focus_topic not in (None, "") else keys[0]
    if focus not in keys:
        focus = keys[0]
    tree = format_topic_tree_markdown(
        keys, labels, parent, focus, responsibilities=R
    )
    spec = figure_map.get(focus) or next(iter(figure_map.values()), {})
    return (
        R.tolist(),
        figure_map,
        spec,
        keys,
        labels,
        parent,
        tree,
        focus,
    )


def _hard_figure_map(
    X: np.ndarray,
    R: np.ndarray,
    phrases: Any,
    *,
    children: np.ndarray | None = None,
    distances: np.ndarray | None = None,
    title: str = "cluster PCA",
) -> dict[str, dict[str, Any]]:
    from referia.util.plotly_figures import (
        cluster_dendrogram_plotly_spec,
        cluster_pca_plotly_spec,
    )

    keys = topic_keys(R.shape[1])
    phrase_vals = phrase_list(phrases, X.shape[0])
    out: dict[str, dict[str, Any]] = {}
    for j, key in enumerate(keys):
        spec = cluster_pca_plotly_spec(
            X,
            R,
            focus=j,
            phrases=phrase_vals,
            title=f"Focus {key} — {title}",
        )
        if spec is not None:
            out[key] = spec
    if children is not None and distances is not None and children.size:
        dendro = cluster_dendrogram_plotly_spec(
            children,
            distances,
            phrases=phrase_vals,
            labels=np.argmax(R, axis=1),
            n=X.shape[0],
        )
        if dendro is not None:
            out["_dendrogram"] = dendro
    return out


def subject_grain_fit(
    embeddings,
    phrases=None,
    cluster_method: str = "mppca",
    n_clusters: int = 8,
    k: int | None = None,
    force_refit: bool = False,
    responsibilities=None,
    uq_by_topic=None,
    uq_spec=None,
    topic_keys_existing=None,
    topic_labels=None,
    topic_parent=None,
    topic_tree=None,
    focus_topic=None,
    sigma2: float | None = None,
    sigma2_mode: str = "fixed",
    em_accept: int = 40,
    seed: int = 0,
    kmeans_init: str = "k-means++",
    kmeans_n_init: int = 10,
    kmeans_max_iter: int = 300,
    agglo_linkage: str = "average",
    agglo_metric: str = "cosine",
    lens_weight: str = "uniform",
    vq_mass=None,
    **_kwargs,
):
    """Fit the grain catalogue for ``cluster_method``.

    ``mppca`` keeps the CIP-0015 k=1 seed (or ``k``). Hard methods use
    ``n_clusters`` and write one-hot ``R``. Skip-if-``R``-present unless
    ``force_refit``, and only when ``R`` rows match the current embeddings
    (codebook ``m``, not leftover phrase-level scores).
    """
    method = str(cluster_method or "mppca").strip().lower()
    if method not in SOFT_METHODS | HARD_METHODS:
        raise ValueError(
            f"cluster_method must be mppca, kmeans, or agglomerative, "
            f"got {cluster_method!r}"
        )

    X = as_embedding_matrix(embeddings)
    if not force_refit and responsibilities_present(responsibilities):
        R_exist = np.asarray(responsibilities, dtype=float)
        if R_exist.ndim == 2 and R_exist.shape[0] == X.shape[0]:
            from .mppca import subject_grain_seed_fit

            return subject_grain_seed_fit(
                embeddings,
                phrases=phrases,
                force_refit=False,
                responsibilities=responsibilities,
                uq_by_topic=uq_by_topic,
                uq_spec=uq_spec,
                topic_keys_existing=topic_keys_existing,
                topic_labels=topic_labels,
                topic_parent=topic_parent,
                topic_tree=topic_tree,
                focus_topic=focus_topic,
            )

    weights = _lens_row_weights(X.shape[0], lens_weight, vq_mass, method)

    if method == "mppca":
        from .mppca import subject_grain_seed_fit

        k_use = 1 if k is None else int(k)
        return subject_grain_seed_fit(
            embeddings,
            phrases=phrases,
            sigma2=sigma2,
            sigma2_mode=sigma2_mode,
            em_accept=em_accept,
            k=k_use,
            force_refit=True,
            seed=int(seed),
            row_weights=weights,
        )

    n_k = int(n_clusters) if n_clusters is not None else 8
    if method == "kmeans":
        packed = fit_kmeans(
            X,
            n_k,
            init=kmeans_init,
            n_init=int(kmeans_n_init),
            max_iter=int(kmeans_max_iter),
            seed=int(seed),
            sample_weight=weights,
        )
        fig_title = "k-means PCA"
        children = distances = None
    else:
        packed = fit_agglomerative(
            X,
            n_k,
            linkage=agglo_linkage,
            metric=agglo_metric,
        )
        fig_title = "agglomerative PCA"
        children = packed.get("children")
        distances = packed.get("distances")

    R = np.asarray(packed["responsibilities"], float)
    figure_map = _hard_figure_map(
        X,
        R,
        phrases,
        children=children,
        distances=distances,
        title=fig_title,
    )
    return _pack_catalogue(X, R, phrases, figure_map=figure_map)


def subject_grain_reset(
    embeddings,
    phrases=None,
    cluster_method: str = "mppca",
    n_clusters: int = 8,
    **kwargs,
):
    """Refit: MPPCA returns to k=1; hard methods refit current ``n_clusters``."""
    method = str(cluster_method or "mppca").strip().lower()
    extra = dict(kwargs)
    extra.pop("k", None)
    extra.pop("force_refit", None)
    if method == "mppca":
        k_use = 1
    else:
        k_use = int(n_clusters) if n_clusters is not None else 8
    out = subject_grain_fit(
        embeddings,
        phrases=phrases,
        cluster_method=method,
        n_clusters=k_use,
        k=k_use,
        force_refit=True,
        **extra,
    )
    pending, undo = _empty_pending()
    selected = ""
    return (*out, pending, undo, selected)
