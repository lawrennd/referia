"""Vector quantisation of phrase embeddings (CIP-001A).

K-means codebook on the packed phrase row. Cluster = fine cell; 04_grain
reads the centroids as its grain. Phrase-to-lens membership is QR.
"""

from __future__ import annotations

import json
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
    try:
        if np.isnan(value):
            return default
    except (TypeError, ValueError):
        pass
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: Any, default: int) -> int:
    """Coerce a knob; empty output columns arrive as NaN and must not crash."""
    if value is None or value == "":
        return int(default)
    try:
        f = float(value)
    except (TypeError, ValueError):
        return int(default)
    if not np.isfinite(f):
        return int(default)
    return int(f)


def _as_spec_dict(value: Any) -> dict:
    if value is None or value == "":
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    return dict(value) if isinstance(value, dict) else {}


def _spec_for_store(spec: Any) -> str:
    """Parquet cannot mix list traces with a layout mapping; store JSON."""
    if spec is None or spec == "":
        return ""
    if isinstance(spec, str):
        return spec
    return json.dumps(spec)


def _as_float(value: Any, default: float) -> float:
    if value is None or value == "":
        return float(default)
    try:
        f = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not np.isfinite(f):
        return float(default)
    return f


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

    Return order matches ``03_vq`` ``field:``:
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
    m = min(_as_int(n_vq, 64), n)
    if m < 1:
        raise ValueError(f"n_vq must be >= 1, got {n_vq!r}")
    if (
        not force_refit
        and cluster_ids is not None
        and codebook_embeddings is not None
        and _as_spec_dict(vq_spec).get("frames")
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
                _spec_for_store(vq_spec),
                int(m),
                _as_float(vq_inertia, 0.0),
                n,
            )

    packed = fit_kmeans(
        X,
        m,
        init=kmeans_init if kmeans_init not in (None, "") else "k-means++",
        n_init=_as_int(kmeans_n_init, 10),
        max_iter=_as_int(kmeans_max_iter, 300),
        seed=_as_int(seed, 0),
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
        n_frames=_as_int(vq_walk_frames, 48),
        speed=_as_float(vq_walk_speed, 0.08),
        subspace=_as_int(vq_walk_subspace, 8),
        linger=_as_bool(vq_walk_linger, True),
        seed=_as_int(seed, 0),
    ) or {}

    return (
        labels.tolist(),
        l2_normalize_rows(centres).tolist(),
        exemplars,
        mass.tolist(),
        _spec_for_store(spec),
        int(m),
        float(packed.get("inertia", 0.0)),
        n,
    )
