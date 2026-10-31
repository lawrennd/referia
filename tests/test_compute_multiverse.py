"""CIP-001E: analysis-choice product on main-run codes (not 1080 LLM jobs)."""

from referia.assess.compute.multiverse import run_analysis_multiverse


def _point(fmt, doc, basis, *, rnd="spring_2026", support=1.0, unit="::c0003"):
    return {
        "format": fmt,
        "doc_id": doc,
        "basis": basis,
        "round": rnd,
        "session_type": "breakout" if fmt == "workshop" else "chatbot",
        "quote_support": support,
        "unit_id": f"{doc}{unit}",
        "extract_text": "Speaker 2: a line",
        "lens": "T0" if fmt == "workshop" else "T1",
    }


def test_analysis_multiverse_workshop_higher_experience():
    points = [
        _point("chatbot", "autumn_2025::1", "principle"),
        _point("chatbot", "autumn_2025::2", "principle"),
        _point("workshop", "workshops/a.docx", "personal_experience"),
        _point("workshop", "workshops/b.docx", "others_experience"),
    ]
    summary, md, n = run_analysis_multiverse(
        points, n_jsd_shuffles=8, seed=0
    )
    assert n > 0
    assert summary[0]["pct_positive"] == 100.0
    assert summary[0]["canonical"] > 0
    assert "1080 populate-all" in md
    assert "Own-words" in md
    assert "personal_experience" not in md or "main-run" in md.lower()


def test_analysis_multiverse_waits_on_grounds():
    summary, md, n = run_analysis_multiverse(
        [], missing_hint="Run 07_grounds Classify all + Save first."
    )
    assert summary == []
    assert n == 0
    assert "07_grounds" in md


def test_analysis_multiverse_requires_basis_and_both_formats():
    summary, md, n = run_analysis_multiverse(
        [{"format": "workshop", "doc_id": "a", "quote_support": 1.0}]
    )
    assert n == 0
    assert "07 basis" in md
    only_ws = [
        _point("workshop", "workshops/a.docx", "personal_experience"),
        _point("workshop", "workshops/b.docx", "principle"),
    ]
    summary, md, n = run_analysis_multiverse(only_ws, n_jsd_shuffles=0)
    assert n == 0
    assert "both formats" in md


def test_analysis_multiverse_exclusions_and_point_weighting():
    points = [
        _point("chatbot", "autumn_2025::1", "principle"),
        _point(
            "workshop",
            "workshops/a.docx",
            "personal_experience",
            unit="::c0001",
        ),
        _point(
            "workshop",
            "workshops/carousel.docx",
            "personal_experience",
        ),
        _point("workshop", "workshops/b.docx", "principle"),
    ]
    points[2]["session_type"] = "carousel"
    points[3]["extract_text"] = "Speaker 1: welcome everyone"
    summary, md, n = run_analysis_multiverse(
        points, n_jsd_shuffles=0, seed="0"
    )
    assert n > 0
    assert summary[0]["configurations"] == n
    summary2, md2, n2 = run_analysis_multiverse(
        points, n_jsd_shuffles="8", seed=0
    )
    assert n2 == n
    assert "JSD" in md2 or "1080" in md2
