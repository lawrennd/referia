"""CIP-001E: llm_classify_grounds parse rules and stub client."""

from referia.assess.compute.grounds import (
    llm_classify_grounds,
    normalise_basis,
)


PROMPT = (
    "For EACH numbered point, say what it rests on.\n"
    "TEXT\n<<UNIT>>\n\nPOINTS\n<<POINTS>>"
)


class _StubComplete:
    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def call(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return self.reply


def test_normalise_basis_aliases():
    assert normalise_basis("personal") == "personal_experience"
    assert normalise_basis("Values") == "principle"
    assert normalise_basis("nope") == "unclear"


def test_as_points_accepts_mapping_rows():
    import numpy as np
    from referia.assess.compute.grounds import _as_points

    class _Row(dict):
        pass

    rows = _as_points(np.array([_Row(phrase_id="p1", phrase="fairness")], dtype=object))
    assert rows[0]["phrase_id"] == "p1"
    assert rows[0]["phrase"] == "fairness"


def test_empty_points_noop():
    payload, rows = llm_classify_grounds(
        "hello", [], prompt_template=PROMPT, client=_StubComplete("{}")
    )
    assert payload == ""
    assert rows == []


def test_parse_json_bases_and_phrase_ids():
    client = _StubComplete(
        '{"bases": [{"n": 1, "basis": "principle"}, '
        '{"n": 2, "basis": "personal_experience"}]}'
    )
    payload, rows = llm_classify_grounds(
        "I think fairness matters. When I rang the council it took weeks.",
        [
            {"phrase_id": "p1", "phrase": "fairness matters", "kind": "condition"},
            {
                "phrase_id": "p2",
                "phrase": "slow council response",
                "kind": "concern",
                "quote": "When I rang the council",
            },
        ],
        prompt_template=PROMPT,
        client=client,
    )
    assert "fairness matters" in client.prompts[0]
    assert rows[0]["basis"] == "principle"
    assert rows[0]["phrase_id"] == "p1"
    assert rows[1]["basis"] == "personal_experience"
    assert payload.startswith("{")


def test_missing_point_is_unclear():
    client = _StubComplete('{"bases": [{"n": 1, "basis": "principle"}]}')
    _payload, rows = llm_classify_grounds(
        "text",
        [{"phrase_id": "a"}, {"phrase_id": "b"}],
        prompt_template=PROMPT,
        client=client,
    )
    assert rows[0]["basis"] == "principle"
    assert rows[1]["basis"] == "unclear"


def test_wrapper_does_not_open_phrases_yml():
    from referia.assess.compute import Compute

    compute = Compute.__new__(Compute)

    def boom(*_args, **_kwargs):
        raise AssertionError("must not load phrases.yml")

    compute._load_info_yaml_rows = boom
    payload, rows = compute._llm_classify_grounds(
        "hello",
        points=[],
        unit_id="u1",
        prompt_template=PROMPT,
        client=_StubComplete("{}"),
    )
    assert payload == ""
    assert rows == []

    payload, rows = compute._llm_classify_grounds(
        "hello",
        points=[{"phrase_id": "p1", "phrase": "fairness"}],
        unit_id="u1",
        prompt_template=PROMPT,
        client=_StubComplete('{"bases": [{"n": 1, "basis": "principle"}]}'),
    )
    assert rows[0]["basis"] == "principle"
    assert rows[0]["phrase_id"] == "p1"


def test_context_is_wrapped_not_coded_from():
    client = _StubComplete('{"bases": [{"n": 1, "basis": "principle"}]}')
    llm_classify_grounds(
        "because it should be fair",
        [{"phrase_id": "p1", "phrase": "fairness"}],
        prompt_template=PROMPT,
        client=client,
        context="Have you ever used this?",
    )
    prompt = client.prompts[0]
    assert "context only" in prompt
    assert "Have you ever used this?" in prompt
