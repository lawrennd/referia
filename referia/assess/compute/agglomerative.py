"""sklearn agglomerative clustering as a hard grain method (CIP-0019)."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from .grain_catalogue import as_embedding_matrix, l2_normalize_rows, one_hot_from_labels

__all__ = ["fit_agglomerative"]

_EUCLIDEAN = frozenset({"euclidean", "l2"})


def fit_agglomerative(
    embeddings: Any,
    n_clusters: int,
    *,
    linkage: str = "average",
    metric: str = "cosine",
) -> dict[str, Any]:
    """Partition embeddings with sklearn ``AgglomerativeClustering``.

    Ward linkage requires Euclidean metric; we fail before the estimator
    so the message names both knobs. ``compute_distances=True`` fills
    ``children_`` / ``distances_`` for the dendrogram figure.
    """
    X = as_embedding_matrix(embeddings)
    if X.ndim != 2 or X.shape[0] == 0:
        raise ValueError(
            f"agglomerative embeddings must be non-empty 2-D, got shape {X.shape}"
        )
    k = int(n_clusters)
    if k < 1:
        raise ValueError(f"n_clusters must be >= 1, got {n_clusters!r}")
    if k > X.shape[0]:
        raise ValueError(
            f"n_clusters={k} exceeds n={X.shape[0]} embeddings"
        )
    link = str(linkage).strip().lower()
    met = str(metric).strip().lower()
    if link == "ward" and met not in _EUCLIDEAN:
        raise ValueError(
            f"Ward linkage requires euclidean metric, got linkage={link!r} "
            f"metric={met!r}"
        )
    est = AgglomerativeClustering(
        n_clusters=k,
        linkage=link,
        metric=met,
        compute_distances=True,
    )
    labels = np.asarray(est.fit_predict(X), dtype=int)
    R = one_hot_from_labels(labels, k)
    # Cluster means are not returned by sklearn; responsibility-weighted mean.
    mass = R.sum(axis=0, keepdims=True)
    mass = np.clip(mass, 1e-12, None)
    means = l2_normalize_rows((R.T @ X) / mass.T)
    children = np.asarray(getattr(est, "children_", np.zeros((0, 2))), dtype=int)
    distances = np.asarray(getattr(est, "distances_", np.zeros(0)), dtype=float)
    return {
        "responsibilities": R,
        "means": means,
        "labels": labels,
        "children": children,
        "distances": distances,
        "linkage": link,
        "metric": met,
    }
