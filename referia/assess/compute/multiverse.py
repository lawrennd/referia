"""Analysis-choice product (CIP-001E). Methodology of the 1080-config
multiverse on **main-run 07 codes** — not 1080 LLM jobs.

Axes: experience definition × weighting × exclusion × quote threshold ×
round. Own-words coding variants wait on a recode stage and are omitted
until that store exists.
"""

from __future__ import annotations

import re
from itertools import product
from typing import Any, Mapping, Sequence

import numpy as np

from .compare import jsd
from .distance import _jsonable

__all__ = ["run_analysis_multiverse"]

DEFINITIONS = {
    "personal only": frozenset({"personal_experience"}),
    "personal + others'": frozenset(
        {"personal_experience", "others_experience"}
    ),
    "personal + others' + professional": frozenset(
        {
            "personal_experience",
            "others_experience",
            "professional_knowledge",
        }
    ),
}
WEIGHTINGS = ("each document equal", "each point equal")
EXCLUSIONS = (
    "none",
    "drop workshop openings (first 2 units)",
    "drop carousel sessions",
    "drop 'Speaker 1' lines",
)
THRESHOLDS = (0.8, 0.9, 0.95)
ROUNDS = ("pooled", "autumn_2025", "spring_2026")
CANONICAL = {
    "definition": "personal + others'",
    "weighting": "each document equal",
    "exclusion": "none",
    "threshold": 0.8,
    "round": "pooled",
}

_SPEAKER1 = re.compile(
    r"^\s*(?:Speaker\s*1|S1)(?!\d)\s*[:\-–.\t]", re.I
)
_OPENING = re.compile(r"::c000[12]$")


def _as_int(value: Any, default: int) -> int:
    if value is None or value == "":
        return int(default)
    try:
        f = float(value)
    except (TypeError, ValueError):
        return int(default)
    if not np.isfinite(f):
        return int(default)
    return int(f)


def _speaker1(extract_text: Any) -> bool:
    for line in str(extract_text or "").split("\n"):
        if _SPEAKER1.match(line):
            return True
    return bool(_SPEAKER1.search(str(extract_text or "")))


def _opening_unit(unit_id: Any) -> bool:
    return bool(_OPENING.search(str(unit_id or "")))


def _share(flags: np.ndarray, doc_ids: np.ndarray, weighting: str) -> float:
    if len(flags) == 0:
        return float("nan")
    if weighting == "each point equal":
        return float(100.0 * flags.mean())
    by: dict[str, list[float]] = {}
    for flag, doc in zip(flags, doc_ids):
        by.setdefault(str(doc), []).append(float(flag))
    if not by:
        return float("nan")
    return float(100.0 * np.mean([np.mean(v) for v in by.values()]))


def _md_table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    head = "| " + " | ".join(title for title, _ in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        cells = []
        for _, key in columns:
            val = row.get(key, "")
            if val is None or (isinstance(val, float) and not np.isfinite(val)):
                cells.append("—")
            elif isinstance(val, float):
                cells.append(f"{val:.3g}")
            else:
                cells.append(str(val))
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *body])


def run_analysis_multiverse(
    points: Sequence[Mapping[str, Any]] | None = None,
    *,
    n_jsd_shuffles: int = 100,
    seed: int = 0,
    missing_hint: str | None = None,
    **_kwargs,
) -> tuple:
    """Experience-gap product over analysis choices. Returns summary, markdown, n_configs."""
    if not points:
        hint = missing_hint or (
            "No coded points. Classify all + Save on 07_grounds first."
        )
        return [], hint, 0

    n_jsd_shuffles = max(0, _as_int(n_jsd_shuffles, 100))
    rng = np.random.default_rng(_as_int(seed, 0))

    recs = []
    for row in points:
        basis = str(row.get("basis") or "").strip()
        if not basis:
            continue
        recs.append(
            {
                "basis": basis,
                "format": str(row.get("format") or row.get("group") or ""),
                "doc_id": str(row.get("doc_id") or ""),
                "round": str(row.get("round") or ""),
                "session_type": str(row.get("session_type") or ""),
                "quote_support": float(row.get("quote_support") or 0.0),
                "unit_id": str(row.get("unit_id") or ""),
                "speaker1": _speaker1(row.get("extract_text")),
                "opening": _opening_unit(row.get("unit_id")),
                "lens": row.get("lens") or row.get("topic"),
            }
        )
    if not recs:
        return [], "Points loaded but none have a 07 basis.", 0

    def subset(exclusion: str, threshold: float, rnd: str) -> list[dict]:
        out = [r for r in recs if r["quote_support"] >= threshold]
        if rnd != "pooled":
            out = [r for r in out if r["round"] == rnd]
        if exclusion.startswith("drop workshop openings"):
            out = [r for r in out if not r["opening"]]
        elif exclusion == "drop carousel sessions":
            out = [r for r in out if r["session_type"] != "carousel"]
        elif exclusion.startswith("drop 'Speaker 1'"):
            out = [r for r in out if not r["speaker1"]]
        return out

    rows_b = []
    for definition, weighting, exclusion, threshold, rnd in product(
        DEFINITIONS, WEIGHTINGS, EXCLUSIONS, THRESHOLDS, ROUNDS
    ):
        d = subset(exclusion, threshold, rnd)
        formats = {r["format"] for r in d}
        if "chatbot" not in formats or "workshop" not in formats:
            continue
        exp_set = DEFINITIONS[definition]
        flags = np.array([r["basis"] in exp_set for r in d])
        docs = np.array([r["doc_id"] for r in d])
        fmt = np.array([r["format"] for r in d])
        c, w = fmt == "chatbot", fmt == "workshop"
        ec = _share(flags[c], docs[c], weighting)
        ew = _share(flags[w], docs[w], weighting)
        rows_b.append(
            {
                "definition": definition,
                "weighting": weighting,
                "exclusion": exclusion,
                "threshold": threshold,
                "round": rnd,
                "n_points": len(d),
                "chatbot_exp_pct": None if not np.isfinite(ec) else round(ec, 3),
                "workshop_exp_pct": None if not np.isfinite(ew) else round(ew, 3),
                "experience_gap": (
                    None
                    if not (np.isfinite(ec) and np.isfinite(ew))
                    else round(ew - ec, 3)
                ),
            }
        )

    if not rows_b:
        return [], "No configuration kept both formats.", 0

    gaps = np.array(
        [r["experience_gap"] for r in rows_b if r["experience_gap"] is not None],
        dtype=float,
    )
    can = [
        r
        for r in rows_b
        if all(r.get(k) == v for k, v in CANONICAL.items())
    ]
    canonical = can[0]["experience_gap"] if can else None
    n_pos = float((gaps > 0).mean()) if len(gaps) else float("nan")
    summary = [
        {
            "result": "B: experience gap (workshop − chatbot, points)",
            "configurations": len(gaps),
            "canonical": canonical,
            "median": None if not len(gaps) else round(float(np.median(gaps)), 3),
            "p5": None if not len(gaps) else round(float(np.quantile(gaps, 0.05)), 3),
            "p95": None if not len(gaps) else round(float(np.quantile(gaps, 0.95)), 3),
            "pct_positive": None if not np.isfinite(n_pos) else round(100.0 * n_pos, 1),
        }
    ]

    # Chance-level agenda JSD on canonical subset, if lens/topic present.
    dcan = subset("none", 0.8, "pooled")
    lenses = [r.get("lens") for r in dcan if r.get("lens") not in (None, "")]
    chance_line = ""
    if lenses and n_jsd_shuffles:
        lens_list = sorted({str(x) for x in lenses})

        def profile(subset_rows, weighting):
            if weighting == "each point equal":
                counts = {k: 0.0 for k in lens_list}
                n = 0
                for r in subset_rows:
                    lab = r.get("lens")
                    if lab in (None, ""):
                        continue
                    counts[str(lab)] += 1
                    n += 1
                if not n:
                    return None
                return np.array([counts[k] / n for k in lens_list])
            by: dict[str, dict[str, float]] = {}
            for r in subset_rows:
                lab = r.get("lens")
                if lab in (None, ""):
                    continue
                by.setdefault(r["doc_id"], {k: 0.0 for k in lens_list})
                by[r["doc_id"]][str(lab)] += 1
            if not by:
                return None
            mats = []
            for hist in by.values():
                tot = sum(hist.values()) or 1.0
                mats.append([hist[k] / tot for k in lens_list])
            return np.mean(mats, axis=0)

        bot = [r for r in dcan if r["format"] == "chatbot"]
        ws = [r for r in dcan if r["format"] == "workshop"]
        pb = profile(bot, "each document equal")
        pw = profile(ws, "each document equal")
        if pb is not None and pw is not None:
            obs = jsd(pb, pw)
            docs = {}
            for r in dcan:
                docs.setdefault(r["doc_id"], r["format"])
            doc_ids = list(docs)
            fmts = np.array([docs[d] for d in doc_ids])
            null = []
            for _ in range(n_jsd_shuffles):
                perm = rng.permutation(fmts)
                lab = dict(zip(doc_ids, perm))
                bot_p = profile(
                    [r for r in dcan if lab.get(r["doc_id"]) == "chatbot"],
                    "each document equal",
                )
                ws_p = profile(
                    [r for r in dcan if lab.get(r["doc_id"]) == "workshop"],
                    "each document equal",
                )
                if bot_p is None or ws_p is None:
                    continue
                null.append(jsd(bot_p, ws_p))
            if null:
                chance_line = (
                    f" Canonical agenda JSD {obs:.3f} vs shuffled mean "
                    f"{float(np.mean(null)):.3f} (95th {float(np.percentile(null, 95)):.3f})."
                )

    md = (
        f"Main-run 07 codes only — **{len(gaps)} configurations** "
        "(definition × weighting × exclusion × threshold × round). "
        "This is the methodology of the 1080-config table with one coding "
        "(main run), not 1080 populate-all LLM jobs. Own-words coding "
        "variants wait on a format-blind recode; k=25/60 is a refit of "
        "03_vq then 04_grain then 06_compare, not this page.\n\n"
        + _md_table(
            summary,
            [
                ("Result", "result"),
                ("n", "configurations"),
                ("canonical", "canonical"),
                ("median", "median"),
                ("5th", "p5"),
                ("95th", "p95"),
                ("% > 0", "pct_positive"),
            ],
        )
        + (f"\n\n{chance_line.strip()}" if chance_line else "")
    )
    return _jsonable(summary), md, int(len(gaps))
