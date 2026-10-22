"""Plotly.js figure builders for soft-topic Assess views.

Geometry (planes, covariances, responsibilities) comes from
``referia.assess.compute.mppca``. This module only turns that geometry into
figure JSON for the interactive viewer.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from referia.assess.compute.mppca import (
    component_local_plane,
    responsibilities_to_labels,
    topic_keys,
)

__all__ = [
    "local_uq_plotly_spec",
    "proposed_split_plotly_spec",
    "relabel_proposed_split_plotly_spec",
    "doc_mds_plotly_spec",
    "topic_document_heatmap_spec",
    "chapter_lens_radar_spec",
    "emd_heatmap_spec",
    "axis_correlate_bars_spec",
    "cluster_pca_plotly_spec",
    "cluster_dendrogram_plotly_spec",
    "vq_projection_walk_plotly_spec",
    "stiefel_step_scale",
]


def _ellipse_polyline(
    center: np.ndarray,
    cov2: np.ndarray,
    *,
    n: int = 64,
) -> tuple[list[float], list[float]] | None:
    """Sample a 1-SD ellipse in the plane as closed polylines (JSON-safe)."""
    c = np.asarray(center, float).ravel()[:2]
    C = np.asarray(cov2, float)
    if c.size < 2 or C.shape != (2, 2) or not np.isfinite(C).all():
        return None
    try:
        vals, vecs = np.linalg.eigh(C)
    except np.linalg.LinAlgError:
        return None
    vals = np.clip(vals, 0.0, None)
    if float(vals.sum()) <= 0:
        return None
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=True)
    circle = np.column_stack([np.cos(t), np.sin(t)])
    pts = circle @ (vecs * np.sqrt(vals)[None, :]).T + c
    return pts[:, 0].tolist(), pts[:, 1].tolist()


_UQ_PALETTE = ("#2a78d6", "#eb6834", "#3d9b8f", "#8b5cf6", "#c45c26", "#5a6a7a")


def local_uq_plotly_spec(
    embeddings: np.ndarray,
    responsibilities: np.ndarray,
    *,
    focus: int,
    component_fits: Sequence[dict] | None = None,
    phrases: Sequence[Any] | None = None,
    sigma2: float | None = None,
    title: str | None = None,
    topic_prefix: str = "T",
    hover_max_chars: int = 72,
) -> dict[str, Any] | None:
    """Bishop–Tipping local ``U_q`` panel as Plotly.js figure JSON.

    Every phrase is projected onto the focus component's local plane. Markers
    are uniform solid dark — this panel *is* the component view, so soft mass
    is not used for colour or size (chrome must not apply ``responsibility_ink``
    on top). ``customdata`` still carries phrase / topic / responsibilities for
    click bindings.

    Returns ``None`` when the plane cannot be formed.
    """
    X = np.asarray(embeddings, float)
    R = np.asarray(responsibilities, float)
    focus = int(focus)
    if X.ndim != 2 or len(X) < 2 or R.ndim != 2 or R.shape[0] != len(X):
        return None
    if focus < 0 or focus >= R.shape[1]:
        return None
    if not np.isfinite(X).all() or not np.isfinite(R).all():
        return None

    cf = None
    if component_fits is not None and 0 <= focus < len(component_fits):
        cf = component_fits[focus]
    plane = component_local_plane(X, R[:, focus], cf, q_viz=2)
    if plane is None:
        return None
    mu, U, scales, q_model = plane
    xy = (X - mu) @ U
    if not np.isfinite(xy).all():
        return None

    k = R.shape[1]
    keys = topic_keys(k, prefix=topic_prefix)
    labels = responsibilities_to_labels(R)
    mass = np.clip(R[:, focus], 0.0, 1.0)
    phrase_list: list[str] = []
    if phrases is None:
        phrase_list = [f"phrase {i}" for i in range(len(X))]
    else:
        phrase_list = [str(p) for p in phrases]
        if len(phrase_list) != len(X):
            phrase_list = (phrase_list + ["—"] * len(X))[: len(X)]

    order = np.arange(len(X), dtype=int)
    hover_short: list[str] = []
    customdata: list[dict[str, Any]] = []
    for i in order:
        text = " ".join(phrase_list[i].split()) or "—"
        short = text if len(text) <= hover_max_chars else text[: hover_max_chars - 1] + "…"
        hover_short.append(short)
        lab = int(labels[i])
        topic = keys[lab] if 0 <= lab < k else keys[0]
        customdata.append(
            {
                "topic": topic,
                "phrase": text,
                "responsibilities": {
                    keys[j]: float(R[i, j]) for j in range(k)
                },
            }
        )

    if title is None:
        title = f"Topic {keys[focus]} — local U_q (model q={q_model})"

    s0 = float(scales[0]) if len(scales) > 0 else 0.0
    s1 = float(scales[1]) if len(scales) > 1 else 0.0
    if sigma2 is not None and float(sigma2) > 0:
        s0 = float(np.sqrt(s0 ** 2 + float(sigma2)))
        s1 = float(np.sqrt(s1 ** 2 + float(sigma2)))

    colour = _UQ_PALETTE[focus % len(_UQ_PALETTE)]
    traces: list[dict[str, Any]] = [
        {
            "type": "scatter",
            "mode": "markers",
            "name": "phrases",
            "x": xy[order, 0].tolist(),
            "y": xy[order, 1].tolist(),
            "text": hover_short,
            "customdata": customdata,
            "hovertemplate": "%{text}<extra></extra>",
            "marker": {
                "size": 5,
                "color": "#0b0b0b",
                "opacity": 1.0,
                "line": {"width": 0},
            },
            "showlegend": False,
        }
    ]
    poly = _ellipse_polyline(
        np.zeros(2),
        np.diag([max(s0, 1e-9) ** 2, max(s1, 1e-9) ** 2]),
    )
    if poly is not None and (s0 > 0 or s1 > 0):
        xs, ys = poly
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": "1-SD local U_q",
                "x": xs,
                "y": ys,
                "line": {"color": colour, "width": 1.5},
                "hoverinfo": "skip",
                "showlegend": True,
            }
        )
    traces.append(
        {
            "type": "scatter",
            "mode": "markers",
            "name": "μ",
            "x": [0.0],
            "y": [0.0],
            "marker": {
                "symbol": "x",
                "size": 14,
                "color": colour,
                "line": {"width": 1.2, "color": "#0b0b0b"},
            },
            "hoverinfo": "skip",
            "showlegend": False,
        }
    )

    w = mass
    wsum = float(w.sum()) or 1.0
    mid = (xy * w[:, None]).sum(axis=0) / wsum
    spread = np.sqrt((((xy - mid) ** 2) * w[:, None]).sum(axis=0) / wsum)
    half = float(max(1.5 * float(np.max(spread)), 0.5))

    return {
        "data": traces,
        "layout": {
            "title": {
                "text": title,
                "x": 0.0,
                "xanchor": "left",
                "font": {"size": 14, "color": "#0b0b0b"},
            },
            "xaxis": {
                "title": "local PC1 (U_q)",
                "range": [float(mid[0] - half), float(mid[0] + half)],
                "scaleanchor": "y",
                "scaleratio": 1,
                "gridcolor": "#e4e3df",
                "zeroline": False,
            },
            "yaxis": {
                "title": "local PC2 (U_q)",
                "range": [float(mid[1] - half), float(mid[1] + half)],
                "gridcolor": "#e4e3df",
                "zeroline": False,
            },
            "plot_bgcolor": "white",
            "paper_bgcolor": "white",
            "margin": {"l": 50, "r": 20, "t": 50, "b": 50},
            "height": 460,
            "width": 520,
            "legend": {
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "x": 0,
            },
        },
    }


def _ppca_cov(component_fit: dict, sigma2: float) -> np.ndarray:
    """Ambient covariance for a PPCA component: ``U diag(λ) Uᵀ + σ² I``."""
    mu = np.asarray(component_fit["mu"], float).ravel()
    d = int(mu.shape[0])
    Cov = np.eye(d) * float(max(sigma2, 0.0))
    U = np.asarray(component_fit.get("U_q"), float)
    lam = np.asarray(component_fit.get("lambdas_q"), float).ravel()
    if U.ndim == 2 and U.shape[0] == d and U.size and lam.size:
        q = min(U.shape[1], len(lam))
        if q > 0:
            Cov = Cov + (U[:, :q] * lam[:q]) @ U[:, :q].T
    return Cov


def _clip_label(text: str, n: int = 28) -> str:
    """Truncate display labels for Plotly legends / titles.

    When the string ends with a Propose placeholder
    (``→ (unnamed N)``), keep that suffix so siblings with a long shared
    parent prefix stay distinguishable after clipping.
    """
    import re

    s = " ".join(str(text).split())
    if len(s) <= n:
        return s
    m = re.search(r"(→\s*\(unnamed\s+\d+\))\s*$", s, flags=re.IGNORECASE)
    if m:
        suffix = m.group(1)
        keep = n - len(suffix) - 1  # room for ellipsis
        if keep >= 6:
            return s[:keep].rstrip() + "…" + suffix
    return s[: max(1, n - 1)] + "…"


def relabel_proposed_split_plotly_spec(
    spec: Any,
    *,
    child_labels: Sequence[str],
    parent_label: str | None = None,
) -> Any:
    """Return a deep copy of a proposed-split figure with display names updated.

    Trace layout matches :func:`proposed_split_plotly_spec`: phrases, parent
    solid ellipse, parent μ, then per child dashed ellipse + μ text marker.
    Used after LLM naming so the pending overlay stops showing
    ``(unnamed…)`` placeholders without rebuilding geometry.
    """
    import copy
    import re

    if not isinstance(spec, dict) or not child_labels:
        return spec
    out = copy.deepcopy(spec)
    parent_name = parent_label or "parent"
    layout = out.get("layout")
    if isinstance(layout, dict):
        title = layout.get("title")
        old_text = ""
        if isinstance(title, dict):
            old_text = str(title.get("text") or "")
        elif isinstance(title, str):
            old_text = title
        q_m = re.search(r"\(q=\d+\)", old_text)
        q_bit = f" {q_m.group(0)}" if q_m else ""
        new_text = (
            f"Proposed split of «{_clip_label(parent_name, 40)}» "
            f"— parent U_q{q_bit}"
        )
        if isinstance(title, dict):
            titled = dict(title)
            titled["text"] = new_text
            layout["title"] = titled
        else:
            layout["title"] = {
                "text": new_text,
                "x": 0.0,
                "xanchor": "left",
                "font": {"size": 14, "color": "#0b0b0b"},
            }

    data = out.get("data")
    if not isinstance(data, list):
        return out

    child_i = 0
    for tr in data:
        if not isinstance(tr, dict):
            continue
        name = str(tr.get("name") or "")
        mode = str(tr.get("mode") or "")
        line = tr.get("line") if isinstance(tr.get("line"), dict) else {}
        dash = line.get("dash")

        if name.startswith("parent «"):
            tr["name"] = f"parent «{_clip_label(parent_name, 20)}»"
            continue
        if name == "parent μ" or name == "phrases":
            continue
        if dash == "dash" and mode == "lines":
            if child_i < len(child_labels):
                short = _clip_label(str(child_labels[child_i]), 28)
                tr["name"] = short
            child_i += 1
            continue
        if mode == "markers+text" and name.endswith(" μ"):
            idx = child_i - 1
            if 0 <= idx < len(child_labels):
                short = _clip_label(str(child_labels[idx]), 28)
                tr["name"] = f"{short} μ"
                tr["text"] = [short]
            continue
    return out


def proposed_split_plotly_spec(
    embeddings: np.ndarray,
    *,
    parent_mass: np.ndarray,
    parent_component_fit: dict,
    child_component_fits: Sequence[dict],
    responsibilities: np.ndarray | None = None,
    phrases: Sequence[Any] | None = None,
    child_labels: Sequence[str] | None = None,
    parent_label: str | None = None,
    sigma2: float = 0.0,
    title: str | None = None,
    hover_max_chars: int = 72,
) -> dict[str, Any] | None:
    """Proposed split overlay: parent ellipse + child ellipses in parent ``U_q``.

    Points are uniform solid dark — the proposal is about the child ellipses,
    not responsibility ink. Solid muted 1-SD ellipse is the combined parent;
    dashed coloured ellipses are the proposed children (local cov projected
    into the parent plane).
    """
    X = np.asarray(embeddings, float)
    mass = np.asarray(parent_mass, float).ravel()
    if X.ndim != 2 or len(X) < 2 or mass.shape[0] != len(X):
        return None
    if not child_component_fits:
        return None
    if not np.isfinite(X).all() or not np.isfinite(mass).all():
        return None

    plane = component_local_plane(X, mass, parent_component_fit, q_viz=2)
    if plane is None:
        return None
    mu, U, _scales, q_model = plane
    xy = (X - mu) @ U
    if not np.isfinite(xy).all():
        return None

    parent_name = parent_label or "parent"
    if title is None:
        title = (
            f"Proposed split of «{_clip_label(parent_name, 40)}» "
            f"— parent U_q (q={q_model})"
        )

    phrase_list: list[str]
    if phrases is None:
        phrase_list = [f"phrase {i}" for i in range(len(X))]
    else:
        phrase_list = [str(p) for p in phrases]
        if len(phrase_list) != len(X):
            phrase_list = (phrase_list + ["—"] * len(X))[: len(X)]

    R = None
    if responsibilities is not None:
        R = np.asarray(responsibilities, float)
        if R.ndim != 2 or R.shape[0] != len(X):
            R = None
    keys = topic_keys(R.shape[1]) if R is not None else []
    labels = responsibilities_to_labels(R) if R is not None else None

    # Stable draw order; colour/size do not encode responsibilities.
    order = np.arange(len(X), dtype=int)
    hover_short: list[str] = []
    customdata: list[dict[str, Any]] = []
    for i in order:
        text = " ".join(phrase_list[i].split()) or "—"
        short = text if len(text) <= hover_max_chars else text[: hover_max_chars - 1] + "…"
        hover_short.append(short)
        if R is not None and labels is not None:
            lab = int(labels[i])
            topic = keys[lab] if 0 <= lab < len(keys) else (keys[0] if keys else "T0")
            customdata.append(
                {
                    "topic": topic,
                    "phrase": text,
                    "responsibilities": {
                        keys[j]: float(R[i, j]) for j in range(len(keys))
                    },
                }
            )
        else:
            customdata.append({"topic": "", "phrase": text, "responsibilities": {}})

    traces: list[dict[str, Any]] = [
        {
            "type": "scatter",
            "mode": "markers",
            "name": "phrases",
            "x": xy[order, 0].tolist(),
            "y": xy[order, 1].tolist(),
            "text": hover_short,
            "customdata": customdata,
            "hovertemplate": "%{text}<extra></extra>",
            "marker": {
                "size": 5,
                "color": "#0b0b0b",
                "opacity": 1.0,
                "line": {"width": 0},
            },
            "showlegend": False,
        }
    ]

    # Combined parent (solid) at the origin of the parent plane.
    Cov_p = _ppca_cov(parent_component_fit, float(sigma2))
    C2_p = U.T @ Cov_p @ U
    parent_poly = _ellipse_polyline(np.zeros(2), C2_p)
    if parent_poly is not None:
        xs, ys = parent_poly
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": f"parent «{_clip_label(parent_name, 20)}»",
                "x": xs,
                "y": ys,
                "line": {"color": "#8a8680", "width": 2.0, "dash": "solid"},
                "hoverinfo": "skip",
                "showlegend": True,
            }
        )
    traces.append(
        {
            "type": "scatter",
            "mode": "markers",
            "name": "parent μ",
            "x": [0.0],
            "y": [0.0],
            "marker": {
                "symbol": "x",
                "size": 12,
                "color": "#8a8680",
                "line": {"width": 1.2, "color": "#0b0b0b"},
            },
            "hoverinfo": "skip",
            "showlegend": False,
        }
    )

    anchors: list[np.ndarray] = [np.zeros(2)]
    for j, cf in enumerate(child_component_fits):
        colour = _UQ_PALETTE[j % len(_UQ_PALETTE)]
        mu_c = np.asarray(cf["mu"], float).ravel()
        center = (mu_c - mu) @ U
        Cov = _ppca_cov(cf, float(sigma2))
        C2 = U.T @ Cov @ U
        name = None
        if child_labels is not None and j < len(child_labels):
            name = str(child_labels[j])
        if not name:
            name = f"child {j}"
        short = _clip_label(name, 28)
        poly = _ellipse_polyline(center, C2)
        if poly is not None:
            xs, ys = poly
            traces.append(
                {
                    "type": "scatter",
                    "mode": "lines",
                    "name": short,
                    "x": xs,
                    "y": ys,
                    "line": {"color": colour, "width": 1.8, "dash": "dash"},
                    "hoverinfo": "skip",
                    "showlegend": True,
                }
            )
        traces.append(
            {
                "type": "scatter",
                "mode": "markers+text",
                "name": f"{short} μ",
                "x": [float(center[0])],
                "y": [float(center[1])],
                "text": [short],
                "textposition": "top right",
                "textfont": {"size": 10, "color": colour},
                "marker": {
                    "symbol": "x",
                    "size": 14,
                    "color": colour,
                    "line": {"width": 1.2, "color": "#0b0b0b"},
                },
                "hoverinfo": "skip",
                "showlegend": False,
            }
        )
        if np.isfinite(center).all():
            anchors.append(np.asarray(center, float).ravel()[:2])

    w = np.clip(mass, 0.0, None)
    wsum = float(w.sum()) or 1.0
    mid = (xy * w[:, None]).sum(axis=0) / wsum
    spread = np.sqrt((((xy - mid) ** 2) * w[:, None]).sum(axis=0) / wsum)
    half = float(max(1.5 * float(np.max(spread)), 0.5))
    for a in anchors:
        half = max(half, float(np.max(np.abs(a - mid))) + 0.3)

    return {
        "data": traces,
        "layout": {
            "title": {
                "text": title,
                "x": 0.0,
                "xanchor": "left",
                "font": {"size": 14, "color": "#0b0b0b"},
            },
            "xaxis": {
                "title": "parent local PC1 (U_q)",
                "range": [float(mid[0] - half), float(mid[0] + half)],
                "scaleanchor": "y",
                "scaleratio": 1,
                "gridcolor": "#e4e3df",
                "zeroline": False,
            },
            "yaxis": {
                "title": "parent local PC2 (U_q)",
                "range": [float(mid[1] - half), float(mid[1] + half)],
                "gridcolor": "#e4e3df",
                "zeroline": False,
            },
            "plot_bgcolor": "white",
            "paper_bgcolor": "white",
            "margin": {"l": 50, "r": 20, "t": 50, "b": 50},
            "height": 460,
            "width": 520,
            "legend": {
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "x": 0,
            },
        },
    }


_GROUP_PALETTE = ("#2a78d6", "#eb6834", "#3d9b8f", "#8b5cf6", "#c45c26", "#5a6a7a")


def _topic_label(k: int, topic_labels: dict | None) -> str:
    labels = topic_labels or {}
    key = f"T{k}"
    return str(labels.get(key, labels.get(k, labels.get(str(k), key))))


def _display_docs(
    doc_ids: Sequence[Any], doc_labels: Sequence[Any] | None = None
) -> tuple[list[str], list[str]]:
    docs = [str(d) for d in list(doc_ids)]
    if doc_labels is None:
        return docs, docs
    labels = [str(x) for x in list(doc_labels)]
    if len(labels) != len(docs):
        return docs, docs
    return docs, labels


def _leaf_order(X: np.ndarray) -> np.ndarray:
    """Optimal leaf order of rows under average-linkage cosine clustering.

    This is the microarray seriation: hierarchical clustering of the vectors,
    then Bar-Joseph leaf order so adjacent leaves are as similar as the
    dendrogram allows. n ≤ 2 keeps the given order. Missing scipy falls back
    to the original order.
    """
    arr = np.asarray(X, float)
    if arr.ndim != 2:
        return np.arange(0)
    n = int(arr.shape[0])
    if n <= 2:
        return np.arange(n)
    try:
        from scipy.cluster.hierarchy import (
            leaves_list,
            linkage,
            optimal_leaf_ordering,
        )
        from scipy.spatial.distance import pdist
    except ImportError:
        return np.arange(n)
    y = pdist(arr, metric="cosine")
    y = np.nan_to_num(np.asarray(y, float), nan=1.0, posinf=1.0, neginf=1.0)
    if not np.any(y > 0):
        return np.arange(n)
    Z = linkage(y, method="average")
    try:
        Z = optimal_leaf_ordering(Z, y)
    except (ValueError, FloatingPointError):
        pass
    return np.asarray(leaves_list(Z), dtype=int)


def _seriate_share_matrix(
    P,
    doc_ids: Sequence[Any],
    *,
    topic_labels=None,
    doc_labels: Sequence[Any] | None = None,
    reorder: bool = True,
) -> tuple[np.ndarray, list[str], list[str], list[str]]:
    """Reorder chapters and lenses so similar share profiles are adjacent."""
    arr = np.asarray(P, float)
    docs, labels = _display_docs(doc_ids, doc_labels)
    if arr.ndim != 2:
        return arr, docs, labels, []
    k = int(arr.shape[1])
    col_ids = list(range(k))
    if reorder and arr.shape[0] == len(docs) and k > 0:
        row_ord = _leaf_order(arr)
        col_ord = _leaf_order(arr.T)
        arr = arr[np.ix_(row_ord, col_ord)]
        docs = [docs[i] for i in row_ord]
        labels = [labels[i] for i in row_ord]
        col_ids = [int(j) for j in col_ord]
    x = [_topic_label(j, topic_labels) for j in col_ids]
    return arr, docs, labels, x


def doc_mds_plotly_spec(
    mds_coords,
    doc_ids: Sequence[Any],
    *,
    groups: Sequence[Any] | None = None,
    topic_labels=None,
    title: str | None = None,
    doc_labels: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """MDS scatter; ``customdata.doc`` for CIP-0011 click → ``selected_doc``."""
    coords = np.asarray(mds_coords, float)
    docs, labels = _display_docs(doc_ids, doc_labels)
    if coords.ndim != 2 or coords.shape[0] != len(docs):
        return {"data": [], "layout": {"title": {"text": title or "Document MDS"}}}
    if coords.shape[1] < 2:
        padded = np.zeros((len(docs), 2))
        padded[:, : coords.shape[1]] = coords
        coords = padded
    grp = [
        str(g) if g is not None else ""
        for g in (list(groups) if groups is not None else [""] * len(docs))
    ]
    if len(grp) != len(docs):
        grp = [""] * len(docs)
    uniq: list[str] = []
    for g in grp:
        if g not in uniq:
            uniq.append(g)
    color_of = {
        g: _GROUP_PALETTE[i % len(_GROUP_PALETTE)] for i, g in enumerate(uniq)
    }
    traces = []
    for g in uniq:
        idx = [i for i, val in enumerate(grp) if val == g]
        customdata = [
            {"doc": docs[i], "group": grp[i], "label": labels[i]} for i in idx
        ]
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": g or "document",
                "x": [float(coords[i, 0]) for i in idx],
                "y": [float(coords[i, 1]) for i in idx],
                "customdata": customdata,
                "hovertemplate": "%{customdata.label}<extra></extra>",
                "marker": {
                    "size": 10,
                    "color": color_of[g],
                    "line": {"width": 1, "color": "#ffffff"},
                },
            }
        )
    return {
        "data": traces,
        "layout": {
            "title": {
                "text": title or "Document MDS",
                "x": 0.0,
                "xanchor": "left",
                "font": {"size": 14, "color": "#0b0b0b"},
            },
            "xaxis": {"title": "MDS1", "gridcolor": "#e4e3df", "zeroline": False},
            "yaxis": {"title": "MDS2", "gridcolor": "#e4e3df", "zeroline": False},
            "plot_bgcolor": "white",
            "paper_bgcolor": "white",
            "margin": {"l": 50, "r": 20, "t": 50, "b": 50},
            "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        },
    }


def topic_document_heatmap_spec(
    P,
    doc_ids: Sequence[Any],
    *,
    topic_labels=None,
    title: str | None = None,
    doc_labels: Sequence[Any] | None = None,
    reorder: bool = True,
) -> dict[str, Any]:
    """Heatmap of chapter × lens soft histograms.

    Rows and columns are leaf-ordered (average-linkage cosine, optimal
    leaf order) so similar share profiles sit next to each other — the
    microarray seriation. Pass ``reorder=False`` to keep pack order.
    """
    arr, docs, labels, x = _seriate_share_matrix(
        P,
        doc_ids,
        topic_labels=topic_labels,
        doc_labels=doc_labels,
        reorder=reorder,
    )
    return {
        "data": [
            {
                "type": "heatmap",
                "z": arr.tolist() if arr.ndim == 2 else [],
                "x": x,
                "y": labels,
                "hovertemplate": "%{y} · %{x}: %{z:.3f}<extra></extra>",
                "customdata": [[{"doc": d} for _ in x] for d in docs],
                "colorscale": "RdBu_r",
            }
        ],
        "layout": {
            "title": {
                "text": title or "Lens share by chapter",
                "x": 0.0,
                "xanchor": "left",
                "font": {"size": 14, "color": "#0b0b0b"},
            },
            "xaxis": {"title": "Lens", "tickangle": -35, "automargin": True},
            "yaxis": {"title": "Chapter", "autorange": "reversed", "automargin": True},
            "plot_bgcolor": "white",
            "paper_bgcolor": "white",
            "margin": {"l": 200, "r": 20, "t": 50, "b": 140},
        },
    }


def chapter_lens_radar_spec(
    P,
    doc_ids: Sequence[Any],
    *,
    topic_labels=None,
    title: str | None = None,
    doc_labels: Sequence[Any] | None = None,
    reorder: bool = True,
) -> dict[str, Any]:
    """One polar trace per chapter: lens shares, matching pub-dialogue radar.

    Spoke order matches the leaf-ordered heatmap so the two views agree.
    """
    arr, docs, labels, theta = _seriate_share_matrix(
        P,
        doc_ids,
        topic_labels=topic_labels,
        doc_labels=doc_labels,
        reorder=reorder,
    )
    if arr.ndim != 2 or arr.shape[0] != len(docs) or arr.shape[1] == 0:
        return {
            "data": [],
            "layout": {"title": {"text": title or "Lens share by chapter"}},
        }
    theta_loop = theta + theta[:1]
    peak = float(np.nanmax(arr)) if arr.size else 0.0
    traces = []
    for i, name in enumerate(labels):
        row = [float(v) for v in arr[i]]
        traces.append(
            {
                "type": "scatterpolar",
                "r": row + row[:1],
                "theta": theta_loop,
                "fill": "toself",
                "name": name,
            }
        )
    return {
        "data": traces,
        "layout": {
            "title": {
                "text": title or "Lens share by chapter",
                "x": 0.0,
                "xanchor": "left",
                "font": {"size": 14, "color": "#0b0b0b"},
            },
            "polar": {
                "radialaxis": {
                    "visible": True,
                    "range": [0, max(peak * 1.1, 0.05)],
                }
            },
            "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
            "plot_bgcolor": "white",
            "paper_bgcolor": "white",
            "margin": {"l": 60, "r": 20, "t": 70, "b": 40},
        },
    }


def emd_heatmap_spec(
    emd_matrix,
    doc_ids: Sequence[Any],
    *,
    title: str | None = None,
    doc_labels: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Pairwise EMD heatmap."""
    arr = np.asarray(emd_matrix, float)
    docs, labels = _display_docs(doc_ids, doc_labels)
    return {
        "data": [
            {
                "type": "heatmap",
                "z": arr.tolist() if arr.ndim == 2 else [],
                "x": labels,
                "y": labels,
                "hovertemplate": "%{y} → %{x}: %{z:.3f}<extra></extra>",
                "customdata": [[{"doc": d} for d in docs] for _ in docs],
            }
        ],
        "layout": {
            "title": {
                "text": title or "Pairwise EMD",
                "x": 0.0,
                "xanchor": "left",
                "font": {"size": 14, "color": "#0b0b0b"},
            },
            "xaxis": {"title": "Document"},
            "yaxis": {"title": "Document", "autorange": "reversed"},
            "plot_bgcolor": "white",
            "paper_bgcolor": "white",
            "margin": {"l": 80, "r": 20, "t": 50, "b": 80},
        },
    }


def axis_correlate_bars_spec(
    correlates: Sequence[dict[str, Any]] | None,
    *,
    title: str | None = None,
) -> dict[str, Any]:
    """Bar chart of Pearson r between MDS axes and topic shares."""
    rows = list(correlates or [])
    traces = []
    axes = sorted({int(r.get("axis", 1)) for r in rows}) or [1]
    for axis in axes:
        subset = [
            r
            for r in rows
            if int(r.get("axis", 1)) == axis and r.get("end") == "positive"
        ]
        subset += [
            r
            for r in rows
            if int(r.get("axis", 1)) == axis and r.get("end") == "negative"
        ]
        seen: set[str] = set()
        uniq = []
        for row in subset:
            label = str(row.get("label") or row.get("topic_id"))
            if label in seen:
                continue
            seen.add(label)
            uniq.append(row)
        traces.append(
            {
                "type": "bar",
                "name": f"MDS{axis}",
                "x": [str(r.get("label") or r.get("topic_id")) for r in uniq],
                "y": [float(r.get("r") or 0.0) for r in uniq],
            }
        )
    return {
        "data": traces,
        "layout": {
            "title": {
                "text": title or "MDS axis correlates",
                "x": 0.0,
                "xanchor": "left",
                "font": {"size": 14, "color": "#0b0b0b"},
            },
            "barmode": "group",
            "xaxis": {"title": "Topic"},
            "yaxis": {"title": "Pearson r", "range": [-1, 1]},
            "plot_bgcolor": "white",
            "paper_bgcolor": "white",
            "margin": {"l": 50, "r": 20, "t": 50, "b": 80},
        },
    }


def cluster_pca_plotly_spec(
    embeddings: np.ndarray,
    responsibilities: np.ndarray,
    *,
    focus: int = 0,
    phrases: Sequence[Any] | None = None,
    title: str | None = None,
    topic_prefix: str = "T",
    hover_max_chars: int = 72,
) -> dict[str, Any] | None:
    """2-D PCA scatter of embeddings, colour = MAP cluster (CIP-0019)."""
    from sklearn.decomposition import PCA

    X = np.asarray(embeddings, float)
    R = np.asarray(responsibilities, float)
    if X.ndim != 2 or len(X) < 2 or R.ndim != 2 or R.shape[0] != len(X):
        return None
    if not np.isfinite(X).all() or not np.isfinite(R).all():
        return None
    focus = int(focus)
    k = R.shape[1]
    if k < 1 or focus < 0 or focus >= k:
        return None
    n_comp = 2 if X.shape[1] >= 2 else 1
    xy = PCA(n_components=n_comp, random_state=0).fit_transform(X)
    if n_comp == 1:
        xy = np.column_stack([xy[:, 0], np.zeros(len(X))])
    keys = topic_keys(k, prefix=topic_prefix)
    labels = responsibilities_to_labels(R)
    if phrases is None:
        phrase_list = [f"phrase {i}" for i in range(len(X))]
    else:
        phrase_list = [str(p) for p in phrases]
        if len(phrase_list) != len(X):
            phrase_list = (phrase_list + ["—"] * len(X))[: len(X)]
    traces: list[dict[str, Any]] = []
    for j, key in enumerate(keys):
        mask = labels == j
        if not np.any(mask):
            continue
        idx = np.where(mask)[0]
        hover = []
        custom = []
        for i in idx:
            text = " ".join(phrase_list[i].split()) or "—"
            short = text if len(text) <= hover_max_chars else text[: hover_max_chars - 1] + "…"
            hover.append(short)
            custom.append({"topic": key, "phrase": text})
        colour = _UQ_PALETTE[j % len(_UQ_PALETTE)]
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": key,
                "x": xy[idx, 0].tolist(),
                "y": xy[idx, 1].tolist(),
                "text": hover,
                "customdata": custom,
                "hovertemplate": "%{text}<extra></extra>",
                "marker": {
                    "size": 8 if j == focus else 5,
                    "color": colour,
                    "opacity": 1.0 if j == focus else 0.45,
                    "line": {"width": 1 if j == focus else 0, "color": "#0b0b0b"},
                },
            }
        )
    return {
        "data": traces,
        "layout": {
            "title": {
                "text": title or f"Focus {keys[focus]} — PCA",
                "x": 0.0,
                "xanchor": "left",
                "font": {"size": 14, "color": "#0b0b0b"},
            },
            "xaxis": {"title": "PC1", "zeroline": False, "showgrid": True, "gridcolor": "#e4e3df"},
            "yaxis": {"title": "PC2", "zeroline": False, "showgrid": True, "gridcolor": "#e4e3df", "scaleanchor": "x"},
            "plot_bgcolor": "white",
            "paper_bgcolor": "white",
            "margin": {"l": 50, "r": 20, "t": 50, "b": 50},
            "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        },
    }


def cluster_dendrogram_plotly_spec(
    children: np.ndarray,
    distances: np.ndarray,
    *,
    phrases: Sequence[Any] | None = None,
    labels: np.ndarray | None = None,
    n: int | None = None,
    title: str | None = None,
) -> dict[str, Any] | None:
    """U-shaped dendrogram from sklearn ``children_`` / ``distances_``."""
    ch = np.asarray(children, dtype=int)
    dist = np.asarray(distances, dtype=float).ravel()
    if ch.ndim != 2 or ch.shape[1] != 2 or ch.shape[0] == 0:
        return None
    n_leaves = int(n if n is not None else ch.shape[0] + 1)
    if dist.shape[0] != ch.shape[0]:
        return None
    xpos = [float(i) for i in range(n_leaves)]
    ypos = [0.0] * n_leaves
    xs: list[float | None] = []
    ys: list[float | None] = []
    for i, (a, b) in enumerate(ch):
        a = int(a)
        b = int(b)
        if a >= len(xpos) or b >= len(xpos):
            return None
        xa, xb = xpos[a], xpos[b]
        ya, yb = ypos[a], ypos[b]
        y = float(dist[i])
        x = 0.5 * (xa + xb)
        xs.extend([xa, xa, xb, xb, None])
        ys.extend([ya, y, y, yb, None])
        xpos.append(x)
        ypos.append(y)
    return {
        "data": [
            {
                "type": "scatter",
                "mode": "lines",
                "x": xs,
                "y": ys,
                "line": {"color": "#0b0b0b", "width": 1},
                "hoverinfo": "skip",
                "showlegend": False,
            }
        ],
        "layout": {
            "title": {
                "text": title or "Agglomerative dendrogram",
                "x": 0.0,
                "xanchor": "left",
                "font": {"size": 14, "color": "#0b0b0b"},
            },
            "xaxis": {"title": "phrase order", "showticklabels": False, "zeroline": False},
            "yaxis": {"title": "join distance", "zeroline": False},
            "plot_bgcolor": "white",
            "paper_bgcolor": "white",
            "margin": {"l": 50, "r": 20, "t": 50, "b": 40},
        },
    }


def stiefel_step_scale(speed: float, plane_var: float, linger: bool) -> float:
    """Diffusion coefficient for one Stiefel step.

    When ``linger`` is on, high-variance planes take smaller steps so the
    walk spends more time on views that capture codebook variance.
    """
    s = float(speed)
    if linger:
        s = s / float(np.sqrt(max(float(plane_var), 1e-12)))
    return s


def _plane_captured_variance(Xq: np.ndarray, U: np.ndarray) -> float:
    z = Xq @ U
    return float(z.var(axis=0, ddof=0).sum())


def _qr_stiefel(U: np.ndarray) -> np.ndarray:
    q, _ = np.linalg.qr(U)
    for j in range(q.shape[1]):
        if q[0, j] < 0:
            q[:, j] *= -1.0
    return q


def _cluster_cov2(xy: np.ndarray, floor: float) -> np.ndarray:
    if xy.shape[0] < 2:
        return (floor ** 2) * np.eye(2)
    cov = np.cov(xy, rowvar=False, ddof=0)
    if cov.shape != (2, 2) or not np.isfinite(cov).all():
        return (floor ** 2) * np.eye(2)
    vals = np.linalg.eigvalsh(cov)
    if float(np.min(vals)) < 0.25 * floor ** 2:
        cov = cov + (floor ** 2) * np.eye(2)
    return cov


def vq_projection_walk_plotly_spec(
    embeddings: np.ndarray,
    labels: np.ndarray,
    centres: np.ndarray,
    *,
    phrases: Sequence[Any] | None = None,
    masses: np.ndarray | None = None,
    n_frames: int = 48,
    speed: float = 0.08,
    subspace: int = 8,
    linger: bool = True,
    max_points: int = 300,
    ellipse_n: int = 24,
    seed: int = 0,
    title: str | None = None,
    hover_max_chars: int = 72,
) -> dict[str, Any] | None:
    """Brownian 2-frame walk through the leading-variance PCA subspace.

    Each frame projects phrases (subsampled), codebook centres, and 1-SD
    member ellipses. Play / Pause live on ``layout.updatemenus``.
    """
    X = np.asarray(embeddings, float)
    y = np.asarray(labels, int).ravel()
    C = np.asarray(centres, float)
    if X.ndim != 2 or X.shape[0] < 3 or X.shape[1] < 2:
        return None
    n, d = X.shape
    if y.shape[0] != n:
        return None
    m = int(C.shape[0]) if C.ndim == 2 else 0
    if m < 1 or C.shape[1] != d:
        return None
    k = int(max(int(y.max()) + 1 if y.size else 0, m))
    q = int(max(2, min(int(subspace), n - 1, d)))
    n_frames = int(max(2, n_frames))
    rng = np.random.default_rng(int(seed))

    Xc = X - X.mean(axis=0, keepdims=True)
    try:
        from sklearn.decomposition import PCA

        pca = PCA(n_components=q, svd_solver="randomized", random_state=int(seed))
        Xq = np.asarray(pca.fit_transform(X), float)
        Cq = np.asarray(pca.transform(C), float)
    except Exception:
        gram = Xc @ Xc.T
        vals, vecs = np.linalg.eigh(gram)
        order = np.argsort(vals)[::-1][:q]
        Xq = vecs[:, order] * np.sqrt(np.clip(vals[order], 0.0, None))
        denom = np.sqrt(np.clip(vals[order], 1e-12, None))
        Vt = (Xc.T @ vecs[:, order]) / denom
        Cq = (C - X.mean(axis=0)) @ Vt

    if Xq.shape[1] < 2:
        return None

    if n > int(max_points):
        keep = np.sort(rng.choice(n, size=int(max_points), replace=False))
    else:
        keep = np.arange(n, dtype=int)
    Xq_keep = Xq[keep]
    y_keep = y[keep]

    phrase_vals = [str(p) for p in phrases] if phrases is not None else []
    if len(phrase_vals) != n:
        phrase_vals = [f"phrase {i}" for i in range(n)]
    hover = []
    for i in keep:
        text = " ".join(phrase_vals[i].split()) or "—"
        if len(text) > hover_max_chars:
            text = text[: hover_max_chars - 1] + "…"
        hover.append(text)
    colours = [_UQ_PALETTE[int(lab) % len(_UQ_PALETTE)] for lab in y_keep]
    mass = (
        np.asarray(masses, float).ravel()
        if masses is not None
        else np.bincount(np.clip(y, 0, k - 1), minlength=k).astype(float)
    )
    if mass.shape[0] < m:
        mass = np.pad(mass, (0, m - mass.shape[0]))
    mass = mass[:m]
    size = 10.0 + 8.0 * np.sqrt(np.clip(mass, 1.0, None) / max(float(mass.max()), 1.0))

    U = np.zeros((q, 2), dtype=float)
    U[0, 0] = 1.0
    U[1, 1] = 1.0
    frames: list[dict[str, Any]] = []
    first_phrases: tuple[list[float], list[float]] | None = None
    first_centres: tuple[list[float], list[float]] | None = None
    first_ellipses: tuple[list[float | None], list[float | None]] | None = None

    for t in range(n_frames):
        v = _plane_captured_variance(Xq, U)
        sigma = stiefel_step_scale(speed, v, bool(linger))
        if t > 0:
            z = rng.normal(size=(q, 2)) * sigma
            z = z - U @ (U.T @ z)
            U = _qr_stiefel(U + z)
        xy = Xq_keep @ U
        cy = Cq @ U
        px, py = xy[:, 0].tolist(), xy[:, 1].tolist()
        cx, cy_l = cy[:, 0].tolist(), cy[:, 1].tolist()
        rms = float(np.sqrt(np.mean(xy ** 2))) if xy.size else 1.0
        floor = max(0.04 * rms, 1e-4)
        ex: list[float | None] = []
        ey: list[float | None] = []
        for j in range(m):
            members = Xq[y == j] @ U if np.any(y == j) else cy[j : j + 1]
            poly = _ellipse_polyline(
                cy[j],
                _cluster_cov2(np.asarray(members, float), floor),
                n=int(ellipse_n),
            )
            if poly is None:
                continue
            ex.extend(poly[0] + [None])
            ey.extend(poly[1] + [None])
        if first_phrases is None:
            first_phrases = (px, py)
            first_centres = (cx, cy_l)
            first_ellipses = (ex, ey)
        frames.append(
            {
                "name": str(t),
                "data": [
                    {"x": px, "y": py},
                    {"x": cx, "y": cy_l},
                    {"x": ex, "y": ey},
                ],
            }
        )

    assert first_phrases is not None and first_centres is not None
    assert first_ellipses is not None
    dt = 90
    steps = [
        {
            "args": [
                [str(t)],
                {
                    "frame": {"duration": 0, "redraw": False},
                    "mode": "immediate",
                    "transition": {"duration": 0},
                },
            ],
            "label": str(t),
            "method": "animate",
        }
        for t in range(n_frames)
    ]
    play_args = [
        None,
        {
            "frame": {"duration": dt, "redraw": False},
            "fromcurrent": True,
            "transition": {"duration": 0},
        },
    ]
    pause_args = [
        [None],
        {
            "frame": {"duration": 0, "redraw": False},
            "mode": "immediate",
            "transition": {"duration": 0},
        },
    ]
    heading = title or (
        "VQ projection walk — centres and 1-SD extent "
        f"(q={q}, linger={'on' if linger else 'off'})"
    )
    return {
        "data": [
            {
                "type": "scatter",
                "mode": "markers",
                "name": "phrases",
                "x": first_phrases[0],
                "y": first_phrases[1],
                "marker": {"color": colours, "size": 6, "opacity": 0.55},
                "text": hover,
                "hovertemplate": "%{text}<extra></extra>",
                "showlegend": False,
            },
            {
                "type": "scatter",
                "mode": "markers",
                "name": "centres",
                "x": first_centres[0],
                "y": first_centres[1],
                "marker": {
                    "symbol": "diamond",
                    "size": size.tolist(),
                    "color": [
                        _UQ_PALETTE[j % len(_UQ_PALETTE)] for j in range(m)
                    ],
                    "line": {"width": 1, "color": "#0b0b0b"},
                },
                "text": [f"cluster {j} · n={int(mass[j])}" for j in range(m)],
                "hovertemplate": "%{text}<extra></extra>",
                "showlegend": False,
            },
            {
                "type": "scatter",
                "mode": "lines",
                "name": "extent",
                "x": first_ellipses[0],
                "y": first_ellipses[1],
                "line": {"color": "#5a6a7a", "width": 1},
                "hoverinfo": "skip",
                "showlegend": False,
            },
        ],
        "layout": {
            "title": {
                "text": heading,
                "x": 0.0,
                "xanchor": "left",
                "font": {"size": 14, "color": "#0b0b0b"},
            },
            "xaxis": {
                "title": "plane 1",
                "zeroline": False,
                "scaleanchor": "y",
                "scaleratio": 1,
            },
            "yaxis": {"title": "plane 2", "zeroline": False},
            "plot_bgcolor": "white",
            "paper_bgcolor": "white",
            "margin": {"l": 50, "r": 20, "t": 70, "b": 70},
            "updatemenus": [
                {
                    "type": "buttons",
                    "showactive": False,
                    "x": 0.0,
                    "y": 1.16,
                    "xanchor": "left",
                    "yanchor": "top",
                    "direction": "left",
                    "pad": {"r": 10, "t": 0},
                    "buttons": [
                        {
                            "label": "Play",
                            "method": "animate",
                            "args": play_args,
                        },
                        {
                            "label": "Pause",
                            "method": "animate",
                            "args": pause_args,
                        },
                    ],
                }
            ],
            "sliders": [
                {
                    "active": 0,
                    "y": 0.0,
                    "x": 0.12,
                    "len": 0.75,
                    "pad": {"t": 30, "b": 0},
                    "currentvalue": {
                        "prefix": "frame ",
                        "xanchor": "right",
                    },
                    "steps": steps,
                }
            ],
        },
        "frames": frames,
    }
