"""Topic-naming helpers for soft-topic Assess (prompt fill / stub / parse).

Prompt text belongs in the review config (``label_prompt`` field), not here.
Live LLM calls are wired in ``referia.assess.compute.Compute``.
"""

from __future__ import annotations

import json
import re
from typing import Any, Sequence

import numpy as np

from referia.assess.compute.mppca import example_phrases_for_soft_topics, topic_keys

__all__ = [
    "subject_grain_prepare_label",
    "subject_grain_stub_label",
    "subject_grain_parse_label_reply",
    "subject_grain_apply_focus_label",
]


def _topic_index(keys: Sequence[str], focus_topic: Any) -> int:
    key = str(focus_topic) if focus_topic is not None else ""
    if key in keys:
        return list(keys).index(key)
    try:
        idx = int(key.replace("T", ""))
        if 0 <= idx < len(keys):
            return idx
    except ValueError:
        pass
    return 0


def _phrase_list(phrases: Any, n: int) -> list[str]:
    if phrases is None:
        return [f"phrase {i}" for i in range(n)]
    out = [str(p) for p in phrases]
    if len(out) != n:
        out = (out + ["—"] * n)[:n]
    return out


def subject_grain_prepare_label(
    phrases: Any,
    responsibilities: Any,
    focus_topic: Any = "T0",
    label_prompt: Any = None,
    *,
    n_exemplars: int = 8,
) -> tuple[str, list[str], str]:
    """Build the filled naming prompt for the focus topic.

    Returns ``(user_prompt, exemplars, focus_key)``. Does not call an LLM.
    """
    R = np.asarray(responsibilities, dtype=float)
    if R.ndim != 2:
        raise ValueError(f"responsibilities must be 2-D, got shape {R.shape}")
    phrase_list = _phrase_list(phrases, R.shape[0])
    keys = topic_keys(R.shape[1])
    if focus_topic is None or focus_topic == "":
        focus = keys[0] if keys else "T0"
    else:
        focus = str(focus_topic)
    j = _topic_index(keys, focus)
    focus = keys[j] if keys else focus
    units = example_phrases_for_soft_topics(
        phrase_list, R, n_top=int(n_exemplars), n_sample=0, seed=0
    )
    exemplars = list(units[j].get("examples") or []) if j < len(units) else []
    if not exemplars:
        # Soft mass too thin — fall back to highest-mass phrases anyway.
        order = np.argsort(-R[:, j], kind="mergesort")[: int(n_exemplars)]
        exemplars = [phrase_list[i] for i in order if R[i, j] > 0]
    if label_prompt is None or not str(label_prompt).strip():
        raise ValueError(
            "label_prompt is required (set it in the review config / scores seed)"
        )
    tmpl = str(label_prompt)
    if "<<PHRASES>>" not in tmpl:
        raise ValueError("label_prompt must contain the <<PHRASES>> placeholder")
    bullet = "\n".join(f"- {p}" for p in exemplars) or "- (no exemplars)"
    return tmpl.replace("<<PHRASES>>", bullet), exemplars, focus


def subject_grain_stub_label(exemplars: Sequence[str], focus_key: str = "T0") -> str:
    """Offline label: first few content words of the top exemplar."""
    for text in exemplars:
        words = [w for w in re.split(r"\W+", str(text)) if w]
        if words:
            return " ".join(words[:6])[:80]
    return f"{focus_key} (unnamed)"


def subject_grain_parse_label_reply(raw: Any, exemplars: Sequence[str] | None = None) -> str:
    """Parse an LLM naming reply into a short label string."""
    text = (raw if isinstance(raw, str) else str(raw or "")).strip()
    if not text:
        return subject_grain_stub_label(exemplars or [], "topic")
    data: Any = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Models sometimes wrap JSON in fences or prose.
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                data = None
    label = None
    if isinstance(data, dict):
        label = data.get("label")
        if label is None:
            for key in ("title", "name", "thema", "heading"):
                if key in data:
                    label = data[key]
                    break
    if label is None:
        # Bare string reply — take first line.
        label = text.splitlines()[0].strip().strip('"').strip("'")
    label = re.sub(r"\s+", " ", str(label)).strip()
    if not label or label in {"?", "untitled", "unnamed"}:
        return subject_grain_stub_label(exemplars or [], "topic")
    return label[:80]


def subject_grain_apply_focus_label(
    topic_labels: Any,
    focus_key: str,
    label: str,
) -> dict:
    """Return a copy of ``topic_labels`` with ``focus_key`` set (catalogue write)."""
    out: dict = {}
    if isinstance(topic_labels, dict):
        out = {str(k): str(v) for k, v in topic_labels.items()}
    elif topic_labels is not None:
        try:
            out = {str(k): str(v) for k, v in dict(topic_labels).items()}
        except (TypeError, ValueError):
            out = {}
    out[str(focus_key)] = str(label)[:80]
    return out
