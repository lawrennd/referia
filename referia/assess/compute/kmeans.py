"""sklearn k-means as a hard grain method (CIP-0019).

Writes a one-hot row-stochastic ``R``. Does not import ``mppca_fit``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.cluster import KMeans

from .grain_catalogue import as_embedding_matrix, l2_normalize_rows, one_hot_from_labels

__all__ = ["fit_kmeans"]


def fit_kmeans(
    embeddings: Any,
    n_clusters: int,
    *,
    init: str = "k-means++",
    n_init: int = 10,
    max_iter: int = 300,
    seed: int = 0,
) -> dict[str, Any]:
    """Partition ``(n, d)`` embeddings with sklearn ``KMeans``.

    Returns ``responsibilities`` (one-hot), L2-normalised ``means``,
    integer ``labels``, and ``inertia``.
    """
    X = as_embedding_matrix(embeddings)
    if X.ndim != 2 or X.shape[0] == 0:
        raise ValueError(
            f"k-means embeddings must be non-empty 2-D, got shape {X.shape}"
        )
    k = int(n_clusters)
    if k < 1:
        raise ValueError(f"n_clusters must be >= 1, got {n_clusters!r}")
    if k > X.shape[0]:
        raise ValueError(
            f"n_clusters={k} exceeds n={X.shape[0]} embeddings"
        )
    est = KMeans(
        n_clusters=k,
        init=str(init),
        n_init=int(n_init),
        max_iter=int(max_iter),
        random_state=int(seed),
    )
    labels = np.asarray(est.fit_predict(X), dtype=int)
    R = one_hot_from_labels(labels, k)
    means = l2_normalize_rows(np.asarray(est.cluster_centers_, dtype=float))
    return {
        "responsibilities": R,
        "means": means,
        "labels": labels,
        "inertia": float(est.inertia_),
    }
