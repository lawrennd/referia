"""CIP-001E: document-weighted type/lens mix and JSD."""

import numpy as np

from referia.assess.compute.compare import (
    jsd,
    run_format_share_compare,
    run_question_type_stress,
    run_wordlist_floor,
)


def test_jsd_identical_is_zero():
    p = [0.2, 0.5, 0.3]
    assert jsd(p, p) == 0.0


def test_jsd_max_is_one():
    assert jsd([1, 0], [0, 1]) == 1.0


def test_format_share_compare_two_groups():
    doc_ids = ["c1", "c1", "w1", "w1"]
    groups = ["chatbot", "chatbot", "workshop", "workshop"]
    kinds = ["concern", "benefit", "concern", "condition"]
    cluster_ids = [0, 1, 2, 3]
    codebook_R = np.array(
        [
            [1.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [0.0, 1.0],
        ]
    )
    type_mix, lens_mix, jsd_value, type_md, lens_md, jsd_md, n_docs = (
        run_format_share_compare(
            doc_ids,
            codebook_R,
            groups=groups,
            cluster_ids=cluster_ids,
            kinds=kinds,
            topic_labels={"T0": "A", "T1": "B"},
            n_boot=50,
            seed=0,
            min_mass=1,
        )
    )
    assert jsd_value == 1.0
    assert n_docs == {"chatbot": 1, "workshop": 1}
    assert any(r["value"] == "concern" for r in type_mix)
    assert "Jensen–Shannon" in jsd_md
    assert "A" in lens_md
    assert type_md.startswith("|")


def test_format_share_compare_without_kinds_notes():
    type_mix, _lens, jsd_value, type_md, _lmd, jsd_md, _n = (
        run_format_share_compare(
            ["a", "b"],
            [[1.0, 0.0], [0.0, 1.0]],
            groups=["chatbot", "workshop"],
            n_boot=20,
            seed=1,
        )
    )
    assert type_mix == []
    assert "No phrase kinds" in type_md or "No type mix" in type_md
    assert jsd_value == 1.0
    assert "0.006" in jsd_md


def test_question_type_stress_counts_chatbot_only():
    rows, md, n_bot = run_question_type_stress(
        [
            "Have you ever used this in your work?",
            "What do you think in principle?",
            "Have you ever used this at work?",
        ],
        formats=["chatbot", "workshop", "chatbot"],
    )
    assert n_bot == 2
    exp = next(
        r for r in rows if "experience" in r["bot_question"]
    )
    assert exp["n_questions"] == 2
    assert exp["pct_of_chatbot_units"] == 100.0
    assert "2 chatbot units" in md


def test_wordlist_floor_hits_own_quote():
    rows, md = run_wordlist_floor(
        ["when I rang the council last year", "in principle this is unfair"],
        bases=["personal_experience", "principle"],
        groups=["workshop", "chatbot"],
        doc_ids=["w", "c"],
    )
    wl = rows[0]
    assert wl["n_hit"] == 1
    assert "Word-list floor" in md
    assert any("LLM grounds" in r["measure"] for r in rows)
