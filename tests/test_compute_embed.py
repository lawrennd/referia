"""CIP-0015: llm_embed with a stub client."""

import numpy as np

from referia.assess.compute import Compute
from referia.assess.compute.embed import llm_embed, l2_normalize_vector


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
