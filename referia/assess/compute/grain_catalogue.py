"""Shared subject-grain catalogue helpers (CIP-0019).

Soft MPPCA and sklearn partitions both write a row-stochastic ``R`` plus
topic keys, labels, parent map, and tree Markdown. Method-specific geometry
stays in ``mppca.py`` / ``kmeans.py`` / ``agglomerative.py``.
"""

from __future__ import annotations

import html
from typing import Any, Sequence

import numpy as np

__all__ = [
    "as_embedding_matrix",
    "format_topic_tree_markdown",
    "l2_normalize_rows",
    "one_hot_from_labels",
    "phrase_list",
    "responsibilities_present",
    "topic_keys",
    "topic_parent_map",
]


def l2_normalize_rows(X: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    return X / np.clip(norms, eps, None)


def as_embedding_matrix(X: Any) -> np.ndarray:
    """C-contiguous ``(n, d)`` float64, including pandas object columns of lists.

    ``np.asarray`` on a packed object series of 3072-float lists is a 1-D
    object array; stacking that inside EM is the hang we saw on Draghi.
    """
    arr = np.asarray(X)
    if arr.ndim == 2 and arr.dtype != object:
        return np.ascontiguousarray(arr, dtype=np.float64)
    if arr.dtype != object and arr.ndim != 2:
        raise ValueError(f"embeddings must be 2-D, got shape {arr.shape}")
    seq = arr.tolist() if isinstance(arr, np.ndarray) else list(X)
    if not seq:
        return np.zeros((0, 0), dtype=np.float64)
    rows = [np.asarray(row, dtype=np.float64).reshape(-1) for row in seq]
    d = int(rows[0].shape[0])
    out = np.empty((len(rows), d), dtype=np.float64, order="C")
    for i, row in enumerate(rows):
        if int(row.shape[0]) != d:
            raise ValueError(
                f"embedding row {i} has length {row.shape[0]}, expected {d}"
            )
        out[i] = row
    return out


def topic_keys(k: int, *, prefix: str = "T") -> list[str]:
    """Stable string keys for topics (``T0``, ``T1``, …)."""
    return [f"{prefix}{i}" for i in range(int(k))]


def responsibilities_present(responsibilities: Any) -> bool:
    if responsibilities is None:
        return False
    try:
        arr = np.asarray(responsibilities, dtype=float)
    except (TypeError, ValueError):
        return False
    return arr.ndim == 2 and arr.size > 0


def phrase_list(phrases: Any, n: int) -> list[str]:
    if phrases is None:
        return [f"phrase {i}" for i in range(n)]
    if isinstance(phrases, str):
        return [phrases]
    out = [str(p) for p in phrases]
    if len(out) != n:
        return (out + ["—"] * n)[:n]
    return out


def topic_parent_map(raw: Any, keys: Sequence[str]) -> dict[str, str | None]:
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


def one_hot_from_labels(labels: Any, n_clusters: int | None = None) -> np.ndarray:
    """Row-stochastic one-hot ``R`` from integer cluster ids."""
    y = np.asarray(labels).reshape(-1)
    if y.size == 0:
        k = int(n_clusters or 0)
        return np.zeros((0, k), dtype=float)
    if y.dtype == object or y.dtype.kind in "US":
        y = np.asarray(y, dtype=float)
    y = y.astype(int)
    k = int(n_clusters if n_clusters is not None else (int(y.max()) + 1 if y.size else 0))
    if k <= 0:
        raise ValueError("n_clusters must be positive")
    if np.any(y < 0) or np.any(y >= k):
        raise ValueError(f"labels must be in [0, {k}), got min={y.min()} max={y.max()}")
    R = np.zeros((y.shape[0], k), dtype=float)
    R[np.arange(y.shape[0]), y] = 1.0
    return R


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
    parent = topic_parent_map(topic_parent, keys)
    focus = str(focus_topic) if focus_topic not in (None, "") else None
    n_soft, soft_mass = _soft_association_counts(
        responsibilities, len(keys), mass_threshold=mass_threshold
    )

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

    rows = [
        "<table>",
        "<thead><tr><th>Topic</th><th>Soft n</th><th>Mass</th></tr></thead>",
        "<tbody>",
    ]
    for i, key in enumerate(keys):
        mark = " ← focus" if focus and key == focus else ""
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


# Private aliases used by mppca.py re-exports / existing call sites.
_as_embedding_matrix = as_embedding_matrix
_phrase_list = phrase_list
_responsibilities_present = responsibilities_present
_topic_parent_map = topic_parent_map
