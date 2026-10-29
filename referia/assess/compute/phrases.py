"""Stateless LLM phrase extraction for dialogue configs (CIP-0015).

Module-level callables. The registry is a name map only — this is not a
nested closure on ``Compute`` and does not read ``self.interface``.
"""

from __future__ import annotations

import difflib
import json
import re
from typing import Any, Mapping, Sequence

from lynguine.access.documents.segment import document_segment

from ...exceptions import ComputeError

__all__ = [
    "parse_extraction_payload",
    "llm_extract_phrases",
    "word_count_phrase",
    "quote_support",
    "dialogue_doc_id",
    "stamp_dialogue_doc_ids",
    "segment_dialogue_units",
]


def word_count_phrase(text: str) -> int:
    """Count whitespace-separated tokens in a phrase."""
    return len(str(text).split())


def _blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        if value != value:  # NaN
            return True
    except Exception:
        pass
    return str(value).strip() in ("", "nan", "None")


def _qnorm(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        re.sub(r"[^a-z0-9' ]+", " ", str(value).lower().replace("’", "'")),
    ).strip()


def quote_support(quote: Any, source: Any) -> float:
    """1.0 = verbatim. Otherwise the share of the quote's words found, in order, in the source.

    Quotes joined with ' … ' are checked part by part. Same contract as
    ``multilogue.text.quote_support`` (CIP-0015 optional quote threshold).
    """
    parts = [p for p in re.split(r"\s*(?:…|\.\.\.)\s*", str(quote or "")) if _qnorm(p)]
    if not parts:
        return 0.0
    src = _qnorm(source)
    src_t = src.split()
    total = matched = 0
    for part in parts:
        q = _qnorm(part)
        qt = q.split()
        total += len(qt)
        if f" {q} " in f" {src} ":
            matched += len(qt)
        else:
            matched += sum(
                block.size
                for block in difflib.SequenceMatcher(
                    None, qt, src_t, autojunk=False
                ).get_matching_blocks()
            )
    return round(matched / total, 3) if total else 0.0


def dialogue_doc_id(
    *,
    doc_id: Any = None,
    participant_id: Any = None,
    round: Any = None,
    filename: Any = None,
    format: Any = None,
    **_: Any,
) -> Any:
    """Paper document grain: ``{round}::{participant_id}`` for chatbot, filename for workshops.

    Recollective dumps are two files covering many conversations. Packing
    ``filename`` would weight 2 chatbot documents against 38 workshops.
    """
    if not _blank(participant_id):
        pid = str(participant_id).strip()
        rnd = str(round).strip() if not _blank(round) else ""
        return f"{rnd}::{pid}" if rnd else pid
    if not _blank(doc_id):
        return doc_id
    return None if _blank(filename) else filename


def stamp_dialogue_doc_ids(
    units: Sequence[Mapping[str, Any]] | None,
    *,
    round: Any = None,
    filename: Any = None,
    format: Any = None,
    min_unit_words: int | None = None,
    **_: Any,
) -> list[dict[str, Any]]:
    """Stamp ``doc_id`` on each unit dict. Optionally drop units under ``min_unit_words``."""
    out: list[dict[str, Any]] = []
    min_words = int(min_unit_words) if min_unit_words not in (None, "") else None
    for item in units or []:
        if hasattr(item, "to_dict"):
            item = item.to_dict()
        if not isinstance(item, Mapping):
            continue
        row = dict(item)
        if min_words is not None:
            n = row.get("word_count")
            if n is None:
                n = word_count_phrase(row.get("text") or row.get("extract_text") or "")
            if int(n) < min_words:
                continue
        row["doc_id"] = dialogue_doc_id(
            doc_id=row.get("doc_id"),
            participant_id=row.get("participant_id"),
            round=round if not _blank(round) else row.get("round"),
            filename=filename if not _blank(filename) else row.get("filename") or row.get("source_path"),
            format=format if not _blank(format) else row.get("format"),
        )
        out.append(row)
    return out


def segment_dialogue_units(path: str, **kwargs: Any) -> list[dict[str, Any]]:
    """``document_segment`` then stamp conversation ``doc_id`` (chatbot vs workshop grain)."""
    units = document_segment(path, **kwargs)
    return stamp_dialogue_doc_ids(
        units,
        round=kwargs.get("round"),
        filename=kwargs.get("filename"),
        format=kwargs.get("format"),
        min_unit_words=kwargs.get("min_unit_words"),
    )


def _as_kinds(kinds: Any) -> list[str]:
    if kinds is None:
        raise ValueError(
            "llm_extract_phrases requires kinds from config "
            "(e.g. concern, benefit, condition)."
        )
    if isinstance(kinds, str):
        parts = [p.strip() for p in kinds.replace(";", ",").split(",") if p.strip()]
        return parts or [kinds.strip()]
    return [str(k).strip() for k in kinds if str(k).strip()]


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
    extract_text: Any = None,
    context: Any = None,
    unit_text: Any = None,
    quote_support_threshold: float = 0.0,
) -> list[dict[str, Any]]:
    """Parse one kind's LLM reply into phrase dicts, applying drop rules.

    Accepts JSON (list, ``{\"phrases\": [...]}``) or newline text, including
    ``phrase || quote`` lines. Drops sentinels, empty lines, and phrases
    outside ``min_words``/``max_words``. Caps at ``max_items``.

    When ``quote_support_threshold`` > 0, keep only verified quotes
    (support ≥ threshold against ``extract_text`` or ``unit_text``) and
    drop quotes that match the bot question / facilitator context but not
    the extractable speaker text.
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
    thr = float(quote_support_threshold or 0.0)
    source = extract_text if not _blank(extract_text) else unit_text
    kept: list[dict[str, Any]] = []
    for phrase, quote in parsed or []:
        if not phrase:
            continue
        if phrase.strip().upper() == sentinel_folded:
            continue
        n_words = word_count_phrase(phrase)
        if n_words < int(min_words) or n_words > int(max_words):
            continue
        sup = quote_support(quote, source) if quote else 0.0
        if quote and thr > 0 and sup < thr:
            combined = " ".join(
                str(part)
                for part in (context, unit_text if not _blank(unit_text) else source)
                if not _blank(part)
            )
            if combined and quote_support(quote, combined) >= thr:
                continue
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
                "quote_support": sup,
                "verified": bool(quote) and sup >= thr if thr > 0 else True,
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
    participant_id: Any = None,
    round: Any = None,
    filename: Any = None,
    format: Any = None,
    extract_text: Any = None,
    context: Any = None,
    quote_support_threshold: float = 0.0,
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
    packed_doc_id = dialogue_doc_id(
        doc_id=doc_id,
        participant_id=participant_id,
        round=round,
        filename=filename,
        format=format,
    )
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
                doc_id=packed_doc_id,
                extract_text=extract_text,
                context=context,
                unit_text=text,
                quote_support_threshold=quote_support_threshold,
            )
        )
    return payload, phrases
