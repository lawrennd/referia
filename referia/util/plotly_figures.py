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
