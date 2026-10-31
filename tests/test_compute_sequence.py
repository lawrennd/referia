"""CIP-001E: stories-follow-stories methodology (no quote text in output)."""

from referia.assess.compute.sequence import (
    Labels,
    build_turns,
    is_labelled,
    place_points,
    run_rebuild_speaker_turns,
    run_stories_follow_stories,
    turns_for_round,
    workshop_round_points,
)


def test_is_labelled_needs_majority_speaker_tags():
    labelled = [
        "Speaker 1: hello everyone",
        "Speaker 2: I saw this last year",
        "unlabelled aside",
    ]
    assert is_labelled(labelled, min_share=0.5)
    assert not is_labelled(["hello", "there"], min_share=0.5)


def test_labels_accept_tab_compact_and_named_facilitator():
    labels = Labels(["Alex"])
    assert labels.label.match("S2:\thello")
    assert labels.label.match("Speaker2: hello")
    assert labels.label.match("speaker 2: hello")
    assert labels.label.match("Alex: welcome")
    assert is_labelled(["S2:\thello", "S3:\tthere"], facilitator_names=["Alex"])


def test_build_turns_marks_speaker_1_and_named_facilitator():
    turns = build_turns(
        [
            "Alex: welcome",
            "Speaker 2: I saw this at work last year",
            "Speaker 2: and the team agreed",
            "Speaker 3: in principle we should",
        ],
        doc_id="workshops/spring.docx",
        facilitator_names=["Alex"],
        treat_speaker_1_as_facilitator=True,
    )
    assert len(turns) == 4
    assert turns[0]["facilitator"] is True
    assert turns[1]["speaker"] == "s2"
    assert turns[1]["facilitator"] is False
    assert "team agreed" in turns[2]["text"]
    assert turns[2]["speaker"] == "s2"


def test_place_points_matches_quote_to_turn():
    turns = build_turns(
        [
            "Speaker 2: I saw this at work last year",
            "Speaker 3: in principle we should",
        ],
        doc_id="workshops/spring.docx",
        facilitator_names=[],
    )
    placed = place_points(
        turns,
        [
            {
                "doc_id": "workshops/spring.docx",
                "quote": "I saw this at work last year",
                "basis": "personal_experience",
            }
        ],
    )
    assert placed[0]["turn_i"] == 0
    assert placed[0]["speaker"] == "s2"


def test_stories_follow_stories_gap_positive_when_stories_cluster():
    turns = []
    for doc in ("workshops/a.docx", "workshops/b.docx"):
        turns.extend(
            build_turns(
                [
                    "Alex: welcome",
                    "Speaker 2: I saw this last year at work",
                    "Speaker 3: my neighbour had the same",
                    "Speaker 2: the team did it that year too",
                    "Speaker 3: a colleague told me the same",
                    "Speaker 2: in principle councils should",
                    "Speaker 3: we must consider the rules",
                ],
                doc_id=doc,
                facilitator_names=["Alex"],
            )
        )
    points = []
    for doc in ("workshops/a.docx", "workshops/b.docx"):
        points.extend(
            [
                {
                    "doc_id": doc,
                    "quote": "I saw this last year at work",
                    "basis": "personal_experience",
                    "unit_id": f"{doc}::c0003",
                },
                {
                    "doc_id": doc,
                    "quote": "my neighbour had the same",
                    "basis": "others_experience",
                    "unit_id": f"{doc}::c0004",
                },
                {
                    "doc_id": doc,
                    "quote": "the team did it that year too",
                    "basis": "personal_experience",
                    "unit_id": f"{doc}::c0005",
                },
                {
                    "doc_id": doc,
                    "quote": "a colleague told me the same",
                    "basis": "others_experience",
                    "unit_id": f"{doc}::c0006",
                },
                {
                    "doc_id": doc,
                    "quote": "in principle councils should",
                    "basis": "principle",
                    "unit_id": f"{doc}::c0007",
                },
                {
                    "doc_id": doc,
                    "quote": "we must consider the rules",
                    "basis": "principle",
                    "unit_id": f"{doc}::c0008",
                },
            ]
        )
    rows, md, n_turns = run_stories_follow_stories(
        turns,
        points,
        lookbacks=[1],
        n_shuffles=40,
        seed=0,
    )
    assert n_turns == 14
    assert rows
    assert rows[0]["observed"] > rows[0]["shuffled"]
    assert rows[0]["gap"] > 0
    assert "I saw this" not in md
    assert "main-run 07" in md
    assert "Own-words" in md


def test_workshop_round_points_distinguishes_missing_from_wrong_round():
    empty, empty_hint = workshop_round_points([], "spring_2026")
    assert empty == []
    assert "Classify all + Save" in empty_hint
    autumn = [
        {"format": "workshop", "round": "autumn_2025", "phrase_id": "a"},
        {"format": "chatbot", "round": "spring_2026", "phrase_id": "b"},
    ]
    points, hint = workshop_round_points(autumn, "spring_2026")
    assert points == []
    assert "0 are workshop · spring_2026" in hint
    assert "skip-filled" in hint
    spring = autumn + [
        {"format": "workshop", "round": "spring_2026", "phrase_id": "c"},
    ]
    kept, ok = workshop_round_points(spring, "spring_2026")
    assert ok is None
    assert [row["phrase_id"] for row in kept] == ["c"]


def test_rebuild_speaker_turns_counts_labelled_files_without_text():
    documents = [
        {"filename": "workshops/a.docx", "format": "workshop", "round": "spring_2026"},
        {"filename": "workshops/b.docx", "format": "workshop", "round": "spring_2026"},
        {"filename": "workshops/plain.docx", "format": "workshop", "round": "autumn_2025"},
        {"filename": "chatbot/x.docx", "format": "chatbot", "round": "spring_2026"},
    ]
    paragraphs = {
        "workshops/a.docx": [
            "Speaker 1: welcome everyone",
            "Speaker 2: I saw this last year at work",
            "Speaker 3: in principle we should",
        ],
        "workshops/b.docx": [
            "S2:\tI saw this last year at work",
            "S3:\tin principle we should",
        ],
        "workshops/plain.docx": ["hello", "there", "no labels"],
    }
    turns, md, n = run_rebuild_speaker_turns(
        documents,
        paragraphs,
        facilitator_names=["Alex"],
    )
    assert n == 5
    assert len(turns) == 5
    assert "2 labelled" in md
    assert "5 speaker turns" in md
    assert "I saw this" not in md
    assert "welcome everyone" not in md
    assert "workshops/a.docx" in md
    assert "workshops/plain.docx" in md
    assert "| yes |" in md
    assert "| no |" in md
    assert "s2" in md
    assert "facilitator" in md
    kept, hint = turns_for_round(turns, "spring_2026")
    assert hint is None
    assert len(kept) == 5
    empty, wait = turns_for_round([], "spring_2026")
    assert empty == []
    assert "01_turns" in wait


def test_info_yaml_rows_cache_invalidates_on_mtime(tmp_path):
    from referia.assess.compute import Compute

    info = tmp_path / "info"
    info.mkdir()
    path = info / "turns.yml"
    path.write_text("- turn_id: a\n", encoding="utf-8")

    class _Iface:
        directory = None
        def get(self, key, default=None):
            if key == "input":
                return {"directory": str(info), "filename": "constants.yml"}
            return default

    compute = Compute({"input": {}})
    compute._interface = _Iface()
    first = compute._load_info_yaml_rows("turns.yml")
    assert [row.get("turn_id") for row in first] == ["a"]
    path.write_text("- turn_id: a\n- turn_id: b\n", encoding="utf-8")
    import os

    os.utime(path, (path.stat().st_mtime + 2, path.stat().st_mtime + 2))
    second = compute._load_info_yaml_rows("turns.yml")
    assert [row.get("turn_id") for row in second] == ["a", "b"]


def test_stories_follow_stories_waiting_on_grounds():
    rows, md, n = run_stories_follow_stories(
        [{"doc_id": "x", "turn_i": 0, "speaker": "Speaker 2", "facilitator": False, "text": "hi"}],
        [],
        missing_hint="Run 07_grounds Classify all + Save first.",
    )
    assert rows == []
    assert n == 0
    assert "07_grounds" in md


def test_is_labelled_empty_and_inner_speaker_split():
    assert is_labelled([]) is False
    assert is_labelled(["", "  "]) is False
    paragraphs = [
        "Speaker 2: first Speaker 3: second",
        "and then more from speaker 3",
        "Speaker 1: closing",
    ]
    turns = build_turns(paragraphs, doc_id="workshops/a.docx")
    speakers = [t["speaker"] for t in turns]
    assert "s2" in speakers
    assert "s3" in speakers
    assert turns[-1]["facilitator"] is True


def test_quote_ellipsis_and_unplaced_points():
    turns = build_turns(
        ["Speaker 2: I saw this last year at work"],
        doc_id="workshops/a.docx",
    )
    for turn in turns:
        turn["round"] = "spring_2026"
    points = [
        {
            "doc_id": "workshops/a.docx",
            "quote": "I saw this … at work",
            "basis": "personal_experience",
            "format": "workshop",
            "round": "spring_2026",
            "unit_id": "workshops/a.docx::c0003",
        },
        {
            "doc_id": "workshops/a.docx",
            "quote": "this quote is not in the turn",
            "basis": "principle",
            "format": "workshop",
            "round": "spring_2026",
            "unit_id": "workshops/a.docx::c0004",
        },
    ]
    placed = place_points(turns, points)
    assert placed[0]["turn_i"] is not None
    assert placed[1]["turn_i"] is None
    rows, md, n = run_stories_follow_stories(
        turns, points, n_shuffles=8, seed=0, lookbacks="1,2"
    )
    assert n == 1
    assert rows
    assert "this quote is not" not in md


def test_turns_for_round_wrong_round():
    turns = [{"doc_id": "x", "round": "autumn_2025", "turn_i": 0}]
    got, msg = turns_for_round(turns, "spring_2026")
    assert got == []
    assert "spring_2026" in msg


def test_rebuild_no_workshop_docs_and_zero_examples():
    turns, md, n = run_rebuild_speaker_turns(
        documents=[{"filename": "chatbot/x.docx", "format": "chatbot"}],
        paragraphs_by_filename={},
    )
    assert n == 0
    assert turns == []
    assert "No workshop" in md or "workshop" in md.lower()

    turns, md, n = run_rebuild_speaker_turns(
        documents=[
            {"filename": "workshops/a.docx", "format": "workshop", "round": "spring_2026"}
        ],
        paragraphs_by_filename={"workshops/a.docx": ["Speaker 2: hello there"]},
        example_limit=0,
    )
    assert n == 1
    assert "| — |" in md or "—" in md


def test_stories_topic_gap_and_cross_unit():
    turns = build_turns(
        [
            "Speaker 2: I saw this last year",
            "Speaker 3: in principle this should work",
            "Speaker 2: I saw this last year again",
        ],
        doc_id="workshops/a.docx",
        treat_speaker_1_as_facilitator=False,
    )
    for turn in turns:
        turn["round"] = "spring_2026"
    points = [
        {
            "doc_id": "workshops/a.docx",
            "quote": "I saw this last year",
            "basis": "personal_experience",
            "format": "workshop",
            "round": "spring_2026",
            "unit_id": "workshops/a.docx::c0003",
            "topic": "T0",
        },
        {
            "doc_id": "workshops/a.docx",
            "quote": "in principle this should work",
            "basis": "principle",
            "format": "workshop",
            "round": "spring_2026",
            "unit_id": "workshops/a.docx::c0004",
            "topic": "T1",
        },
        {
            "doc_id": "workshops/a.docx",
            "quote": "I saw this last year again",
            "basis": "personal_experience",
            "format": "workshop",
            "round": "spring_2026",
            "unit_id": "workshops/a.docx::c0005",
            "topic": "T0",
        },
    ]
    rows, md, n = run_stories_follow_stories(
        turns,
        points,
        n_shuffles=8,
        seed=0,
        lookbacks=[1],
        cross_unit_only=True,
    )
    assert n == 3
    assert rows
    assert "within-topic" in md or "topic" in md.lower()
    rows2, md2, n2 = run_stories_follow_stories(
        turns, [], n_shuffles="8", seed=0, lookbacks=[1]
    )
    assert n2 == 0
    assert rows2 == []
