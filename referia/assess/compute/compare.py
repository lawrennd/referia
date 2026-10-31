"""Document-weighted format comparison (CIP-001E).

Part A tables: type mix, lens shares, Jensen–Shannon divergence on the
document-mean lens profiles. Paper Table 1 / Figure 1 analogue. EMD stays
in CIP-0016 ``05_distance``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

import numpy as np

from .distance import (
    _jsonable,
    cluster_ids_missing,
    document_soft_topic_distributions,
)
from .vq import expand_vq_responsibilities

__all__ = [
    "jsd",
    "run_format_share_compare",
    "run_question_type_stress",
    "run_wordlist_floor",
]


def jsd(p, q) -> float:
    """Jensen–Shannon divergence (base 2, 0–1) between two distributions."""
    p = np.asarray(p, float).ravel()
    q = np.asarray(q, float).ravel()
    p = p / p.sum()
    q = q / q.sum()
    m = (p + q) / 2

    def kl(a, b):
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


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


def _topic_names(labels: Mapping | None, n: int) -> list[str]:
    if not labels:
        return [f"T{i}" for i in range(n)]
    out = []
    for i in range(n):
        key = f"T{i}"
        out.append(str(labels.get(key, labels.get(i, labels.get(str(i), key)))))
    return out


def _phrase_r(responsibilities, cluster_ids):
    R = np.asarray(responsibilities, dtype=float)
    if R.ndim != 2:
        raise ValueError(f"responsibilities must be 2-D, got {R.shape}")
    if cluster_ids_missing(cluster_ids):
        return R
    if isinstance(cluster_ids, str):
        import json

        cluster_ids = json.loads(cluster_ids)
    expanded = expand_vq_responsibilities(cluster_ids, R)
    return expanded


def _first_group_per_doc(
    doc_ids: Sequence, groups: Sequence | None
) -> dict[str, str]:
    first: dict[str, str] = {}
    if groups is None:
        return first
    for doc, grp in zip(doc_ids, groups):
        first.setdefault(str(doc), str(grp) if grp is not None else "")
    return first


def _bootstrap_means(
    rows: np.ndarray, rng: np.random.Generator, reps: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return mean, 2.5%, 97.5% of document-resampled means (percent)."""
    n = len(rows)
    if n == 0:
        z = np.zeros(rows.shape[1] if rows.ndim == 2 else 0)
        return z, z, z
    mean = rows.mean(0) * 100
    idx = rng.integers(0, n, size=(reps, n))
    boot = rows[idx].mean(1) * 100
    lo = np.percentile(boot, 2.5, axis=0)
    hi = np.percentile(boot, 97.5, axis=0)
    return mean, lo, hi


def _md_table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    head = "| " + " | ".join(title for title, _ in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        cells = []
        for _, key in columns:
            val = row.get(key, "")
            if isinstance(val, float):
                cells.append(f"{val:.1f}")
            else:
                cells.append(str(val))
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *body])


def _doc_kind_matrix(
    by_doc: dict[str, list[str]], docs: Sequence[str], values: Sequence[str]
) -> np.ndarray:
    mat = []
    for doc in docs:
        counts = {v: 0.0 for v in values}
        for k in by_doc[doc]:
            if k in counts:
                counts[k] += 1
        total = sum(counts.values()) or 1.0
        mat.append([counts[v] / total for v in values])
    return np.asarray(mat, float)


def _type_rows(
    doc_ids: Sequence,
    groups: Sequence | None,
    kinds: Sequence | None,
    *,
    values: Sequence[str],
    rng: np.random.Generator,
    reps: int,
    min_gap: float,
) -> list[dict]:
    if not kinds:
        return []
    by_doc: dict[str, list[str]] = defaultdict(list)
    grp = _first_group_per_doc(doc_ids, groups)
    for doc, kind in zip(doc_ids, kinds):
        if kind is None or str(kind) == "":
            continue
        by_doc[str(doc)].append(str(kind))
    group_docs: dict[str, list[str]] = defaultdict(list)
    for doc in by_doc:
        g = grp.get(doc, "")
        if g:
            group_docs[g].append(doc)
    names = list(group_docs)
    if not names:
        return []
    stats: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
    for g, docs in group_docs.items():
        arr = _doc_kind_matrix(by_doc, docs, values)
        mean, lo, hi = _bootstrap_means(arr, rng, reps)
        idx = rng.integers(0, len(arr), size=(reps, len(arr)))
        boot = arr[idx].mean(1) * 100
        stats[g] = (mean, lo, hi, boot)
    rows = []
    for i, val in enumerate(values):
        row: dict[str, Any] = {"value": val}
        for g, docs in group_docs.items():
            mean, lo, hi, _boot = stats[g]
            row[f"{g}_pct"] = float(mean[i])
            row[f"{g}_lo"] = float(lo[i])
            row[f"{g}_hi"] = float(hi[i])
            row[f"docs_{g}"] = len(docs)
        if len(names) == 2:
            g0, g1 = names[0], names[1]
            d = stats[g1][3][:, i] - stats[g0][3][:, i]
            row["difference"] = row[f"{g1}_pct"] - row[f"{g0}_pct"]
            row["diff_lo"] = float(np.percentile(d, 2.5))
            row["diff_hi"] = float(np.percentile(d, 97.5))
            row["clear"] = bool(
                ((row["diff_lo"] > 0) or (row["diff_hi"] < 0))
                and abs(row["difference"]) >= min_gap
            )
        rows.append(row)
    return rows


def run_format_share_compare(
    doc_ids,
    responsibilities,
    *,
    groups=None,
    cluster_ids=None,
    kinds=None,
    topic_labels: Mapping | None = None,
    min_mass: float = 1.0,
    n_boot: int = 2000,
    seed: int = 42,
    min_gap: float = 3.0,
    type_values: Sequence[str] | None = None,
    **_kwargs,
) -> tuple:
    """Document-weighted type mix, lens mix, and JSD (CIP-001E).

    Return order matches ``06_compare`` ``field:``.
    """
    R = _phrase_r(responsibilities, cluster_ids)
    ids = [str(d) for d in list(doc_ids)]
    if len(ids) != R.shape[0]:
        raise ValueError(
            f"doc_ids length {len(ids)} != responsibilities rows {R.shape[0]}"
        )
    min_mass = float(min_mass) if min_mass not in (None, "") else 1.0
    n_boot = _as_int(n_boot, 2000)
    seed = _as_int(seed, 42)
    min_gap = float(min_gap) if min_gap not in (None, "") else 3.0
    rng = np.random.default_rng(seed)

    P, docs, _mass = document_soft_topic_distributions(
        ids, R, min_mass=min_mass
    )
    names = _topic_names(topic_labels, P.shape[1] if P.size else R.shape[1])
    grp_map = _first_group_per_doc(ids, groups)
    doc_groups = [grp_map.get(d, "") for d in docs]

    lens_mix: list[dict] = []
    jsd_value = None
    note = ""
    unique_g = [g for g in dict.fromkeys(doc_groups) if g]
    preferred = [g for g in ("chatbot", "workshop") if g in unique_g]
    if len(preferred) == len(unique_g):
        unique_g = preferred
    if len(docs) and unique_g:
        boots: dict[str, np.ndarray] = {}
        means: dict[str, np.ndarray] = {}
        los: dict[str, np.ndarray] = {}
        his: dict[str, np.ndarray] = {}
        ndocs: dict[str, int] = {}
        for g in unique_g:
            mask = np.array([dg == g for dg in doc_groups])
            rows = P[mask]
            mean, lo, hi = _bootstrap_means(rows, rng, n_boot)
            means[g] = mean
            los[g] = lo
            his[g] = hi
            ndocs[g] = int(mask.sum())
            idx = rng.integers(0, len(rows), size=(n_boot, len(rows)))
            boots[g] = rows[idx].mean(1) * 100
        if len(unique_g) == 2:
            g0, g1 = unique_g[0], unique_g[1]
            for i, name in enumerate(names):
                d = boots[g1][:, i] - boots[g0][:, i]
                diff = float(means[g1][i] - means[g0][i])
                dlo = float(np.percentile(d, 2.5))
                dhi = float(np.percentile(d, 97.5))
                lens_mix.append(
                    {
                        "lens": name,
                        f"{g0}_pct": float(means[g0][i]),
                        f"{g0}_lo": float(los[g0][i]),
                        f"{g0}_hi": float(his[g0][i]),
                        f"{g1}_pct": float(means[g1][i]),
                        f"{g1}_lo": float(los[g1][i]),
                        f"{g1}_hi": float(his[g1][i]),
                        f"docs_{g0}": ndocs[g0],
                        f"docs_{g1}": ndocs[g1],
                        "difference": diff,
                        "diff_lo": dlo,
                        "diff_hi": dhi,
                        "clear": bool(
                            ((dlo > 0) or (dhi < 0)) and abs(diff) >= min_gap
                        ),
                    }
                )
            p = means[unique_g[0]] / 100.0
            q = means[unique_g[1]] / 100.0
            jsd_value = float(jsd(p, q))
        else:
            g = unique_g[0]
            for i, name in enumerate(names):
                lens_mix.append(
                    {
                        "lens": name,
                        f"{g}_pct": float(means[g][i]),
                        f"{g}_lo": float(los[g][i]),
                        f"{g}_hi": float(his[g][i]),
                        f"docs_{g}": ndocs[g],
                    }
                )
    elif not docs:
        note = "No documents passed min mass."
    else:
        note = "No group labels on packed `groups`."

    type_values = list(type_values or ["concern", "benefit", "condition"])
    type_mix = _type_rows(
        ids,
        groups,
        kinds,
        values=type_values,
        rng=rng,
        reps=n_boot,
        min_gap=min_gap,
    )
    if not type_mix:
        note = (note + "\n" if note else "") + (
            "No phrase kinds: pack `kinds` or load `phrases.yml` for CBC."
        )

    type_cols = [("Type", "value")]
    lens_cols = [("Lens", "lens")]
    for g in unique_g:
        type_cols.append((f"{g} %", f"{g}_pct"))
        lens_cols.append((f"{g} %", f"{g}_pct"))
    if len(unique_g) == 2:
        type_cols += [("w−c", "difference"), ("clear", "clear")]
        lens_cols += [("w−c", "difference"), ("clear", "clear")]

    type_md = _md_table(type_mix, type_cols) if type_mix else "_No type mix._"
    lens_md = _md_table(lens_mix, lens_cols) if lens_mix else "_No lens mix._"
    if jsd_value is None:
        jsd_md = note or "JSD needs two format groups."
    else:
        jsd_md = (
            f"**Jensen–Shannon divergence** (base 2, 0–1) between the "
            f"document-mean lens profiles of **{unique_g[0]}** and "
            f"**{unique_g[1]}** is **{jsd_value:.4f}**. "
            f"The published canonical figure is 0.006 on 11 k-means lenses; "
            f"this number is the same estimator on the current 04_grain "
            f"catalogue ({len(names)} lenses). A coarser catalogue shrinks JSD."
        )
        if note:
            jsd_md += f"\n\n{note}"

    return (
        _jsonable(type_mix),
        _jsonable(lens_mix),
        jsd_value,
        type_md,
        lens_md,
        jsd_md,
        _jsonable({g: doc_groups.count(g) for g in unique_g}),
    )


QUESTION_TYPES = {
    "asks about own / others' experience": (
        r"(?i)your own experience|experience of|have you (?:ever|had|used|"
        r"come across|dealt with|seen)|happened to you|affected you|"
        r"in your (?:work|job|life|family|area)|personally|someone you know|"
        r"anyone you know"
    ),
    "asks for an example": r"(?i)\bexample|for instance|a time when",
    "asks why / for reasons": r"(?i)\bwhy\b|what makes you|reason",
    "asks about conditions / safeguards": (
        r"(?i)red line|condition|safeguard|what would need|need to be in place|"
        r"in place|reassur"
    ),
    "asks how others might feel": (
        r"(?i)other people|others (?:in|might|would)|community|"
        r"residents (?:might|would|feel)"
    ),
    "asks about hopes / benefits": r"(?i)\bhope|benefit|opportunit|positive",
    "asks about concerns / risks": r"(?i)concern|worr|risk|negative",
}

EXPERIENCE_BASES = {"personal_experience", "others_experience"}

EXPERIENCE_WORDS = (
    r"(?i)\b(?:when i\b|i was\b|i had\b|i've had|i have had|i used to|"
    r"i went|i rang|i phoned|i called|i got\b|i've been|i've seen|i've used|"
    r"i've noticed|i've got|i have to\b|happened to (?:me|us)|"
    r"my (?:mum|mother|dad|father|son|daughter|husband|wife|partner|friend|"
    r"neighbou?r|family|kids|children|gran|nan|grandad|grandmother|"
    r"disability|condition|carer|job|work|manager|colleague)|"
    r"in my (?:job|work|experience|area|street|road)|at work|where i work|"
    r"i work (?:in|for|as|at)|we had|we were|"
    r"our (?:street|road|area|estate|bins))"
)


def run_question_type_stress(
    contexts,
    formats=None,
    bases=None,
    unit_ids=None,
    *,
    patterns: Mapping[str, str] | None = None,
    **_kwargs,
) -> tuple:
    """Share of chatbot questions matching each pattern; experience after it.

    ``contexts`` / ``formats`` are per-unit. ``bases`` / ``unit_ids`` are
    per-phrase when present (from exploded grounds).
    """
    import re

    pats = dict(patterns or QUESTION_TYPES)
    ctx = list(contexts or [])
    fmts = list(formats) if formats is not None else ["chatbot"] * len(ctx)
    n_bot = 0
    asked = {name: 0 for name in pats}
    for text, fmt in zip(ctx, fmts):
        if str(fmt) != "chatbot":
            continue
        n_bot += 1
        blob = str(text or "")
        for name, pat in pats.items():
            if re.search(pat, blob):
                asked[name] += 1
    rows = []
    for name, count in asked.items():
        pct = (100.0 * count / n_bot) if n_bot else 0.0
        rows.append(
            {
                "bot_question": name,
                "n_questions": count,
                "pct_of_chatbot_units": round(pct, 1),
            }
        )

    md = _md_table(
        rows,
        [
            ("Bot question", "bot_question"),
            ("n", "n_questions"),
            ("% of chatbot units", "pct_of_chatbot_units"),
        ],
    )
    if n_bot:
        md = (
            f"{n_bot} chatbot units. Experience-question share is the paper's "
            f"0.3% stress-test denominator when the pattern is "
            f"`asks about own / others' experience`.\n\n"
            + md
        )
    else:
        md = "No chatbot units in `formats`.\n\n" + md
    return _jsonable(rows), md, n_bot


def run_wordlist_floor(
    quotes,
    bases=None,
    groups=None,
    doc_ids=None,
    *,
    pattern: str | None = None,
    **_kwargs,
) -> tuple:
    """Word-list experience floor on each point's own quote (no model)."""
    import re

    pat = re.compile(pattern or EXPERIENCE_WORDS)
    quotes = list(quotes or [])
    n = len(quotes)
    flags = [bool(pat.search(str(q or ""))) for q in quotes]
    n_hit = int(sum(flags))
    rows = [
        {
            "measure": "word list on own quote",
            "n_points": n,
            "n_hit": n_hit,
            "pct": round(100.0 * n_hit / n, 1) if n else 0.0,
        }
    ]
    if bases is not None:
        exp = [str(b) in EXPERIENCE_BASES for b in list(bases)]
        if len(exp) == n and n:
            rows.append(
                {
                    "measure": "LLM grounds (personal + others)",
                    "n_points": n,
                    "n_hit": int(sum(exp)),
                    "pct": round(100.0 * sum(exp) / n, 1),
                }
            )
    if groups is not None and doc_ids is not None and n:
        by = defaultdict(lambda: [0, 0])
        for hit, grp in zip(flags, groups):
            g = str(grp)
            by[g][1] += 1
            by[g][0] += int(hit)
        for g, (hit, tot) in sorted(by.items()):
            rows.append(
                {
                    "measure": f"word list · {g}",
                    "n_points": tot,
                    "n_hit": hit,
                    "pct": round(100.0 * hit / tot, 1) if tot else 0.0,
                }
            )
    md = _md_table(
        rows,
        [
            ("Measure", "measure"),
            ("n", "n_points"),
            ("hits", "n_hit"),
            ("% ", "pct"),
        ],
    )
    md = (
        "Word-list floor is a transparent lower bound: it misses much real "
        "experience. The **ratio** of workshop to chatbot hits is what the "
        "paper uses, not the absolute level. Own-words recode (format-blind "
        "LLM) waits on a later coding pass; it is not this table.\n\n"
        + md
    )
    return _jsonable(rows), md
