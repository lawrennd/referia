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
    "subject_grain_keys_needing_names",
    "_is_provisional_label",
    "_short_parent_for_placeholder",
    "_prune_ghost_parents",
]


def _is_provisional_label(label: Any, key: Any = None) -> bool:
    """True for seed / Propose placeholders that still need a human title.

    Covers ``Topic N`` bake seeds, bare catalogue keys (``T0``), empty
    strings, and Propose placeholders like ``«Parent» → (unnamed 0)``.
    """
    text = str(label or "").strip()
    if not text:
        return True
    lower = text.lower()
    if "(unnamed" in lower:
        return True
    if re.fullmatch(r"Topic\s+\d+", text, flags=re.IGNORECASE):
        return True
    if key is not None and text == str(key):
        return True
    if re.fullmatch(r"T\d+", text):
        return True
    return False


def _short_parent_for_placeholder(
    parent_label: Any,
    parent_key: Any = None,
) -> str:
    """Parent fragment for Propose placeholders and overlay titles.

    Never nests an existing ``«…» → (unnamed N)`` into another placeholder.
    Named parents pass through unchanged; provisional labels peel to an
    innermost ``Topic N`` seed when present, else the catalogue key.
    """
    text = str(parent_label or "").strip()
    if text and not _is_provisional_label(text, parent_key):
        return text
    seed = re.search(r"Topic\s+\d+", text, flags=re.IGNORECASE)
    if seed:
        # Normalise spacing / capitalisation for stable UI strings.
        num = re.search(r"\d+", seed.group(0))
        return f"Topic {num.group(0)}" if num else seed.group(0)
    if parent_key is not None and str(parent_key).strip():
        return str(parent_key)
    return "parent"


# Back-compat alias used in older tests / call sites.
def _is_unnamed_label(label: Any) -> bool:
    return _is_provisional_label(label)


def subject_grain_keys_needing_names(
    topic_labels: Any,
    focus_topic: Any,
    topic_keys: Any = None,
) -> list[str]:
    """Keys to name on a Name click: focus first, then other provisional topics.

    Propose leaves children as ``«Parent» → (unnamed t)`` without calling an
    LLM. Bake seeds use ``Topic N``. One Name action covers the focus and
    every remaining provisional label so the analyst need not re-focus each
    child (or the initial seed) and click again.
    """
    labels: dict[str, str] = {}
    if isinstance(topic_labels, dict):
        labels = {str(k): str(v) for k, v in topic_labels.items()}
    keys = [str(k) for k in (topic_keys or list(labels.keys()))]
    if not keys and labels:
        keys = list(labels.keys())
    focus = (
        str(focus_topic)
        if focus_topic not in (None, "")
        else (keys[0] if keys else "T0")
    )
    provisionals = [
        key
        for key in keys
        if _is_provisional_label(labels.get(key, key), key)
    ]
    if not provisionals:
        # Nothing provisional — still name the focus on an explicit click.
        if focus in keys:
            return [focus]
        return keys[:1] if keys else []
    ordered: list[str] = []
    # Focus first only when it still needs a title (do not re-LLM named topics
    # just because they are selected while siblings are provisional).
    if focus in provisionals:
        ordered.append(focus)
    for key in provisionals:
        if key not in ordered:
            ordered.append(key)
    return ordered


def _prune_ghost_parents(
    topic_parent: Any,
    topic_labels: Any,
) -> dict[str, str | None]:
    """Drop parent pointers whose label is no longer a live topic.

    After a soft split the parent *topic* is replaced by its children, but
    ``topic_parent`` still stores the old label (often the seed ``Topic 0``).
    Keeping that ghost makes the UI look like naming failed (``← Topic 0`` /
    ``(orphaned)``). Clear pointers that match no live label; ancestry for
    named parents that were split away is rendered as a virtual tree header.
    """
    labels: dict[str, str] = {}
    if isinstance(topic_labels, dict):
        labels = {str(k): str(v) for k, v in topic_labels.items()}
    live = {str(v) for v in labels.values() if v not in (None, "")}
    live |= set(labels.keys())
    out: dict[str, str | None] = {}
    if isinstance(topic_parent, dict):
        for k, v in topic_parent.items():
            if v in (None, "", "null"):
                out[str(k)] = None
            elif str(v) in live:
                out[str(k)] = str(v)
            elif _is_provisional_label(v):
                # Seed / unnamed ghost — drop so Name leaves a clean tree.
                out[str(k)] = None
            else:
                # Named parent that was split away — keep for virtual header.
                out[str(k)] = str(v)
    for key in labels:
        out.setdefault(str(key), None)
    return out


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
    topic_parent: Any = None,
    topic_keys: Any = None,
    responsibilities: Any = None,
    mass_threshold: float = 0.05,
) -> tuple:
    """Apply a new focus label and keep genealogy pointers consistent.

    Returns ``(topic_labels, topic_parent, topic_tree)``.  Children that
    pointed at the old label are remapped to the new one; ``topic_tree`` is
    the derived Markdown view (same formatter as Propose / Undo), including
    the soft-association table when ``responsibilities`` are supplied.
    """
    from referia.assess.compute.mppca import format_topic_tree_markdown

    out: dict = {}
    if isinstance(topic_labels, dict):
        out = {str(k): str(v) for k, v in topic_labels.items()}
    elif topic_labels is not None:
        try:
            out = {str(k): str(v) for k, v in dict(topic_labels).items()}
        except (TypeError, ValueError):
            out = {}
    focus = str(focus_key)
    old_label = out.get(focus, focus)
    new_label = str(label)[:80]
    out[focus] = new_label

    keys = [str(k) for k in (topic_keys or list(out.keys()))]
    parent: dict[str, str | None] = {}
    if isinstance(topic_parent, dict):
        for k, v in topic_parent.items():
            parent[str(k)] = None if v in (None, "", "null") else str(v)
    for key in keys:
        parent.setdefault(key, None)
    if old_label != new_label:
        for key, p in list(parent.items()):
            if p == old_label:
                parent[key] = new_label
    parent = _prune_ghost_parents(parent, out)
    tree = format_topic_tree_markdown(
        keys,
        out,
        parent,
        focus,
        responsibilities=responsibilities,
        mass_threshold=float(mass_threshold),
    )
    return (out, parent, tree)
