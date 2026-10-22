"""Vector quantisation of phrase embeddings (CIP-001A).

K-means codebook on the packed phrase row. Cluster = fine cell; 03_grain
reads the centroids as its grain. Phrase-to-lens membership is QR.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .grain_catalogue import as_embedding_matrix, l2_normalize_rows, phrase_list
from .kmeans import fit_kmeans

__all__ = [
    "expand_vq_responsibilities",
    "subject_vq_fit",
]


def _as_bool(value: Any, default: bool = True) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, np.integer)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def expand_vq_responsibilities(cluster_ids, codebook_responsibilities) -> np.ndarray:
    """Lift codebook ``R`` (m × L) to phrase rows via one-hot ``Q``: ``QR``."""
    ids = np.asarray(cluster_ids, dtype=int).ravel()
    R = np.asarray(codebook_responsibilities, dtype=float)
    if R.ndim != 2:
        raise ValueError(
            f"codebook responsibilities must be 2-D, got shape {R.shape}"
        )
    if ids.size == 0:
        raise ValueError("cluster_ids must be non-empty")
    if int(ids.min()) < 0 or int(ids.max()) >= R.shape[0]:
        raise ValueError(
            f"cluster_ids range [{int(ids.min())}, {int(ids.max())}] is "
            f"outside codebook rows {R.shape[0]}"
        )
    return R[ids]


def subject_vq_fit(
    embeddings,
    phrases=None,
    n_vq: int = 64,
    force_refit: bool = False,
    cluster_ids=None,
    vq_spec=None,
    codebook_embeddings=None,
    codebook_phrases=None,
    vq_mass=None,
    vq_inertia=None,
    seed: int = 0,
    kmeans_init: str = "k-means++",
    kmeans_n_init: int = 10,
    kmeans_max_iter: int = 300,
    vq_walk_speed: float = 0.08,
    vq_walk_frames: int = 48,
    vq_walk_subspace: int = 8,
    vq_walk_linger: Any = True,
    **_kwargs,
):
    """Fit a k-means codebook and a Brownian projection-walk figure.

    Return order matches ``02_vq`` ``field:``:
    cluster_ids, codebook_embeddings, codebook_phrases, vq_mass,
    vq_spec, n_vq, vq_inertia, vq_n_phrases.

    Centroids are not written over input ``embeddings`` (phrase vectors).
    """
    X = as_embedding_matrix(embeddings)
    if X.ndim != 2 or X.shape[0] == 0:
        raise ValueError(
            f"VQ embeddings must be non-empty 2-D, got shape {X.shape}"
        )
    n = int(X.shape[0])
    m = min(int(n_vq) if n_vq is not None else 64, n)
    if m < 1:
        raise ValueError(f"n_vq must be >= 1, got {n_vq!r}")
    if (
        not force_refit
        and cluster_ids is not None
        and codebook_embeddings is not None
        and isinstance(vq_spec, dict)
        and vq_spec.get("frames")
    ):
        ids = np.asarray(cluster_ids).ravel()
        if ids.size == n:
            stored_phrases = (
                codebook_phrases if codebook_phrases is not None else phrases
            )
            return (
                ids.tolist(),
                np.asarray(codebook_embeddings).tolist(),
                list(stored_phrases)
                if not isinstance(stored_phrases, str)
                else [stored_phrases],
                np.asarray(vq_mass if vq_mass is not None else []).tolist(),
                vq_spec,
                int(m),
                float(vq_inertia or 0.0),
                n,
            )

    packed = fit_kmeans(
        X,
        m,
        init=kmeans_init,
        n_init=int(kmeans_n_init),
        max_iter=int(kmeans_max_iter),
        seed=int(seed),
    )
    labels = np.asarray(packed["labels"], dtype=int)
    centres = np.asarray(packed.get("centers"), dtype=float)
    if centres.ndim != 2 or centres.shape[0] != m:
        centres = np.vstack(
            [
                X[labels == j].mean(axis=0) if np.any(labels == j) else np.zeros(X.shape[1])
                for j in range(m)
            ]
        )
    mass = np.bincount(np.clip(labels, 0, m - 1), minlength=m).astype(float)
    phrase_vals = phrase_list(phrases, n)
    exemplars: list[str] = []
    Xl = l2_normalize_rows(X)
    Cl = l2_normalize_rows(centres)
    for j in range(m):
        idx = np.where(labels == j)[0]
        if idx.size == 0:
            exemplars.append("—")
            continue
        sim = Xl[idx] @ Cl[j]
        exemplars.append(phrase_vals[int(idx[int(np.argmax(sim))])])

    from referia.util.plotly_figures import vq_projection_walk_plotly_spec

    spec = vq_projection_walk_plotly_spec(
        X,
        labels,
        centres,
        phrases=phrase_vals,
        masses=mass,
        n_frames=int(vq_walk_frames),
        speed=float(vq_walk_speed),
        subspace=int(vq_walk_subspace),
        linger=_as_bool(vq_walk_linger, True),
        seed=int(seed),
    ) or {}

    return (
        labels.tolist(),
        l2_normalize_rows(centres).tolist(),
        exemplars,
        mass.tolist(),
        spec,
        int(m),
        float(packed.get("inertia", 0.0)),
        n,
    )
