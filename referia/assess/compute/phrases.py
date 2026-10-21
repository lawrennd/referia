"""Stateless LLM phrase extraction for dialogue configs (CIP-0015).

Module-level callables. The registry is a name map only — this is not a
nested closure on ``Compute`` and does not read ``self.interface``.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from ...exceptions import ComputeError

__all__ = [
    "parse_extraction_payload",
    "llm_extract_phrases",
    "word_count_phrase",
]


def word_count_phrase(text: str) -> int:
    """Count whitespace-separated tokens in a phrase."""
    return len(str(text).split())


def _as_kinds(kinds: Any) -> list[str]:
    if kinds is None:
        raise ValueError(
            "llm_extract_phrases requires kinds from config "
            "(e.g. concern, benefit, condition)."
        )
    if isinstance(kinds, str):
        return [kinds]
    return [str(k) for k in kinds]


def _sentinel_for(kind: str, sentinels: Mapping[str, str] | None, **kwargs) -> str:
    if sentinels and kind in sentinels:
        return str(sentinels[kind])
    key = f"sentinel_{kind}"
    if key in kwargs and kwargs[key]:
        return str(kwargs[key])
    if kwargs.get("sentinel"):
        return str(kwargs["sentinel"])
    return f"NO_{kind.upper()}"


def _render_prompt(template: str, *, text: str, kind: str, sentinel: str) -> str:
    rendered = str(template)
    rendered = rendered.replace("<<TEXT>>", str(text))
    rendered = rendered.replace("{{ kind }}", str(kind))
    rendered = rendered.replace("{{ sentinel }}", str(sentinel))
    rendered = rendered.replace("{{kind}}", str(kind))
    rendered = rendered.replace("{{sentinel}}", str(sentinel))
    return rendered


def _split_phrase_quote(line: str) -> tuple[str, str | None]:
    if "||" in line:
        phrase, quote = line.split("||", 1)
        phrase = phrase.strip()
        quote = quote.strip() or None
        return phrase, quote
    return line.strip(), None


def _from_json(payload: Any) -> list[tuple[str, str | None]] | None:
    if isinstance(payload, dict):
        items = payload.get("phrases", payload.get("items"))
        if items is None:
            return None
        payload = items
    if not isinstance(payload, list):
        return None
    out: list[tuple[str, str | None]] = []
    for item in payload:
        if isinstance(item, str):
            out.append(_split_phrase_quote(item))
        elif isinstance(item, dict):
            phrase = str(item.get("phrase") or item.get("text") or "").strip()
            quote = item.get("quote")
            quote = str(quote).strip() if quote else None
            if phrase:
                out.append((phrase, quote))
        else:
            continue
    return out


def parse_extraction_payload(
    payload: Any,
    *,
    kind: str,
    sentinel: str,
    min_words: int = 3,
    max_words: int = 10,
    max_items: int = 8,
    chunk_id: Any = None,
    doc_id: Any = None,
) -> list[dict[str, Any]]:
    """Parse one kind's LLM reply into phrase dicts, applying drop rules.

    Accepts JSON (list, ``{\"phrases\": [...]}``) or newline text, including
    ``phrase || quote`` lines. Drops sentinels, empty lines, and phrases
    outside ``min_words``/``max_words``. Caps at ``max_items``.
    """
    raw: list[tuple[str, str | None]] = []
    parsed = None
    if isinstance(payload, (dict, list)):
        parsed = _from_json(payload)
    elif isinstance(payload, str):
        text = payload.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                parsed = _from_json(json.loads(text))
            except json.JSONDecodeError:
                parsed = None
        if parsed is None:
            parsed = [
                _split_phrase_quote(line)
                for line in text.splitlines()
                if line.strip()
            ]
    else:
        parsed = []

    sentinel_folded = str(sentinel).strip().upper()
    kept: list[dict[str, Any]] = []
    for phrase, quote in parsed or []:
        if not phrase:
            continue
        if phrase.strip().upper() == sentinel_folded:
            continue
        n_words = word_count_phrase(phrase)
        if n_words < int(min_words) or n_words > int(max_words):
            continue
        idx = len(kept)
        phrase_id_parts = [str(p) for p in (chunk_id, kind, idx) if p not in (None, "")]
        kept.append(
            {
                "phrase": phrase,
                "kind": kind,
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "quote": quote,
                "phrase_id": ":".join(phrase_id_parts) if phrase_id_parts else str(idx),
            }
        )
        if len(kept) >= int(max_items):
            break
    return kept


def _call_client(client: Any, **kwargs) -> str:
    if client is None:
        from ...util.llm import get_llm_manager

        client = get_llm_manager()
    if hasattr(client, "call"):
        return client.call(**kwargs)
    raise ComputeError(
        "llm_extract_phrases client has no call(). Inject LLMManager or a stub."
    )


def llm_extract_phrases(
    text: str,
    *,
    prompt_template: str,
    kinds: Sequence[str] | str,
    chunk_id: Any = None,
    doc_id: Any = None,
    model: str = "gpt-4o-mini",
    min_words: int = 3,
    max_words: int = 10,
    max_items: int = 8,
    sentinels: Mapping[str, str] | None = None,
    temperature: float = 0.2,
    system_prompt: str | None = None,
    client: Any = None,
    **kwargs,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Extract short phrases from one chunk. Returns payload and phrase dicts.

    ``prompt_template`` and ``model`` come from config. ``client`` is injected
    (stub in tests; ``LLMManager`` in production). Does not replace
    ``llm_extract``.
    """
    if not prompt_template or not str(prompt_template).strip():
        raise ValueError(
            "llm_extract_phrases requires prompt_template from constants or args."
        )
    if text is None or not str(text).strip():
        return {}, []

    kind_list = _as_kinds(kinds)
    payload: dict[str, str] = {}
    phrases: list[dict[str, Any]] = []
    default_system = (
        system_prompt
        or "Extract short public-dialogue phrases. Reply with one phrase per "
        "line, or JSON. If none, reply with exactly the sentinel."
    )
    for kind in kind_list:
        sentinel = _sentinel_for(kind, sentinels, **kwargs)
        prompt = _render_prompt(
            prompt_template, text=str(text)[:4000], kind=kind, sentinel=sentinel
        )
        reply = _call_client(
            client,
            prompt=prompt,
            model=model,
            temperature=float(temperature),
            system_prompt=default_system,
        )
        payload[kind] = reply if reply is not None else ""
        phrases.extend(
            parse_extraction_payload(
                payload[kind],
                kind=kind,
                sentinel=sentinel,
                min_words=min_words,
                max_words=max_words,
                max_items=max_items,
                chunk_id=chunk_id,
                doc_id=doc_id,
            )
        )
    return payload, phrases
