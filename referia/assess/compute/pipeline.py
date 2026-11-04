"""Pipeline manifest + multiverse axis selection helpers (CIP-0023).

Option A: an explicit study ``pipeline.yml`` lists nodes, edges, and
per-knob cost classes. The multiverse page uses this to draw a DAG and
to decide which ticks are executable in Phase 1 (``aggregate`` only).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

__all__ = [
    "COST_CLASSES",
    "PAPER_AXES",
    "WRITE_STORE_ROLES",
    "READ_STORE_ROLES",
    "discover_pipeline_edges",
    "expand_stage_selection",
    "load_pipeline_manifest",
    "pipeline_dag_figure",
    "pipeline_stage_params_md",
    "resolve_active_paper_axes",
    "selection_cost_gate",
]

# CIP-0024 Option B: interface keys that write / read products.
WRITE_STORE_ROLES = frozenset({"output", "pack"})
READ_STORE_ROLES = frozenset(
    {
        "input",
        "data",
        "constants",
        "grounds",
        "phrases",
        "turns",
        "chunks",
        "codebook",
        "roster",
        "grain",
        "scores",
        "documents",
    }
)

COST_CLASSES = frozenset({"aggregate", "refit", "llm", "display"})

# Phase 1 paper axes → levels consumed by run_analysis_multiverse.
PAPER_AXES = (
    "definitions",
    "weightings",
    "exclusions",
    "thresholds",
    "rounds",
)


def _as_mapping(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        return dict(raw)
    raise ValueError("pipeline manifest must be a mapping")


def load_pipeline_manifest(
    path: str | Path | None = None,
    *,
    data: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Load and validate a pipeline manifest.

    Returns a normalised dict with ``nodes`` (list) and ``edges`` (list).
    """
    if data is None:
        if path is None:
            raise ValueError("path or data is required")
        text = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    manifest = _as_mapping(data)
    nodes_raw = manifest.get("nodes") or []
    edges_raw = manifest.get("edges") or []
    if not isinstance(nodes_raw, list) or not nodes_raw:
        raise ValueError("pipeline.nodes must be a non-empty list")
    if not isinstance(edges_raw, list):
        raise ValueError("pipeline.edges must be a list")

    nodes: list[dict[str, Any]] = []
    ids: set[str] = set()
    for item in nodes_raw:
        if not isinstance(item, Mapping):
            raise ValueError("each node must be a mapping")
        nid = str(item.get("id") or "").strip()
        if not nid:
            raise ValueError("node.id is required")
        if nid in ids:
            raise ValueError(f"duplicate node id {nid!r}")
        ids.add(nid)
        knobs = []
        for knob in item.get("parameters") or []:
            if isinstance(knob, str):
                knobs.append(
                    {
                        "key": knob,
                        "cost_class": "display",
                        "multiverse_eligible": False,
                    }
                )
                continue
            if not isinstance(knob, Mapping):
                raise ValueError(f"node {nid}: parameter entries must be maps")
            key = str(knob.get("key") or "").strip()
            if not key:
                raise ValueError(f"node {nid}: parameter key required")
            cost = str(knob.get("cost_class") or "display").strip()
            if cost not in COST_CLASSES:
                raise ValueError(
                    f"node {nid} key {key}: unknown cost_class {cost!r}"
                )
            knobs.append(
                {
                    "key": key,
                    "cost_class": cost,
                    "multiverse_eligible": bool(
                        knob.get("multiverse_eligible", False)
                    ),
                    "paper_axis": knob.get("paper_axis"),
                    "label": knob.get("label") or key,
                }
            )
        nodes.append(
            {
                "id": nid,
                "permalink": str(item.get("permalink") or f"/{nid}/"),
                "title": str(item.get("title") or nid),
                "parameters_path": item.get("parameters_path"),
                "parameters": knobs,
            }
        )

    edges: list[dict[str, str]] = []
    for item in edges_raw:
        if not isinstance(item, Mapping):
            raise ValueError("each edge must be a mapping")
        frm = str(item.get("from") or "").strip()
        to = str(item.get("to") or "").strip()
        if frm not in ids or to not in ids:
            raise ValueError(f"edge {frm!r} → {to!r} references unknown node")
        edges.append(
            {
                "from": frm,
                "to": to,
                "via": str(item.get("via") or ""),
            }
        )

    _assert_acyclic(ids, edges)
    return {"nodes": nodes, "edges": edges}


def _assert_acyclic(ids: set[str], edges: Sequence[Mapping[str, str]]) -> None:
    adj: dict[str, list[str]] = {i: [] for i in ids}
    for e in edges:
        adj[e["from"]].append(e["to"])
    state: dict[str, int] = {i: 0 for i in ids}  # 0=unseen 1=stack 2=done

    def visit(n: str) -> None:
        if state[n] == 1:
            raise ValueError(f"pipeline has a cycle at {n!r}")
        if state[n] == 2:
            return
        state[n] = 1
        for nxt in adj[n]:
            visit(nxt)
        state[n] = 2

    for n in ids:
        visit(n)


def expand_stage_selection(
    manifest: Mapping[str, Any],
    stage_ids: Sequence[str],
    *,
    executable_only: bool = True,
) -> list[dict[str, Any]]:
    """Expand whole-stage ticks to eligible knobs (Phase 1: aggregate)."""
    by_id = {n["id"]: n for n in manifest.get("nodes") or []}
    out: list[dict[str, Any]] = []
    for sid in stage_ids:
        node = by_id.get(str(sid))
        if not node:
            continue
        for knob in node.get("parameters") or []:
            if not knob.get("multiverse_eligible"):
                continue
            if executable_only and knob.get("cost_class") != "aggregate":
                continue
            out.append({"stage": node["id"], **knob})
    return out


def selection_cost_gate(
    selected: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Split selection into executable aggregate vs refused refit/llm.

    ``selected`` entries need ``cost_class`` (and optionally ``key`` /
    ``stage`` / ``paper_axis``).
    """
    ok: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    for item in selected:
        if not isinstance(item, Mapping):
            continue
        cost = str(item.get("cost_class") or "")
        if cost == "aggregate" and item.get("multiverse_eligible", True):
            ok.append(dict(item))
        elif cost in {"refit", "llm"}:
            refused.append(dict(item))
        # display ignored
    return {
        "executable": ok,
        "refused": refused,
        # Executable aggregate ticks may run even if refused ticks are also
        # present; the message warns. Empty executable with refused → not ok.
        "ok": bool(ok),
        "message": (
            ""
            if not refused
            else (
                "Phase 1 refuses refit/llm ticks: "
                + ", ".join(
                    str(r.get("key") or r.get("stage") or r)
                    for r in refused
                )
            )
        ),
    }


def resolve_active_paper_axes(
    *,
    axis_definitions: Any = True,
    axis_weightings: Any = True,
    axis_exclusions: Any = True,
    axis_thresholds: Any = True,
    axis_rounds: Any = True,
    active_axes: Mapping[str, Any] | None = None,
) -> dict[str, bool]:
    """Normalise checkbox / mapping inputs to the five paper axis flags."""

    def _flag(value: Any, default: bool = True) -> bool:
        if value is None or value == "":
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    axes = {
        "definitions": _flag(axis_definitions),
        "weightings": _flag(axis_weightings),
        "exclusions": _flag(axis_exclusions),
        "thresholds": _flag(axis_thresholds),
        "rounds": _flag(axis_rounds),
    }
    if active_axes:
        for key in PAPER_AXES:
            if key in active_axes:
                axes[key] = _flag(active_axes.get(key), axes[key])
    if not any(axes.values()):
        # Avoid empty product; keep canonical single cell via all-off
        # meaning "canonical only" is handled in multiverse runner.
        pass
    return axes


def pipeline_dag_figure(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Build a Plotly-like figure dict for the pipeline DAG."""
    nodes = list(manifest.get("nodes") or [])
    edges = list(manifest.get("edges") or [])
    if not nodes:
        return {"data": [], "layout": {"title": "Empty pipeline"}}

    # Layer by longest path from sources (simple left-to-right layout).
    ids = [n["id"] for n in nodes]
    indeg = {i: 0 for i in ids}
    adj = {i: [] for i in ids}
    for e in edges:
        adj[e["from"]].append(e["to"])
        indeg[e["to"]] = indeg.get(e["to"], 0) + 1
    layer = {i: 0 for i in ids}
    changed = True
    while changed:
        changed = False
        for frm, tos in adj.items():
            for to in tos:
                cand = layer[frm] + 1
                if cand > layer[to]:
                    layer[to] = cand
                    changed = True
    by_layer: dict[int, list[str]] = {}
    for i, L in layer.items():
        by_layer.setdefault(L, []).append(i)
    pos: dict[str, tuple[float, float]] = {}
    for L, members in sorted(by_layer.items()):
        members = sorted(members)
        for j, nid in enumerate(members):
            y = 1.0 - (j + 0.5) / max(len(members), 1)
            pos[nid] = (float(L), y)

    edge_x: list[Any] = []
    edge_y: list[Any] = []
    for e in edges:
        x0, y0 = pos[e["from"]]
        x1, y1 = pos[e["to"]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    node_x = [pos[n["id"]][0] for n in nodes]
    node_y = [pos[n["id"]][1] for n in nodes]
    texts = []
    for n in nodes:
        n_agg = sum(
            1
            for k in n.get("parameters") or []
            if k.get("multiverse_eligible") and k.get("cost_class") == "aggregate"
        )
        texts.append(
            f"{n['title']}<br>aggregate axes: {n_agg}<br>{n.get('permalink')}"
        )

    return {
        "data": [
            {
                "type": "scatter",
                "x": edge_x,
                "y": edge_y,
                "mode": "lines",
                "line": {"width": 1, "color": "#888"},
                "hoverinfo": "none",
                "showlegend": False,
            },
            {
                "type": "scatter",
                "x": node_x,
                "y": node_y,
                "mode": "markers+text",
                "text": [n["id"] for n in nodes],
                "textposition": "top center",
                "marker": {
                    "size": 18,
                    "color": "#2e6da4",
                    "line": {"width": 1, "color": "#1b4f72"},
                },
                "hovertext": texts,
                "hoverinfo": "text",
                "customdata": [n["id"] for n in nodes],
                "showlegend": False,
            },
        ],
        "layout": {
            "title": "Analysis pipeline (CIP-0023)",
            "xaxis": {"visible": False},
            "yaxis": {"visible": False},
            "margin": {"l": 40, "r": 40, "t": 50, "b": 20},
            "height": 420,
            "plot_bgcolor": "rgba(0,0,0,0)",
            "paper_bgcolor": "rgba(0,0,0,0)",
        },
    }


def pipeline_stage_params_md(
    manifest: Mapping[str, Any],
    stage_id: str | None,
    *,
    values: Mapping[str, Any] | None = None,
) -> str:
    """Markdown table of knobs for *stage_id* (cost class + eligibility)."""
    if not stage_id:
        return "_Select a stage to list its multiverse-relevant parameters._"
    node = next(
        (n for n in manifest.get("nodes") or [] if n["id"] == stage_id),
        None,
    )
    if not node:
        return f"_Unknown stage `{stage_id}`._"
    knobs = node.get("parameters") or []
    if not knobs:
        return f"_No declared parameters on `{stage_id}`._"
    values = values or {}
    lines = [
        f"**{node.get('title') or stage_id}** (`{node.get('permalink')}`)",
        "",
        "| Parameter | Cost | Multiverse | Value |",
        "| --- | --- | --- | --- |",
    ]
    for k in knobs:
        key = k["key"]
        val = values.get(key, "—")
        if isinstance(val, (list, dict)):
            val = yaml.safe_dump(val, default_flow_style=True).strip()
        elig = "yes" if k.get("multiverse_eligible") else "no"
        lines.append(
            f"| `{key}` | {k.get('cost_class')} | {elig} | {val} |"
        )
    return "\n".join(lines)


def _store_path_key(block: Any) -> str | None:
    if not isinstance(block, Mapping):
        return None
    filename = block.get("filename")
    if not filename:
        return None
    directory = block.get("directory")
    if directory:
        return f"{str(directory).rstrip('/')}/{filename}"
    return str(filename)


def _iter_role_stores(
    meta: Mapping[str, Any], roles: frozenset[str]
) -> list[tuple[str, str]]:
    """Return ``(role, path_key)`` for store-shaped blocks under *roles*."""
    out: list[tuple[str, str]] = []
    for role in roles:
        if role not in meta:
            continue
        raw = meta.get(role)
        blocks = raw if isinstance(raw, list) else [raw]
        for block in blocks:
            key = _store_path_key(block)
            if key:
                out.append((role, key))
    return out


def discover_pipeline_edges(
    root: str | Path | None = None,
    *,
    stages: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Infer producer→consumer edges from declared interface stores (CIP-0024).

    *stages* is a sequence of mappings with ``id`` and ``meta`` (frontmatter
    dict). When *stages* is omitted, load referia markdown under *root*
    (``layout: referia``) via ``python-frontmatter`` when available.

    Returns ``{"stages": [...], "edges": [...], "orphans": [...]}`` where
    edges are ``{"from", "to", "via", "write_role", "read_role"}`` and
    orphans are reads with no declared writer (external seeds).
    """
    from collections import defaultdict

    if stages is None:
        if root is None:
            raise ValueError("root or stages is required")
        stages = _load_referia_stage_metas(Path(root))

    producers: dict[str, list[tuple[str, str]]] = defaultdict(list)
    consumers: dict[str, list[tuple[str, str]]] = defaultdict(list)
    stage_ids: list[str] = []
    for stage in stages:
        sid = str(stage.get("id") or "")
        meta = stage.get("meta") or {}
        if not sid or not isinstance(meta, Mapping):
            continue
        stage_ids.append(sid)
        for role, key in _iter_role_stores(meta, WRITE_STORE_ROLES):
            producers[key].append((sid, role))
        for role, key in _iter_role_stores(meta, READ_STORE_ROLES):
            consumers[key].append((sid, role))

    edges: list[dict[str, str]] = []
    orphans: list[dict[str, str]] = []
    for store, cons in sorted(consumers.items()):
        prods = producers.get(store, [])
        for cid, read_role in cons:
            if not prods:
                orphans.append(
                    {"to": cid, "via": store, "read_role": read_role}
                )
                continue
            for pid, write_role in prods:
                if pid == cid:
                    continue
                edges.append(
                    {
                        "from": pid,
                        "to": cid,
                        "via": store,
                        "write_role": write_role,
                        "read_role": read_role,
                    }
                )
    return {
        "stages": stage_ids,
        "edges": edges,
        "orphans": orphans,
        "producers": {k: [p for p, _ in v] for k, v in producers.items()},
    }


def _load_referia_stage_metas(root: Path) -> list[dict[str, Any]]:
    try:
        import frontmatter
    except ImportError as exc:
        raise ImportError(
            "discover_pipeline_edges from a study root requires "
            "python-frontmatter"
        ) from exc

    out: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.md")):
        try:
            post = frontmatter.load(path)
        except Exception:
            continue
        meta = dict(post)
        if meta.get("layout") != "referia":
            continue
        if path.stem in {"index", "README"}:
            continue
        out.append({"id": path.stem, "meta": meta, "path": str(path)})
    return out
