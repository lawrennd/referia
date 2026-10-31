"""Part B grounds coding (CIP-001E).

One LLM call per unit: each extracted point is labelled with a basis
(personal_experience, others_experience, professional_knowledge, principle,
public_example, project_materials, unclear). Matches the formats paper's
``basis`` prompt, as a referia field-in / field-out compute.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ...exceptions import ComputeError
from .phrases import _call_client

__all__ = [
    "BASES",
    "BASIS_ALIASES",
    "llm_classify_grounds",
    "normalise_basis",
]

BASES = (
    "personal_experience",
    "others_experience",
    "professional_knowledge",
    "principle",
    "public_example",
    "project_materials",
    "unclear",
)

BASIS_ALIASES = {
    "personal": "personal_experience",
    "own_experience": "personal_experience",
    "experience": "personal_experience",
    "other_experience": "others_experience",
    "professional": "professional_knowledge",
    "values": "principle",
    "value": "principle",
    "general_principle": "principle",
    "news": "public_example",
    "media": "public_example",
    "materials": "project_materials",
}

DEFAULT_SYSTEM = (
    "You classify the grounds people give for their views. Be conservative."
)


def normalise_basis(value: Any) -> str:
    v = re.sub(r"[\s\-/]+", "_", str(value or "").strip().lower())
    v = BASIS_ALIASES.get(v, v)
    return v if v in BASES else "unclear"


def _as_points(points: Any) -> list[dict[str, Any]]:
    if points is None or points == "":
        return []
    if isinstance(points, str):
        try:
            points = json.loads(points)
        except json.JSONDecodeError:
            return []
    if isinstance(points, dict):
        points = [points]
    out = []
    for item in list(points):
        if isinstance(item, dict):
            out.append(item)
        elif hasattr(item, "keys"):
            out.append(dict(item))
        elif item:
            out.append({"phrase": str(item)})
    return out


def _render_prompt(template: str, unit: str, points_block: str) -> str:
    text = str(template)
    text = text.replace("<<UNIT>>", unit)
    text = text.replace("<<POINTS>>", points_block)
    text = text.replace("{{ unit }}", unit)
    text = text.replace("{{ points }}", points_block)
    return text


def _parse_bases(raw: Any, n_points: int) -> dict[int, str]:
    text = (raw if isinstance(raw, str) else str(raw or "")).strip()
    data: Any = None
    if text:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(0))
                except json.JSONDecodeError:
                    data = None
    got: dict[int, str] = {}
    items = []
    if isinstance(data, dict):
        items = data.get("bases") or data.get("basis") or []
        if isinstance(items, dict):
            items = [items]
    elif isinstance(data, list):
        items = data
    for i, item in enumerate(items, 1):
        if not isinstance(item, dict):
            got.setdefault(i, normalise_basis(item))
            continue
        n_raw = item.get("n", i)
        m = re.search(r"\d+", str(n_raw))
        n = int(m.group()) if m else i
        got.setdefault(n, normalise_basis(item.get("basis", item.get("label"))))
    return got


def llm_classify_grounds(
    text: str,
    points: Any,
    *,
    prompt_template: str,
    model: str = "gpt-4.1-mini",
    temperature: float = 0.1,
    system_prompt: str | None = None,
    client: Any = None,
    context: str | None = None,
    **_kwargs,
) -> tuple[str, list[dict[str, Any]]]:
    """Label each point on a unit. Returns (payload, grounds list).

    Empty ``points`` is a no-op so **Classify all** can run before every
    unit has phrases. ``client`` is injected (stub in tests).
    """
    items = _as_points(points)
    if not items:
        return "", []
    if not prompt_template or not str(prompt_template).strip():
        raise ValueError(
            "llm_classify_grounds requires prompt_template from parameters."
        )
    unit = str(text or "").strip()
    ctx = str(context or "").strip()
    if ctx:
        unit = (
            "The chatbot asked (context only — code nothing from this):\n"
            f'"{ctx}"\n\nThe member of the public replied:\n"{unit}"'
        )
    lines = []
    for n, item in enumerate(items, 1):
        kind = item.get("kind") or item.get("type") or ""
        phrase = item.get("phrase") or ""
        quote = item.get("quote") or ""
        tag = f"[{kind}] " if kind else ""
        q = f' — "{quote}"' if quote else ""
        lines.append(f"{n}. {tag}{phrase}{q}")
    prompt = _render_prompt(str(prompt_template), unit[:4000], "\n".join(lines))
    reply = _call_client(
        client,
        prompt=prompt,
        model=model,
        temperature=float(temperature),
        system_prompt=system_prompt or DEFAULT_SYSTEM,
    )
    payload = reply if reply is not None else ""
    got = _parse_bases(payload, len(items))
    out: list[dict[str, Any]] = []
    for n, item in enumerate(items, 1):
        row = dict(item)
        row["basis"] = got.get(n, "unclear")
        out.append(row)
    return payload, out
