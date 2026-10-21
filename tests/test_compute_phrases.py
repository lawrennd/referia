"""CIP-0015: llm_extract_phrases parse rules and stub client."""

from referia.assess.compute import Compute
from referia.assess.compute.phrases import (
    llm_extract_phrases,
    parse_extraction_payload,
    word_count_phrase,
)


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
