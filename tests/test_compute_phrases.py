"""CIP-0015: llm_extract_phrases parse rules and stub client."""

import pytest

from referia.assess.compute import Compute
from referia.assess.compute.phrases import (
    llm_extract_phrases,
    parse_extraction_payload,
    word_count_phrase,
)
from referia.exceptions import ComputeError


PROMPT = (
    "Extract short phrases of kind {{ kind }}. If none, {{ sentinel }}.\n"
    "Unit:\n<<TEXT>>"
)


class _StubComplete:
    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def call(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return self.replies.pop(0)


def test_word_count_phrase():
    assert word_count_phrase("one two three") == 3


def test_parse_drops_sentinel_and_short_phrases():
    payload = "NO_CONCERN\ntoo few\nprivacy risk from scoring\n"
    out = parse_extraction_payload(
        payload,
        kind="concern",
        sentinel="NO_CONCERN",
        min_words=3,
        max_words=10,
        max_items=8,
        chunk_id="c1",
        doc_id="docA",
    )
    assert len(out) == 1
    assert out[0]["phrase"] == "privacy risk from scoring"
    assert out[0]["kind"] == "concern"
    assert out[0]["chunk_id"] == "c1"
    assert out[0]["doc_id"] == "docA"
    assert out[0]["phrase_id"] == "c1:concern:0"


def test_parse_phrase_quote_and_json():
    line = parse_extraction_payload(
        "data privacy worries || we worry about records",
        kind="concern",
        sentinel="NO_CONCERN",
        chunk_id="c1",
        doc_id="d",
    )
    assert line[0]["quote"] == "we worry about records"
    js = parse_extraction_payload(
        '{"phrases": [{"phrase": "unequal access to tools", "quote": "q"}]}',
        kind="concern",
        sentinel="NO_CONCERN",
        chunk_id="c1",
        doc_id="d",
    )
    assert js[0]["phrase"] == "unequal access to tools"
    assert js[0]["quote"] == "q"


def test_parse_caps_max_items():
    lines = "\n".join(f"this is phrase number {i} here" for i in range(12))
    out = parse_extraction_payload(
        lines, kind="benefit", sentinel="NO_BENEFIT", max_items=3
    )
    assert len(out) == 3


def test_llm_extract_phrases_stub_client():
    client = _StubComplete(
        [
            "opaque scoring of minority views\nNO_CONCERN",
            "NO_BENEFIT",
            "clearer public records of decisions",
        ]
    )
    payload, phrases = llm_extract_phrases(
        "People worry that opaque scoring will silence minority views.",
        prompt_template=PROMPT,
        kinds=["concern", "benefit", "condition"],
        chunk_id="u1",
        doc_id="Doc",
        client=client,
        sentinel_concern="NO_CONCERN",
        sentinel_benefit="NO_BENEFIT",
        sentinel_condition="NO_CONDITION",
    )
    assert set(payload) == {"concern", "benefit", "condition"}
    kinds = {p["kind"] for p in phrases}
    assert "concern" in kinds
    assert "benefit" not in kinds
    assert any(p["kind"] == "condition" for p in phrases)
    assert "<<TEXT>>" not in client.prompts[0]
    assert "concern" in client.prompts[0]


def test_as_kinds_splits_comma_string():
    from referia.assess.compute.phrases import _as_kinds

    assert _as_kinds("concern, benefit, condition") == [
        "concern",
        "benefit",
        "condition",
    ]
    assert _as_kinds("concern; benefit") == ["concern", "benefit"]
    assert _as_kinds("benefit") == ["benefit"]
    assert _as_kinds(["concern", "benefit", " "]) == ["concern", "benefit"]
    assert _as_kinds("  ,  ") == [","]


def test_llm_extract_phrases_comma_kinds_runs_each_kind():
    client = _StubComplete(["opaque scoring of views", "NO_BENEFIT"])
    payload, phrases = llm_extract_phrases(
        "People worry that opaque scoring will silence minority views.",
        prompt_template=PROMPT,
        kinds="concern, benefit",
        chunk_id="u1",
        doc_id="Doc",
        client=client,
        sentinel_concern="NO_CONCERN",
        sentinel_benefit="NO_BENEFIT",
    )
    assert set(payload) == {"concern", "benefit"}
    assert any(p["kind"] == "concern" for p in phrases)


def test_llm_extract_phrases_requires_prompt():
    try:
        llm_extract_phrases("text", prompt_template="", kinds=["concern"])
    except ValueError as exc:
        assert "prompt_template" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_llm_extract_phrases_registered():
    names = {e["name"] for e in Compute({"input": {}})._compute_functions_list()}
    assert "llm_extract_phrases" in names
    assert "llm_extract" in names


def test_parse_json_object_list_and_invalid_json():
    from_items = parse_extraction_payload(
        {"items": ["this is a valid phrase", 12, {"text": "another valid phrase here"}]},
        kind="benefit",
        sentinel="NO_BENEFIT",
        min_words=3,
        max_words=10,
        chunk_id="c1",
        doc_id="d",
    )
    assert [row["phrase"] for row in from_items] == [
        "this is a valid phrase",
        "another valid phrase here",
    ]
    fallback = parse_extraction_payload(
        "{not-json\nstill a valid three word line",
        kind="concern",
        sentinel="NO_CONCERN",
        min_words=3,
        max_words=10,
    )
    assert fallback[0]["phrase"] == "still a valid three word line"
    assert parse_extraction_payload(3.14, kind="concern", sentinel="NO") == []
    empty_quote = parse_extraction_payload(
        "|| only a quote",
        kind="concern",
        sentinel="NO",
        min_words=1,
        max_words=10,
    )
    assert empty_quote == []
    no_chunk = parse_extraction_payload(
        "this is a valid phrase",
        kind="concern",
        sentinel="NO",
        min_words=3,
        max_words=10,
    )
    assert no_chunk[0]["phrase_id"] == "concern:0"
    assert parse_extraction_payload(
        {"other": "ignored"},
        kind="concern",
        sentinel="NO",
        min_words=1,
        max_words=10,
    ) == []
    assert parse_extraction_payload(
        {"phrases": "not-a-list"},
        kind="concern",
        sentinel="NO",
        min_words=1,
        max_words=10,
    ) == []
    listed = parse_extraction_payload(
        ["this is a valid phrase"],
        kind="concern",
        sentinel="NO",
        min_words=3,
        max_words=10,
    )
    assert listed[0]["phrase"] == "this is a valid phrase"


def test_llm_extract_empty_text_and_kinds_string():
    assert llm_extract_phrases("  ", prompt_template="p", kinds=["concern"]) == ({}, [])
    with pytest.raises(ValueError, match="kinds"):
        llm_extract_phrases("hello there friends", prompt_template="p", kinds=None)


def test_llm_extract_sentinels_and_none_reply():
    class _NoneReply:
        def call(self, **kwargs):
            return None

    payload, phrases = llm_extract_phrases(
        "hello there friends",
        prompt_template="kind={{kind}} sentinel={{sentinel}} <<TEXT>>",
        kinds="concern",
        client=_NoneReply(),
        sentinels={"concern": "NONE"},
        min_words=1,
        max_words=10,
    )
    assert payload == {"concern": ""}
    assert phrases == []


def test_llm_extract_client_must_have_call():
    with pytest.raises(ComputeError, match="call"):
        llm_extract_phrases(
            "hello there friends",
            prompt_template="<<TEXT>>",
            kinds=["concern"],
            client=object(),
        )


def test_llm_extract_uses_injected_manager(monkeypatch):
    class _Mgr:
        def call(self, **kwargs):
            return "this is a valid phrase"

    monkeypatch.setattr(
        "referia.util.llm.get_llm_manager", lambda: _Mgr()
    )
    payload, phrases = llm_extract_phrases(
        "hello there friends",
        prompt_template="s={{ sentinel }} <<TEXT>>",
        kinds=["concern"],
        sentinel="NONE",
        min_words=3,
        max_words=10,
    )
    assert "concern" in payload
    assert phrases[0]["phrase"] == "this is a valid phrase"
