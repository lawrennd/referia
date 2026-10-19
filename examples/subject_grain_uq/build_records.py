#!/usr/bin/env python3
"""Bake Bishop–Tipping local-U_q views for the subject_grain_uq demo.

Default corpus: **CIMT German cycling** (Bonn dialogue + survey), matching
multilogue notebook 03 Access. Embeddings use OpenAI when ``OPENAI_API_KEY``
is present (repo-root ``.env``); otherwise pass ``--synthetic`` for the
planted English bank.

    poetry install --with llm
    poetry run python examples/subject_grain_uq/build_records.py
    poetry run python examples/subject_grain_uq/build_records.py --synthetic
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import urllib.request
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]  # referia package root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from referia.assess.compute.mppca import (  # noqa: E402
    mppca_fit,
    rebuild_uq_by_topic,
    topic_keys,
)


def _label_prompt_from_referia_yml() -> str:
    """Read the default naming prompt from ``_referia.yml`` (single source)."""
    cfg = yaml.safe_load((HERE / "_referia.yml").read_text(encoding="utf-8"))
    for block in cfg.get("review") or []:
        entries = block.get("entries") if isinstance(block, dict) else None
        for entry in entries or ([block] if isinstance(block, dict) else []):
            if not isinstance(entry, dict):
                continue
            if entry.get("field") != "label_prompt":
                continue
            default = (entry.get("args") or {}).get("default")
            if default and "<<PHRASES>>" in str(default):
                return str(default).strip() + "\n"
    raise RuntimeError(
        "label_prompt default with <<PHRASES>> not found in _referia.yml"
    )

INFO = HERE / "info"
CACHE = INFO / ".cache" / "cimt"

# Same registry as multilogue.access.resources (CIMT argument-mining corpus).
CIMT_BASE = (
    "https://raw.githubusercontent.com/juliaromberg/"
    "cimt-argument-mining-dataset/master/"
)
CIMT_PROCESSES = {
    "Cycling-Dialogue-Bonn": "Cycling-Dialogue-Bonn/dataset_CDB.tsv",
    "Survey-Bonn": "Survey-Bonn/dataset_CQB.tsv",
}

# Short paragraphs — offline / CI fallback only.
PHRASE_BANK = [
    "Foundation models can summarise long consultation responses without losing the main thread.",
    "Automated clustering helps stewards see repeated benefits across submissions quickly.",
    "Shared embeddings let similar capability claims sit near each other in topic space.",
    "Soft responsibilities keep borderline benefit phrases visible in more than one topic.",
    "A local U_q plane shows how benefit phrases stretch along the component factors.",
    "Reviewers can click a dense point and read the full capability claim in context.",
    "Mixture PPCA separates elongated benefit clouds better than a single global PCA view.",
    "Exemplars for labelling should come from high-mass phrases, not from hard-only cuts.",
    "Respondents worry that opaque scoring will silence minority concerns in the record.",
    "Privacy risk rises when verbatim quotes are echoed without redaction checks.",
    "False confidence in automated summaries can hide sharp disagreements on harms.",
    "Concern phrases often mix with benefit language in the same paragraph.",
    "Soft mass on a concern topic should stay faint on the benefit local plane.",
    "Clicking a ghost point still surfaces the full concern text for Assess reading.",
    "Hard labels alone erase soft membership that Assess needs for grain decisions.",
    "Noise floors that are too large collapse concern geometry into a single blob.",
    "Governed review loops need an explicit split between Assess and Address stages.",
    "Catalogue growth should start from one soft topic and split only when grain appears.",
    "Stewards document why a topic was merged before any LLM lens is applied.",
    "Process phrases cluster around who decides, who audits, and who can override.",
    "Local planes for governance topics often keep sibling means nearly on-centre.",
    "Interactive Assess is question-agnostic: no lens prompt yet, only soft geometry.",
    "Saving selected phrase and topic into scores.yml mirrors a human Assess notebook.",
    "CIP-0011 chrome binds click and responsibility ink without owning the fit.",
]


def _load_dotenv() -> None:
    """Load referia / home ``.env`` so OPENAI_API_KEY is visible."""
    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:
        return
    path = find_dotenv(str(ROOT / ".env"), raise_error_if_not_found=False)
    if not path:
        path = find_dotenv(raise_error_if_not_found=False)
    if path:
        load_dotenv(path, override=False)
    home = Path.home() / ".env"
    if home.is_file():
        load_dotenv(home, override=False)


def _planted_embeddings(
    phrases: list[str],
    *,
    d: int = 24,
    seed: int = 7,
) -> tuple[np.ndarray, list[str]]:
    """Map phrase bank rows onto three elongated subspaces (synthetic)."""
    rng = np.random.default_rng(seed)
    n = len(phrases)
    topic_of = np.array([i // 8 for i in range(n)], dtype=int)
    means = np.zeros((3, d))
    means[0, 0] = 2.8
    means[1, 2] = 2.8
    means[2, 4] = 2.8
    X = np.zeros((n, d))
    for i, t in enumerate(topic_of):
        axis_a, axis_b = 2 * t, 2 * t + 1
        cov = np.eye(d) * 0.04
        cov[axis_a, axis_a] = 0.7
        cov[axis_b, axis_b] = 0.45
        X[i] = rng.multivariate_normal(means[t], cov)
    perm = rng.permutation(n)
    return X[perm], [phrases[i] for i in perm]


def _ensure_cimt_tsv(rel: str, *, force: bool = False) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and not force:
        return dest
    url = CIMT_BASE + rel
    print(f"Downloading CIMT {rel} …")
    urllib.request.urlretrieve(url, dest)
    return dest


def _phrases_from_cimt_tsv(
    path: Path, *, format_tag: str, max_units: int | None
) -> list[str]:
    """One phrase per sentence (multilogue ``phrases_from_units`` pedagogy)."""
    out: list[str] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            content = (row.get("content") or "").strip()
            if not content:
                continue
            # Cap length for the viewer text field.
            if len(content) > 500:
                content = content[:499].rstrip() + "…"
            out.append(content)
            if max_units is not None and len(out) >= max_units:
                break
    if not out:
        raise RuntimeError(f"No CIMT sentences in {path} ({format_tag})")
    return out


def load_cimt_phrases(*, max_units_per: int = 40, force: bool = False) -> tuple[list[str], dict]:
    """Load Bonn cycling dialogue + survey sentences (German)."""
    # Prefer multilogue Access when importable (editable install or sibling tree).
    for candidate in (
        Path(os.environ.get("MULTILOGUE_ROOT", "")),
        ROOT.parent.parent / "mlatcl" / "multilogue",
        ROOT.parent / "multilogue",
    ):
        if candidate.is_dir() and (candidate / "multilogue").is_dir():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            break
    try:
        from multilogue.experiment import load_cimt_format_pair
        from multilogue.extract import phrases_from_units

        units, meta = load_cimt_format_pair(max_units_per=max_units_per)
        if units is None:
            raise RuntimeError(meta.get("error", "CIMT load failed"))
        table = phrases_from_units(units, extra_fields=["group", "format"])
        phrases = [str(p) for p in table["phrase"].tolist()]
        meta = dict(meta)
        meta["loader"] = "multilogue"
        return phrases, meta
    except Exception as exc:  # noqa: BLE001 — fall through to direct download
        print(f"multilogue Access unavailable ({exc}); downloading CIMT TSVs …")

    dial = _ensure_cimt_tsv(
        CIMT_PROCESSES["Cycling-Dialogue-Bonn"], force=force
    )
    surv = _ensure_cimt_tsv(CIMT_PROCESSES["Survey-Bonn"], force=force)
    phrases = _phrases_from_cimt_tsv(
        dial, format_tag="dialogue", max_units=max_units_per
    ) + _phrases_from_cimt_tsv(
        surv, format_tag="survey", max_units=max_units_per
    )
    meta = {
        "loader": "direct",
        "source": "cimt",
        "dialogue_process": "Cycling-Dialogue-Bonn",
        "survey_process": "Survey-Bonn",
        "n_phrases": len(phrases),
        "max_units_per": max_units_per,
    }
    return phrases, meta


def _l2_normalize(X: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return X / norms


def _pca_reduce(X: np.ndarray, d: int, *, seed: int = 0) -> np.ndarray:
    """Project to ``d`` dims for compact YAML (geometry still soft-MPPCA)."""
    X = np.asarray(X, float)
    if X.shape[1] <= d:
        return X
    # Centered SVD — avoid sklearn PCA dependency quirks on sparse ranks.
    xc = X - X.mean(axis=0, keepdims=True)
    _, _, vt = np.linalg.svd(xc, full_matrices=False)
    return xc @ vt[:d].T


def embed_phrases(
    phrases: list[str],
    *,
    model: str = "text-embedding-3-small",
    target_dim: int = 32,
    batch_size: int = 64,
) -> np.ndarray:
    """OpenAI embeddings → L2 → PCA to ``target_dim`` for the demo store."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY missing. Set it in referia's .env, or pass --synthetic."
        )
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "openai package not installed. Run: poetry install --with llm"
        ) from exc

    client = OpenAI(api_key=key)
    vectors: list[list[float]] = []
    for i in range(0, len(phrases), batch_size):
        batch = phrases[i : i + batch_size]
        print(f"Embedding {i + 1}–{i + len(batch)} / {len(phrases)} …")
        resp = client.embeddings.create(model=model, input=batch)
        # API returns data possibly out of order — sort by index.
        ordered = sorted(resp.data, key=lambda d: d.index)
        vectors.extend(d.embedding for d in ordered)
    X = _l2_normalize(np.asarray(vectors, dtype=float))
    return _pca_reduce(X, target_dim)


def _write_yaml(phrases: list[str], X: np.ndarray, *, title: str, source: str) -> None:
    INFO.mkdir(parents=True, exist_ok=True)
    # Multilogue 03 Layer B: Assess entry is k=1; Propose split grows grain.
    k = 1
    fit = mppca_fit(X, k=k, sigma2=0.05, seed=7, max_iter=50, n_init=10)
    keys = topic_keys(k)
    R = np.asarray(fit["responsibilities"], float)
    sigma2 = float(fit["sigma2"])
    uq_by_topic = rebuild_uq_by_topic(
        X,
        R,
        phrases=phrases,
        sigma2=sigma2,
        component_fits=fit["component_fits"],
    )
    focus0 = keys[0]
    records = [
        {
            "Name": "corpus",
            "Title": title,
            "source": source,
            "phrases": phrases,
            "embeddings": X.tolist(),
        }
    ]
    topic_labels = {key: f"Topic {i}" for i, key in enumerate(keys)}
    # Prefer live naming when the bake already saw OPENAI_API_KEY (.env).
    label_model = (
        "gpt-4.1-mini" if os.getenv("OPENAI_API_KEY") else "stub"
    )
    score = {
        "Name": "corpus",
        "focus_topic": focus0,
        "selected_phrase": None,
        "topic_keys": keys,
        "topic_labels": topic_labels,
        "responsibilities": R.tolist(),
        "uq_by_topic": uq_by_topic,
        "uq_spec": uq_by_topic[focus0],
        "sigma2": sigma2,
        "sigma2_mode": "fixed",
        "em_accept": 40,
        "em_preview": 5,
        "label_prompt": _label_prompt_from_referia_yml(),
        "label_model": label_model,
        "pending_proposal": None,
        "split_undo": None,
        "notes": None,
    }

    header = (
        "# Soft MPPCA corpus for subject_grain_uq demo (CIP-0017).\n"
        f"# source={source}\n"
        "# Built by build_records.py — re-run after changing mppca helpers.\n"
        "# Mutable Assess fields live in scores.yml (output).\n"
    )
    with (INFO / "records.yml").open("w", encoding="utf-8") as fh:
        fh.write(header)
        yaml.safe_dump(records, fh, sort_keys=False, allow_unicode=True)

    score_lines = [
        "# Seed output store — focus / click / Propose split write here at runtime.\n",
        f"- Name: {score['Name']}\n",
        f"  focus_topic: {score['focus_topic']}\n",
        "  selected_phrase:\n",
        "  topic_keys:\n",
    ]
    for key in keys:
        score_lines.append(f"  - {key}\n")
    score_lines.append("  topic_labels:\n")
    for key, lab in topic_labels.items():
        score_lines.append(f"    {key}: {lab!r}\n".replace("'", '"'))
    score_lines.append(f"  sigma2: {sigma2}\n")
    score_lines.append("  sigma2_mode: fixed\n")
    score_lines.append("  em_accept: 40\n")
    score_lines.append("  em_preview: 5\n")
    score_lines.append(f"  label_model: {label_model}\n")
    score_lines.append("  pending_proposal:\n")
    score_lines.append("  split_undo:\n")
    score_lines.append("  notes:\n")
    nested = {
        "responsibilities": score["responsibilities"],
        "uq_by_topic": score["uq_by_topic"],
        "uq_spec": score["uq_spec"],
        "label_prompt": score["label_prompt"],
    }
    nested_yaml = yaml.safe_dump(nested, sort_keys=False, allow_unicode=True)
    for line in nested_yaml.splitlines():
        score_lines.append(f"  {line}\n" if line else "\n")
    (INFO / "scores.yml").write_text("".join(score_lines), encoding="utf-8")
    print(f"Wrote 1 corpus record → {INFO / 'records.yml'}")
    print(f"source={source}, n_phrases={len(phrases)}, dim={X.shape[1]}")
    print(
        f"Assess entry k=1, σ²={sigma2:.4g}, n_iter={fit['n_iter']}, "
        f"topics={keys}, label_model={label_model}"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use planted English phrases (offline / CI); skip CIMT + OpenAI.",
    )
    parser.add_argument(
        "--max-units-per",
        type=int,
        default=40,
        help="Max CIMT sentences per format (dialogue / survey). Default 40.",
    )
    parser.add_argument(
        "--embed-dim",
        type=int,
        default=32,
        help="PCA dimension stored in records.yml after OpenAI embed.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download CIMT TSVs into info/.cache/cimt/.",
    )
    args = parser.parse_args(argv)

    _load_dotenv()

    if args.synthetic:
        X, phrases = _planted_embeddings(PHRASE_BANK)
        _write_yaml(
            phrases,
            X,
            title="Assess — soft subject grain (synthetic)",
            source="synthetic",
        )
        return

    phrases, meta = load_cimt_phrases(
        max_units_per=args.max_units_per, force=args.force_download
    )
    print(f"CIMT loaded: {meta}")
    X = embed_phrases(phrases, target_dim=args.embed_dim)
    _write_yaml(
        phrases,
        X,
        title="Assess — CIMT Bonn cycling (de)",
        source="cimt:Cycling-Dialogue-Bonn+Survey-Bonn",
    )


if __name__ == "__main__":
    main()
