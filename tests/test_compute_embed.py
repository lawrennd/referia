"""CIP-0015: llm_embed with a stub client."""

import numpy as np
import pytest

from referia.assess.compute import Compute
from referia.assess.compute.embed import (
    _as_phrase_items,
    _coerce_pca_dim,
    _is_missing_scalar,
    _phrase_text,
    llm_embed,
    llm_embed_extraction_phrases,
    l2_normalize_vector,
)
from referia.exceptions import ComputeError


class _StubEmbed:
    def embed(self, texts, model="text-embedding-3-large"):
        out = []
        for i, _ in enumerate(texts):
            vec = np.zeros(4)
            vec[i % 4] = 3.0
            vec[0] += 1.0
            out.append(vec.tolist())
        return out


def test_l2_normalize_unit_length():
    unit = l2_normalize_vector([3.0, 4.0])
    assert abs(np.linalg.norm(unit) - 1.0) < 1e-9


def test_llm_embed_writes_unit_vector():
    vec = llm_embed("privacy risk from scoring", client=_StubEmbed())
    assert isinstance(vec, list)
    assert abs(np.linalg.norm(vec) - 1.0) < 1e-9
    assert all(isinstance(x, float) for x in vec)


def test_llm_embed_empty_phrase():
    assert llm_embed("  ", client=_StubEmbed()) == []


def test_llm_embed_batch_pca():
    phrases = [
        "first phrase about scoring",
        "second phrase about privacy",
        "third phrase about access",
        "fourth phrase about records",
    ]
    vecs = llm_embed(phrases, pca_dim=2, client=_StubEmbed())
    assert len(vecs) == 4
    assert len(vecs[0]) == 2
    for row in vecs:
        assert abs(np.linalg.norm(row) - 1.0) < 1e-6


def test_llm_embed_registered():
    names = {e["name"] for e in Compute({"input": {}})._compute_functions_list()}
    assert "llm_embed" in names
    assert "llm_embed_extraction_phrases" in names


def test_llm_embed_extraction_phrases_writes_embedding_on_dicts():
    phrases = [
        {"phrase": "privacy risk from scoring", "kind": "concern"},
        {"phrase": "faster access to records", "kind": "benefit"},
    ]
    out = llm_embed_extraction_phrases(phrases, client=_StubEmbed())
    assert len(out) == 2
    assert out[0]["kind"] == "concern"
    assert out[0]["phrase"] == "privacy risk from scoring"
    assert isinstance(out[0]["embedding"], list)
    assert abs(np.linalg.norm(out[0]["embedding"]) - 1.0) < 1e-9
    assert isinstance(out[1]["embedding"], list)


def test_llm_embed_extraction_phrases_empty_is_noop():
    assert llm_embed_extraction_phrases([], client=_StubEmbed()) == []
    assert llm_embed_extraction_phrases(None, client=_StubEmbed()) == []
    assert llm_embed_extraction_phrases(float("nan"), client=_StubEmbed()) == []
    assert llm_embed_extraction_phrases(np.nan, client=_StubEmbed()) == []
    assert llm_embed_extraction_phrases("not-a-list", client=_StubEmbed()) == []


def test_embed_helper_missing_and_phrase_text():
    assert _is_missing_scalar(None) is True
    assert _is_missing_scalar("") is True
    assert _is_missing_scalar(np.nan) is True
    assert _is_missing_scalar(0) is False
    assert _is_missing_scalar(b"x") is False
    assert _is_missing_scalar(np.float64(1.0)) is False
    assert _phrase_text({"phrase": " a "}) == "a"
    assert _phrase_text({"text": " b "}) == "b"
    assert _phrase_text({"kind": "empty"}) == ""
    assert _phrase_text(None) == ""
    assert _phrase_text(12) == "12"
    assert _as_phrase_items(0) == []
    assert _as_phrase_items(({"phrase": "a"},)) == [{"phrase": "a"}]
    assert _coerce_pca_dim("") is None
    assert _coerce_pca_dim("null") is None
    assert _coerce_pca_dim("3") == 3
    assert _coerce_pca_dim(object()) is None


def test_llm_embed_extraction_phrases_mixed_blank_and_text():
    out = llm_embed_extraction_phrases(
        [
            {"phrase": "privacy risk from scoring"},
            {"kind": "empty"},
            None,
            "faster access to records",
        ],
        client=_StubEmbed(),
        pca_dim="",
    )
    assert "embedding" in out[0]
    assert out[1] == {"kind": "empty"}
    assert "embedding" not in out[1]
    assert out[2] == {"phrase": None}
    assert "embedding" in out[3]
    assert abs(np.linalg.norm(out[3]["embedding"]) - 1.0) < 1e-9


def test_llm_embed_extraction_phrases_skips_blank_and_wraps_scalar():
    class _Scalar:
        def embed(self, texts, model="text-embedding-3-large"):
            return [3.0, 4.0]

    blank = llm_embed_extraction_phrases(
        [{"phrase": "  "}, ""],
        client=_StubEmbed(),
    )
    assert blank == [{"phrase": "  "}, {"phrase": ""}]
    wrapped = llm_embed_extraction_phrases(
        {"text": "privacy risk from scoring"},
        client=_Scalar(),
        pca_dim="null",
    )
    assert isinstance(wrapped[0]["embedding"], list)
    skipped = llm_embed_extraction_phrases(
        [{"phrase": "privacy risk from scoring"}],
        client=_StubEmbed(),
        pca_dim="not-a-dim",
    )
    assert isinstance(skipped[0]["embedding"], list)


def test_l2_normalize_empty_and_zero():
    assert l2_normalize_vector([]) == []
    zeros = l2_normalize_vector([0.0, 0.0])
    assert zeros == [0.0, 0.0]


def test_llm_embed_none_and_sequence():
    assert llm_embed(None, client=_StubEmbed()) == []
    vecs = llm_embed(["one", "  ", "two"], client=_StubEmbed())
    assert len(vecs) == 2
    assert all(abs(np.linalg.norm(row) - 1.0) < 1e-9 for row in vecs)


def test_llm_embed_pca_skipped_when_dim_too_large():
    vecs = llm_embed(
        ["a", "b", "c", "d"],
        pca_dim=8,
        client=_StubEmbed(),
    )
    assert len(vecs) == 4
    assert len(vecs[0]) == 4


def test_llm_embed_flat_vector_and_missing_embed():
    class _Flat:
        def embed(self, texts, model="text-embedding-3-large"):
            return [3.0, 4.0]

    unit = llm_embed("hello", client=_Flat())
    assert abs(np.linalg.norm(unit) - 1.0) < 1e-9
    with pytest.raises(ComputeError, match="embed"):
        llm_embed("hello", client=object())


def test_llm_embed_uses_manager(monkeypatch):
    class _Mgr:
        def embed(self, texts, model="text-embedding-3-large"):
            return [[0.0, 4.0]]

    monkeypatch.setattr("referia.util.llm.get_llm_manager", lambda: _Mgr())
    unit = llm_embed("hello")
    assert abs(unit[1] - 1.0) < 1e-9
