"""Stories-follow-stories methodology (CIP-001E).

Among labelled workshop speaker turns: if an earlier different
non-facilitator turn carried an experience-grounded point, does this
speaker's point also rest on experience? Compared to a within-transcript
shuffle (keeps each group's story rate) and, when a topic is present, a
within-topic control.

Grain is speaker turns, not 01_chunk units. Access rebuilds turns with
Jess ``Labels`` (``01_turns`` → ``turns.yml``). Address places 07
points and shuffles (``10_sequence``). Output is counts and gaps only —
no quote or turn text.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

import numpy as np

from .distance import _jsonable

__all__ = [
    "EXPERIENCE_BASES",
    "Labels",
    "speaker_key",
    "is_labelled",
    "build_turns",
    "place_points",
    "workshop_round_points",
    "turns_for_round",
    "run_rebuild_speaker_turns",
    "run_stories_follow_stories",
]

EXPERIENCE_BASES = frozenset({"personal_experience", "others_experience"})


def _qnorm(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        re.sub(r"[^a-z0-9' ]+", " ", str(value or "").lower().replace("’", "'")),
    ).strip()


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


class Labels:
    """Speaker-label patterns from facilitator names (Jess ``access.Labels``).

    ``Speaker N`` / ``S2`` / listed names / ``Facilitator``, case-insensitive.
    Tab counts as a separator. Mid-paragraph splits on `` Speaker N: ``.
    """

    def __init__(
        self,
        facilitator_names: Sequence[str] | None = None,
        facilitator_patterns: Sequence[str] | None = None,
    ):
        names = [
            re.escape(str(n).strip())
            for n in (facilitator_names or [])
            if str(n).strip()
        ]
        extra = [str(p) for p in (facilitator_patterns or []) if str(p).strip()]
        fac = "|".join(["Facilitator"] + names + extra) or "Facilitator"
        self.label = re.compile(
            r"^\s*(Speaker\s*\d+|S\d+|" + fac + r")\s*[:\-–.\t]",
            re.I,
        )
        self.facilitator = re.compile(
            r"^\s*(" + fac + r")\s*[:\-–.\t]",
            re.I,
        )
        self.inner = re.compile(
            r"\s(?=(?:Speaker\s*\d+|S\d+|" + fac + r")\s*:\s)",
            re.I,
        )

    def split_turns(self, par: str) -> list[str]:
        return [x.strip() for x in self.inner.split(par) if x.strip()]


def speaker_key(label: str) -> str:
    key = re.sub(r"\s+", "", str(label or "").lower())
    if key.startswith("speaker"):
        return "s" + key[len("speaker") :]
    return key


def is_labelled(
    paragraphs: Sequence[str],
    *,
    min_share: float = 0.5,
    facilitator_names: Sequence[str] | None = None,
    labels: Labels | None = None,
) -> bool:
    """True when at least ``min_share`` of nonempty paragraphs carry a speaker label."""
    rules = labels or Labels(facilitator_names)
    nonempty = [p for p in paragraphs if str(p).strip()]
    if not nonempty:
        return False
    n_lab = sum(
        1 for p in nonempty if rules.label.match(str(p).strip())
    )
    return (n_lab / len(nonempty)) >= float(min_share)


def build_turns(
    paragraphs: Sequence[str],
    *,
    doc_id: str,
    facilitator_names: Sequence[str] | None = None,
    treat_speaker_1_as_facilitator: bool = True,
    labels: Labels | None = None,
) -> list[dict[str, Any]]:
    """Rebuild speaker turns (Jess ``build_turns``: mid-paragraph split, no collapse).

    Output has ``doc_id``, ``turn_id``, ``turn_i``, ``speaker``, ``facilitator``,
    ``text``. Speaker keys are ``s1`` / ``s2`` / normalised names.
    """
    rules = labels or Labels(facilitator_names)
    turns: list[dict[str, Any]] = []
    for raw in paragraphs:
        line = str(raw or "").replace("\xa0", " ")
        if not line.strip():
            continue
        for piece in rules.split_turns(line):
            match = rules.label.match(piece)
            if match:
                label = re.sub(r"\s+", " ", match.group(1)).strip()
                speaker = speaker_key(label)
                is_fac = bool(rules.facilitator.match(piece))
                if treat_speaker_1_as_facilitator and speaker == "s1":
                    is_fac = True
                turns.append(
                    {
                        "doc_id": doc_id,
                        "speaker": speaker,
                        "facilitator": is_fac,
                        "text": piece[match.end() :].strip(),
                    }
                )
            elif turns:
                turns[-1]["text"] += " " + piece
    for i, turn in enumerate(turns):
        turn["turn_i"] = i
        turn["turn_id"] = f"{doc_id}::{i:04d}"
    return turns


def _quote_in_text(quote: str, text: str) -> bool:
    q = _qnorm(quote)
    if not q:
        return False
    src = _qnorm(text)
    if f" {q} " in f" {src} ":
        return True
    parts = [p for p in re.split(r"\s*(?:…|\.\.\.)\s*", str(quote)) if _qnorm(p)]
    return bool(parts) and all(_qnorm(p) in src for p in parts)


def workshop_round_points(
    coded: Sequence[Mapping[str, Any]] | None,
    labelled_round: str,
) -> tuple[list[dict[str, Any]], str | None]:
    """Workshop points for *labelled_round*, plus a hint when that slice is empty.

    07 Classify all can finish chatbot and autumn workshops while labelled
    spring workshop units are still uncoded. An empty slice is not the same
    as a missing ``grounds.yml``.
    """
    rows = [dict(row) for row in (coded or [])]
    wanted = str(labelled_round or "").strip()
    points = [
        row
        for row in rows
        if str(row.get("format") or row.get("group")) == "workshop"
        and str(row.get("round") or "") == wanted
    ]
    if points:
        return points, None
    if not rows:
        return [], "Run 07_grounds Classify all + Save first."
    n_ws = sum(
        1
        for row in rows
        if str(row.get("format") or row.get("group")) == "workshop"
    )
    return [], (
        f"07 saved {len(rows)} coded points ({n_ws} workshop), but 0 are "
        f"workshop · {wanted}. Classify remaining {wanted} workshop units "
        "on 07_grounds (skip-filled Classify all), then Save."
    )


def turns_for_round(
    turns: Sequence[Mapping[str, Any]] | None,
    labelled_round: str,
) -> tuple[list[dict[str, Any]], str | None]:
    """Speaker turns for *labelled_round*, plus a hint when that slice is empty."""
    rows = [dict(row) for row in (turns or [])]
    wanted = str(labelled_round or "").strip()
    kept = [
        row
        for row in rows
        if str(row.get("round") or "") == wanted
    ]
    if kept:
        return kept, None
    if not rows:
        return [], "Run 01_turns Rebuild + Save first."
    return [], (
        f"01_turns saved {len(rows)} speaker turns, but 0 are round "
        f"{wanted}. Rebuild turns on 01_turns, then Save."
    )


def _turns_assess_markdown(
    *,
    n_workshop: int,
    n_labelled: int,
    n_unlabelled: int,
    n_missing: int,
    min_share: float,
    n_turns: int,
    by_round: Mapping[str, int],
    n_names: int,
    coverage: Sequence[Mapping[str, Any]],
    examples: Sequence[Mapping[str, Any]],
) -> str:
    """Counts, per-file labelling, and structure-only example turns.

    Filenames are roster paths. Spoken text is not included.
    """
    round_bits = ", ".join(
        f"{rnd or 'unknown'} {n}" for rnd, n in sorted(by_round.items())
    ) or "none"
    names_bit = (
        f"{n_names} facilitator name(s) on the parameters row"
        if n_names
        else "0 facilitator names on the parameters row (Speaker N / S2 / Facilitator only)"
    )
    lines = [
        f"**{n_labelled} labelled workshop files** of {n_workshop} "
        f"workshop documents ({n_unlabelled} below the {min_share:.0%} "
        f"speaker-label share; {n_missing} missing on disk). "
        f"**{n_turns} speaker turns** ({round_bits}). {names_bit}. "
        "Jess Labels: Speaker N / S2 / facilitator names, tab or colon, "
        "mid-paragraph split. No turn text in this summary. "
        "10_sequence places 07 grounds on these turns.",
        "",
        "### Files (labelled or not)",
        "",
        "| file | round | labelled | turns | facilitator | participant |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in coverage:
        lines.append(
            "| {file} | {round} | {labelled} | {turns} | {facilitator} | {participant} |".format(
                file=row.get("file") or "",
                round=row.get("round") or "",
                labelled=row.get("labelled") or "",
                turns=row.get("turns") or 0,
                facilitator=row.get("facilitator") or 0,
                participant=row.get("participant") or 0,
            )
        )
    lines.extend(
        [
            "",
            "### Example turns (structure only)",
            "",
            "| file | turn_i | speaker | facilitator | words |",
            "| --- | ---: | --- | --- | ---: |",
        ]
    )
    if examples:
        for row in examples:
            lines.append(
                "| {file} | {turn_i} | {speaker} | {facilitator} | {words} |".format(
                    file=row.get("file") or "",
                    turn_i=row.get("turn_i"),
                    speaker=row.get("speaker") or "",
                    facilitator="yes" if row.get("facilitator") else "no",
                    words=row.get("words") or 0,
                )
            )
    else:
        lines.append("| — | — | — | — | — |")
    return "\n".join(lines)


def run_rebuild_speaker_turns(
    documents: Sequence[Mapping[str, Any]] | None = None,
    paragraphs_by_filename: Mapping[str, Sequence[str]] | None = None,
    *,
    facilitator_names: Sequence[str] | None = None,
    labelled_min_share: float = 0.5,
    treat_speaker_1_as_facilitator: bool = True,
    missing_hint: str | None = None,
    example_limit: int = 12,
    **_kwargs,
) -> tuple:
    """Access: labelled workshop speaker turns. Returns turns, markdown, n_turns.

    Markdown is coverage plus structure-only examples — no spoken text.
    """
    docs = [dict(row) for row in (documents or [])]
    paras_map = paragraphs_by_filename or {}
    names = list(facilitator_names or [])
    if isinstance(facilitator_names, str):
        names = [p.strip() for p in facilitator_names.split(",") if p.strip()]
    rules = Labels(names)
    min_share = float(labelled_min_share or 0.5)
    workshop = [
        row
        for row in docs
        if str(row.get("format") or row.get("group")) == "workshop"
    ]
    n_missing = 0
    n_unlabelled = 0
    n_labelled = 0
    by_round: dict[str, int] = {}
    turns: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []
    limit = max(0, int(example_limit or 0))
    for doc in workshop:
        rel = str(doc.get("filename") or "")
        rnd = str(doc.get("round") or "")
        paras = paras_map.get(rel)
        if paras is None:
            n_missing += 1
            coverage.append(
                {
                    "file": rel,
                    "round": rnd,
                    "labelled": "missing",
                    "turns": 0,
                    "facilitator": 0,
                    "participant": 0,
                }
            )
            continue
        if not is_labelled(paras, min_share=min_share, labels=rules):
            n_unlabelled += 1
            coverage.append(
                {
                    "file": rel,
                    "round": rnd,
                    "labelled": "no",
                    "turns": 0,
                    "facilitator": 0,
                    "participant": 0,
                }
            )
            continue
        n_labelled += 1
        recs = build_turns(
            paras,
            doc_id=rel,
            labels=rules,
            treat_speaker_1_as_facilitator=bool(
                treat_speaker_1_as_facilitator
            ),
        )
        for rec in recs:
            rec["round"] = rnd
            rec["format"] = "workshop"
            rec["filename"] = rel
        turns.extend(recs)
        by_round[rnd] = by_round.get(rnd, 0) + len(recs)
        n_fac = sum(1 for rec in recs if rec.get("facilitator"))
        coverage.append(
            {
                "file": rel,
                "round": rnd,
                "labelled": "yes",
                "turns": len(recs),
                "facilitator": n_fac,
                "participant": len(recs) - n_fac,
            }
        )
        if len(examples) < limit:
            for rec in recs:
                if len(examples) >= limit:
                    break
                examples.append(
                    {
                        "file": rel,
                        "turn_i": rec.get("turn_i"),
                        "speaker": rec.get("speaker") or "",
                        "facilitator": bool(rec.get("facilitator")),
                        "words": len(str(rec.get("text") or "").split()),
                    }
                )
    if not workshop:
        hint = missing_hint or (
            "No workshop rows in documents.yml. Run 01_chunk catalog first."
        )
        return [], hint, 0
    md = _turns_assess_markdown(
        n_workshop=len(workshop),
        n_labelled=n_labelled,
        n_unlabelled=n_unlabelled,
        n_missing=n_missing,
        min_share=min_share,
        n_turns=len(turns),
        by_round=by_round,
        n_names=len(names),
        coverage=coverage,
        examples=examples,
    )
    return _jsonable(turns), md, len(turns)


def place_points(
    turns: Sequence[Mapping[str, Any]],
    points: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Attach each point to the first turn in the same document whose text contains the quote."""
    by_doc: dict[str, list[Mapping[str, Any]]] = {}
    for turn in turns:
        by_doc.setdefault(str(turn.get("doc_id")), []).append(turn)
    placed: list[dict[str, Any]] = []
    for point in points:
        doc = str(point.get("doc_id") or "")
        quote = str(point.get("quote") or "")
        candidates = by_doc.get(doc) or []
        hit = None
        for turn in candidates:
            if _quote_in_text(quote, str(turn.get("text") or "")):
                hit = turn
                break
        row = dict(point)
        if hit is None:
            row["turn_i"] = None
            row["speaker"] = None
            row["facilitator"] = None
        else:
            row["turn_i"] = hit.get("turn_i")
            row["speaker"] = hit.get("speaker")
            row["facilitator"] = bool(hit.get("facilitator"))
        placed.append(row)
    return placed


def _is_experience(basis: Any) -> bool:
    return str(basis or "").strip() in EXPERIENCE_BASES


def _gap(
    speakers: np.ndarray,
    story: np.ndarray,
    lookback: int,
    *,
    same_unit: np.ndarray | None = None,
) -> float:
    """P(this is a story | an earlier different-speaker turn in L was a story)."""
    n = len(speakers)
    if n == 0:
        return float("nan")
    hits = 0
    cond = 0
    for i in range(n):
        lo = max(0, i - lookback)
        earlier = False
        for j in range(lo, i):
            if speakers[j] == speakers[i]:
                continue
            if same_unit is not None and same_unit[j] == same_unit[i]:
                continue
            if story[j]:
                earlier = True
                break
        if not earlier:
            continue
        cond += 1
        if story[i]:
            hits += 1
    return (hits / cond) if cond else float("nan")


def _shuffle_gaps(
    speakers: np.ndarray,
    story: np.ndarray,
    lookback: int,
    rng: np.random.Generator,
    n_shuffles: int,
    *,
    same_unit: np.ndarray | None = None,
) -> np.ndarray:
    """Shuffle story flags within speaker, keeping each speaker's rate."""
    out = np.empty(n_shuffles, dtype=float)
    for s in range(n_shuffles):
        perm = story.copy()
        for spk in np.unique(speakers):
            idx = np.where(speakers == spk)[0]
            perm[idx] = rng.permutation(story[idx])
        out[s] = _gap(speakers, perm, lookback, same_unit=same_unit)
    return out


def _gap_within_topic(
    speakers: np.ndarray,
    story: np.ndarray,
    topics: np.ndarray,
    lookback: int,
) -> float:
    """Same as ``_gap``, but only count earlier stories that share this turn's topic."""
    n = len(speakers)
    if n == 0:
        return float("nan")
    hits = 0
    cond = 0
    for i in range(n):
        if topics[i] is None or (isinstance(topics[i], float) and not np.isfinite(topics[i])):
            continue
        topic = topics[i]
        lo = max(0, i - lookback)
        earlier = False
        for j in range(lo, i):
            if speakers[j] == speakers[i]:
                continue
            if topics[j] != topic:
                continue
            if story[j]:
                earlier = True
                break
        if not earlier:
            continue
        cond += 1
        if story[i]:
            hits += 1
    return (hits / cond) if cond else float("nan")


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
                cells.append(f"{val:.3f}")
            else:
                cells.append(str(val))
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *body])


def run_stories_follow_stories(
    turns: Sequence[Mapping[str, Any]] | None = None,
    points: Sequence[Mapping[str, Any]] | None = None,
    *,
    lookbacks: Sequence[int] | None = None,
    n_shuffles: int = 500,
    seed: int = 0,
    treat_speaker_1_as_facilitator: bool = True,
    cross_unit_only: bool = False,
    missing_hint: str | None = None,
    **_kwargs,
) -> tuple:
    """Look-back shuffle test on labelled workshop turns. Returns rows, markdown, n_turns."""
    if isinstance(lookbacks, str):
        lookbacks = [int(x) for x in lookbacks.split(",") if x.strip()]
    lookbacks = [int(x) for x in (lookbacks or [1, 2, 3, 5])]
    n_shuffles = max(1, _as_int(n_shuffles, 500))
    seed = _as_int(seed, 0)
    if not turns:
        hint = missing_hint or (
            "No labelled workshop turns. Run 01_turns Rebuild + Save first."
        )
        return [], hint, 0
    if not points:
        hint = missing_hint or (
            "No workshop grounds for the labelled round. Classify remaining "
            "spring workshop units on 07_grounds (skip-filled Classify all), "
            "then Save."
        )
        return [], hint, 0

    placed = place_points(turns, points)
    # One row per (doc, turn) among non-facilitator turns that received a point.
    by_turn: dict[tuple, dict[str, Any]] = {}
    for row in placed:
        if row.get("turn_i") is None:
            continue
        if row.get("facilitator"):
            continue
        key = (str(row.get("doc_id")), int(row["turn_i"]))
        rec = by_turn.setdefault(
            key,
            {
                "doc_id": key[0],
                "turn_i": key[1],
                "speaker": row.get("speaker"),
                "unit_id": row.get("unit_id"),
                "topic": row.get("topic"),
                "story": False,
            },
        )
        if _is_experience(row.get("basis")):
            rec["story"] = True
        if rec.get("topic") in (None, "") and row.get("topic") not in (None, ""):
            rec["topic"] = row.get("topic")

    if not by_turn:
        md = (
            "Turns rebuilt, but no 07 quotes landed in a non-facilitator "
            "turn. Check quote placement (substring of the speaker turn) "
            "and that 07 Save wrote `grounds.yml`."
        )
        return [], md, len(turns)

    docs = sorted({rec["doc_id"] for rec in by_turn.values()})
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    n_story_turns = sum(1 for rec in by_turn.values() if rec["story"])

    for lookback in lookbacks:
        obs_gaps = []
        null_means = []
        null_p = []
        topic_gaps = []
        for doc in docs:
            recs = sorted(
                (r for r in by_turn.values() if r["doc_id"] == doc),
                key=lambda r: r["turn_i"],
            )
            speakers = np.array([str(r["speaker"]) for r in recs])
            story = np.array([bool(r["story"]) for r in recs])
            units = np.array([str(r.get("unit_id") or "") for r in recs])
            topics = np.array([r.get("topic") for r in recs], dtype=object)
            same_unit = units if cross_unit_only else None
            obs = _gap(speakers, story, lookback, same_unit=same_unit)
            obs_gaps.append(obs)
            null = _shuffle_gaps(
                speakers,
                story,
                lookback,
                rng,
                n_shuffles,
                same_unit=same_unit,
            )
            null_means.append(float(np.nanmean(null)))
            if np.isfinite(obs):
                null_p.append(float(np.mean(null >= obs)))
            if any(t not in (None, "") for t in topics):
                topic_gaps.append(_gap_within_topic(speakers, story, topics, lookback))
        obs_mean = float(np.nanmean(obs_gaps)) if obs_gaps else float("nan")
        null_mean = float(np.nanmean(null_means)) if null_means else float("nan")
        rows.append(
            {
                "lookback": lookback,
                "treat_speaker_1_as_facilitator": bool(
                    treat_speaker_1_as_facilitator
                ),
                "cross_unit_only": bool(cross_unit_only),
                "n_docs": len(docs),
                "n_turns_with_points": len(by_turn),
                "n_story_turns": n_story_turns,
                "observed": None if not np.isfinite(obs_mean) else round(obs_mean, 4),
                "shuffled": None if not np.isfinite(null_mean) else round(null_mean, 4),
                "gap": (
                    None
                    if not (np.isfinite(obs_mean) and np.isfinite(null_mean))
                    else round(obs_mean - null_mean, 4)
                ),
                "p_ge_observed": (
                    None
                    if not null_p
                    else round(float(np.mean(null_p)), 4)
                ),
                "within_topic": (
                    None
                    if not topic_gaps
                    else round(float(np.nanmean(topic_gaps)), 4)
                ),
            }
        )

    md_rows = _md_table(
        rows,
        [
            ("L", "lookback"),
            ("observed", "observed"),
            ("shuffled", "shuffled"),
            ("gap", "gap"),
            ("P(null ≥ obs)", "p_ge_observed"),
            ("within-topic", "within_topic"),
        ],
    )
    topic_note = (
        "Within-topic is the same look-back restricted to earlier stories "
        "that share this turn's topic (so 'the topic invites stories' is "
        "not mistaken for uptake)."
        if any(r.get("within_topic") is not None for r in rows)
        else (
            "Within-topic is blank: no topic id on the placed points "
            "(VQ cell / grain membership). The shuffle test does not wait on that."
        )
    )
    md = (
        f"**{len(docs)} labelled workshop transcripts**, "
        f"{len(by_turn)} non-facilitator turns that received a 07 point "
        f"({n_story_turns} with an experience ground). "
        f"{n_shuffles} within-transcript shuffles. "
        "Observed is P(this turn is a story | one of the previous L turns "
        "by a *different* non-facilitator was a story). "
        "Shuffle keeps each speaker's story rate. "
        "Own-words recode is a later column — this table is **main-run 07 codes**. "
        "No quote text is stored.\n\n"
        f"{topic_note}\n\n"
        + md_rows
    )
    return _jsonable(rows), md, len(turns)
