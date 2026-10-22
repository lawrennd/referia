"""Document-level EMD, MDS, and permutation tests (CIP-0016).

Module-level callables. After pack, histograms / EMD / MDS are row-local on
the corpus + scores arrays. POT is optional (``referia[distance]``).
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

__all__ = [
    "document_soft_topic_distributions",
    "topic_means_from_responsibilities",
    "cosine_ground_cost",
    "emd_distance_matrix",
    "classical_mds",
    "permanova",
    "permdisp",
    "axis_correlates",
    "distance_tests_markdown",
    "run_document_distance_analysis",
]


def _require_ot():
    try:
        import ot
    except ImportError as exc:
        raise ImportError(
            "POT is required for EMD. Install the Assess extra: "
            "pip install 'referia[distance]'"
        ) from exc
    return ot


def _as_2d(name: str, value) -> np.ndarray:
    arr = np.asarray(value, dtype=float)
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 2-D, got shape {arr.shape}")
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)


def _l2_rows(X: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    return X / np.clip(norms, eps, None)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return value


def document_soft_topic_distributions(
    doc_ids: Sequence,
    responsibilities,
    *,
    min_mass: float = 50.0,
) -> tuple[np.ndarray, list[str], list[float]]:
    """Soft topic histograms: normalised sum of phrase responsibilities per document."""
    R = _as_2d("responsibilities", responsibilities)
    ids = [str(d) for d in list(doc_ids)]
    if len(ids) != R.shape[0]:
        raise ValueError(
            f"doc_ids length {len(ids)} != responsibilities rows {R.shape[0]}"
        )
    k = R.shape[1]
    order: list[str] = []
    seen: dict[str, int] = {}
    sums: dict[str, np.ndarray] = {}
    for doc, row in zip(ids, R):
        if doc not in seen:
            seen[doc] = len(order)
            order.append(doc)
            sums[doc] = np.zeros(k, dtype=float)
        sums[doc] += row
    kept_ids: list[str] = []
    mass: list[float] = []
    rows: list[np.ndarray] = []
    threshold = float(min_mass) if min_mass is not None else 0.0
    for doc in sorted(order):
        total = float(sums[doc].sum())
        if total < threshold:
            continue
        kept_ids.append(doc)
        mass.append(total)
        rows.append(sums[doc] / total if total > 0 else sums[doc])
    if not rows:
        return np.zeros((0, k), dtype=float), [], []
    return np.vstack(rows), kept_ids, mass


def topic_means_from_responsibilities(
    embeddings, responsibilities
) -> np.ndarray:
    """Responsibility-weighted topic means, L2-normalised (k × d)."""
    X = _as_2d("embeddings", embeddings)
    R = _as_2d("responsibilities", responsibilities)
    if X.shape[0] != R.shape[0]:
        raise ValueError(
            f"embeddings rows {X.shape[0]} != responsibilities rows {R.shape[0]}"
        )
    mass = R.sum(axis=0)
    means = (R.T @ X) / np.clip(mass[:, None], 1e-12, None)
    return _l2_rows(means)


def cosine_ground_cost(topic_means) -> np.ndarray:
    """Cosine distance between topic means (k × k, zero diagonal, ≥ 0)."""
    C = _l2_rows(_as_2d("topic_means", topic_means))
    M = 1.0 - C @ C.T
    np.fill_diagonal(M, 0.0)
    return np.clip(M, 0.0, None)


def emd_distance_matrix(P, ground_cost) -> np.ndarray:
    """Pairwise Earth Mover's Distance between rows of *P* under *ground_cost*."""
    ot = _require_ot()
    P = np.ascontiguousarray(_as_2d("P", P), dtype=np.float64)
    M = np.ascontiguousarray(_as_2d("ground_cost", ground_cost), dtype=np.float64)
    n = P.shape[0]
    D = np.zeros((n, n), dtype=float)
    for i in range(n):
        a = np.ascontiguousarray(P[i], dtype=np.float64)
        for j in range(i + 1, n):
            b = np.ascontiguousarray(P[j], dtype=np.float64)
            D[i, j] = D[j, i] = float(ot.emd2(a, b, M))
    return D


def classical_mds(emd_matrix, n_components: int = 2) -> dict[str, Any]:
    """Classical (Torgerson) MDS / principal coordinates analysis."""
    D = _as_2d("emd_matrix", emd_matrix)
    n = D.shape[0]
    if n == 0:
        return {
            "coords": np.zeros((0, int(n_components))),
            "eigenvalues": np.array([]),
            "explained": np.zeros((int(n_components),)),
            "negative_ratio": 0.0,
        }
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(B)
    order = np.argsort(w)[::-1]
    w, V = w[order], V[:, order]
    pos = w > 1e-12
    pos_sum = float(w[pos].sum()) if np.any(pos) else 1.0
    full = V[:, pos] * np.sqrt(w[pos]) if np.any(pos) else np.zeros((n, 0))
    k = int(n_components)
    coords = np.zeros((n, k))
    take = min(k, full.shape[1])
    if take:
        coords[:, :take] = full[:, :take]
    explained = np.zeros(k)
    if take:
        explained[:take] = w[:take] / pos_sum
    return {
        "coords": coords,
        "eigenvalues": w,
        "explained": explained,
        "negative_ratio": float(-w[w < -1e-12].sum() / pos_sum),
        "full_coords": full,
    }


def _pseudo_f(D2: np.ndarray, groups: np.ndarray) -> tuple[float, float]:
    n = len(groups)
    labels = np.unique(groups)
    a = len(labels)
    if a < 2 or n <= a:
        return float("nan"), 0.0
    iu = np.triu_indices(n, 1)
    ss_total = D2[iu].sum() / n
    ss_within = 0.0
    for g in labels:
        idx = np.where(groups == g)[0]
        if len(idx) > 1:
            sub = D2[np.ix_(idx, idx)]
            ss_within += sub[np.triu_indices(len(idx), 1)].sum() / len(idx)
    ss_between = ss_total - ss_within
    denom = ss_within / (n - a)
    if denom <= 0:
        return float("nan"), 0.0
    f = (ss_between / (a - 1)) / denom
    return float(f), float(ss_between / ss_total) if ss_total else 0.0


def permanova(
    emd_matrix, groups: Sequence, n_perm: int = 999, seed: int = 0
) -> dict[str, float]:
    """One-way PERMANOVA on a distance matrix."""
    groups = np.asarray(list(groups))
    D2 = _as_2d("emd_matrix", emd_matrix) ** 2
    f_obs, r2 = _pseudo_f(D2, groups)
    n_perm = int(n_perm)
    rng = np.random.default_rng(int(seed))
    if not np.isfinite(f_obs) or n_perm < 1:
        p_value = 1.0
    else:
        exceed = sum(
            _pseudo_f(D2, rng.permutation(groups))[0] >= f_obs
            for _ in range(n_perm)
        )
        p_value = (1 + exceed) / (1 + n_perm)
    return {
        "pseudo_F": f_obs,
        "R2": r2,
        "p_value": float(p_value),
        "n_docs": int(len(groups)),
        "n_groups": int(len(np.unique(groups))),
        "n_perm": n_perm,
    }


def permdisp(
    emd_matrix, groups: Sequence, n_perm: int = 999, seed: int = 0
) -> dict[str, Any]:
    """Test whether groups differ in multivariate dispersion."""
    groups = np.asarray(list(groups))
    X = classical_mds(emd_matrix)["full_coords"]
    if X.size == 0:
        X = np.zeros((len(groups), 1))
    labels = np.unique(groups)
    z = np.zeros(len(groups))
    for g in labels:
        idx = groups == g
        centroid = X[idx].mean(axis=0) if idx.any() else 0.0
        z[idx] = np.linalg.norm(X[idx] - centroid, axis=1)

    def _anova_f(values, grp):
        if len(labels) < 2 or len(values) <= len(labels):
            return float("nan")
        grand = values.mean()
        ssb = sum(
            (grp == g).sum() * (values[grp == g].mean() - grand) ** 2
            for g in labels
        )
        ssw = sum(
            ((values[grp == g] - values[grp == g].mean()) ** 2).sum()
            for g in labels
        )
        denom = ssw / (len(values) - len(labels))
        if denom <= 0:
            return float("nan")
        return (ssb / (len(labels) - 1)) / denom

    f_obs = _anova_f(z, groups)
    n_perm = int(n_perm)
    rng = np.random.default_rng(int(seed))
    if not np.isfinite(f_obs) or n_perm < 1:
        p_value = 1.0
    else:
        exceed = sum(
            _anova_f(z, rng.permutation(groups)) >= f_obs for _ in range(n_perm)
        )
        p_value = (1 + exceed) / (1 + n_perm)
    return {
        "F": f_obs,
        "p_value": float(p_value),
        "n_perm": n_perm,
        "mean_distance_to_centroid": {
            str(g): float(z[groups == g].mean()) for g in labels
        },
    }


def axis_correlates(
    mds_coords,
    P,
    topic_labels: Mapping | None = None,
    top: int = 5,
) -> list[dict[str, Any]]:
    """Topics whose document shares correlate most with each MDS axis."""
    coords = np.asarray(mds_coords, dtype=float)
    P = _as_2d("P", P)
    if coords.ndim != 2 or coords.shape[0] != P.shape[0]:
        raise ValueError("mds_coords and P must share a document axis")
    labels = topic_labels or {}
    rows: list[dict[str, Any]] = []
    for a in range(coords.shape[1]):
        r = np.array(
            [
                float(np.corrcoef(coords[:, a], P[:, k])[0, 1])
                if P[:, k].std() > 0 and coords[:, a].std() > 0
                else 0.0
                for k in range(P.shape[1])
            ]
        )
        r = np.nan_to_num(r, nan=0.0)
        order = np.argsort(r)
        for end, idxs in (("negative", order[:top]), ("positive", order[::-1][:top])):
            for k in idxs:
                key = f"T{k}"
                label = labels.get(key, labels.get(k, labels.get(str(k), key)))
                rows.append(
                    {
                        "axis": a + 1,
                        "end": end,
                        "topic_id": int(k),
                        "label": str(label),
                        "r": float(r[k]),
                    }
                )
    return rows


def distance_tests_markdown(
    permanova_res: Mapping | None,
    permdisp_res: Mapping | None,
    correlates: Sequence[Mapping] | None = None,
    *,
    note: str = "",
) -> str:
    """Markdown summary for the 04_distance review pane."""
    lines: list[str] = []
    if note:
        lines.append(str(note).rstrip() + "\n")
    if permanova_res:
        lines.append("### PERMANOVA")
        lines.append(
            f"pseudo-F = {permanova_res.get('pseudo_F', '—')}, "
            f"R² = {permanova_res.get('R2', '—')}, "
            f"p = {permanova_res.get('p_value', '—')} "
            f"(n_perm={permanova_res.get('n_perm', '—')}, "
            f"n_docs={permanova_res.get('n_docs', '—')}, "
            f"n_groups={permanova_res.get('n_groups', '—')})."
        )
        lines.append("")
    if permdisp_res:
        lines.append("### PERMDISP")
        lines.append(
            f"F = {permdisp_res.get('F', '—')}, "
            f"p = {permdisp_res.get('p_value', '—')}."
        )
        spread = permdisp_res.get("mean_distance_to_centroid") or {}
        for group, dist in spread.items():
            lines.append(f"- {group}: mean distance to centroid {dist}")
        lines.append("")
    if correlates:
        lines.append("### Axis correlates")
        for row in correlates:
            lines.append(
                f"- MDS{row.get('axis')} {row.get('end')}: "
                f"{row.get('label')} (r={row.get('r')})"
            )
        lines.append("")
    return "\n".join(lines).strip() + ("\n" if lines else "")


def _groups_for_docs(
    docs_kept: Sequence[str],
    *,
    groups=None,
    doc_ids=None,
    doc_group: Mapping | None = None,
) -> list[str] | None:
    if doc_group:
        return [str(doc_group.get(d, doc_group.get(str(d), ""))) for d in docs_kept]
    if groups is None:
        return None
    g_list = [str(x) if x is not None else "" for x in list(groups)]
    if len(g_list) == len(docs_kept):
        return g_list
    phrase_ids = [str(d) for d in list(doc_ids or [])]
    if phrase_ids and len(g_list) == len(phrase_ids):
        first: dict[str, str] = {}
        for doc, grp in zip(phrase_ids, g_list):
            first.setdefault(doc, grp)
        return [first.get(d, "") for d in docs_kept]
    return None


def run_document_distance_analysis(
    embeddings,
    doc_ids,
    responsibilities,
    *,
    groups=None,
    doc_group: Mapping | None = None,
    topic_labels: Mapping | None = None,
    min_mass: float = 50.0,
    n_perm: int = 999,
    seed: int = 0,
    n_components: int = 2,
    group_field: str | None = None,
    cluster_ids=None,
    **_kwargs,
) -> tuple:
    """Façade: histograms → cost → EMD → MDS → tests → Plotly specs.

    Return order matches ``04_distance`` ``field:`` list.
    When ``responsibilities`` are codebook-level (VQ), pass ``cluster_ids``
    (phrase → cluster) and phrase embeddings; membership is ``QR``.
    """
    from .grain_catalogue import as_embedding_matrix

    X = as_embedding_matrix(embeddings)
    R = _as_2d("responsibilities", responsibilities)
    if R.shape[0] != X.shape[0]:
        if cluster_ids is None:
            raise ValueError(
                f"responsibilities rows {R.shape[0]} != embeddings {X.shape[0]}; "
                "pass cluster_ids from the VQ codebook to expand QR"
            )
        from .vq import expand_vq_responsibilities

        R = expand_vq_responsibilities(cluster_ids, R)
        if R.shape[0] != X.shape[0]:
            raise ValueError(
                f"expanded responsibilities rows {R.shape[0]} != "
                f"embeddings {X.shape[0]}"
            )
    P, docs, mass = document_soft_topic_distributions(
        doc_ids, R, min_mass=min_mass
    )
    means = topic_means_from_responsibilities(X, R)
    cost = cosine_ground_cost(means)
    note = ""
    try:
        D = emd_distance_matrix(P, cost) if len(docs) else np.zeros((0, 0))
    except ImportError as exc:
        note = str(exc)
        D = np.zeros((len(docs), len(docs)))
    mds = classical_mds(D, n_components=int(n_components))
    group_labels = _groups_for_docs(
        docs, groups=groups, doc_ids=doc_ids, doc_group=doc_group
    )
    perm_res: dict[str, Any] = {}
    disp_res: dict[str, Any] = {}
    correlates: list[dict[str, Any]] = []
    if group_labels and len(docs) and not note:
        perm_res = permanova(D, group_labels, n_perm=n_perm, seed=seed)
        disp_res = permdisp(D, group_labels, n_perm=n_perm, seed=seed)
        correlates = axis_correlates(mds["coords"], P, topic_labels=topic_labels)
    elif group_labels is None:
        note = (note + "\n" if note else "") + (
            "No group labels: pack a `groups` array or join `doc_group`. "
            f"group_field={group_field!r}."
        )
    md = distance_tests_markdown(perm_res, disp_res, correlates, note=note)

    from ...util.plotly_figures import (
        axis_correlate_bars_spec,
        doc_mds_plotly_spec,
        emd_heatmap_spec,
        topic_document_heatmap_spec,
    )

    mds_spec = doc_mds_plotly_spec(
        mds["coords"], docs, groups=group_labels, topic_labels=topic_labels
    )
    heat_spec = topic_document_heatmap_spec(P, docs, topic_labels=topic_labels)
    emd_spec = emd_heatmap_spec(D, docs)
    bars_spec = axis_correlate_bars_spec(correlates)

    return (
        _jsonable(P),
        _jsonable(means),
        _jsonable(mass),
        list(docs),
        _jsonable(cost),
        _jsonable(D),
        _jsonable(mds["coords"]),
        _jsonable(mds["explained"]),
        _jsonable(perm_res),
        _jsonable(disp_res),
        _jsonable(correlates),
        md,
        mds_spec,
        heat_spec,
        emd_spec,
        bars_spec,
    )
