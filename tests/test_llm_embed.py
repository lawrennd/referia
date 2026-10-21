"""CIP-0015: LLMManager.embed without requiring the llm extra at import."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from referia.util.llm import LLMConfigError, LLMManager


def _manager(*, cache=None, config=None):
    mgr = LLMManager.__new__(LLMManager)
    mgr.config = config or {}
    mgr.cache = cache
    return mgr


def test_embed_empty_texts():
    mgr = _manager()
    assert mgr.embed([]) == []


def test_embed_cache_hit():
    cache = MagicMock()
    cache.get.return_value = [[0.1, 0.2]]
    mgr = _manager(cache=cache)
    assert mgr.embed("hello") == [[0.1, 0.2]]
    cache.get.assert_called()


def test_embed_openai_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", None)
    mgr = _manager(config={"api_keys": {"openai": "k"}})
    with pytest.raises(LLMConfigError, match="openai is not installed"):
        mgr.embed("hello", use_cache=False)


def test_embed_missing_api_key(monkeypatch):
    fake = types.ModuleType("openai")

    class OpenAI:
        def __init__(self, api_key=None):
            raise AssertionError("should not construct")

    fake.OpenAI = OpenAI
    monkeypatch.setitem(sys.modules, "openai", fake)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mgr = _manager(config={})
    with pytest.raises(LLMConfigError, match="API key"):
        mgr.embed("hello", use_cache=False)


def test_embed_api_orders_and_caches(monkeypatch):
    class _Item:
        def __init__(self, index, embedding):
            self.index = index
            self.embedding = embedding

    class _Resp:
        data = [_Item(1, [0.0, 1.0]), _Item(0, [1.0, 0.0])]

    class _Embeddings:
        def create(self, model, input):
            self.model = model
            self.input = input
            return _Resp()

    class _OpenAI:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.embeddings = _Embeddings()

    fake = types.ModuleType("openai")
    fake.OpenAI = _OpenAI
    monkeypatch.setitem(sys.modules, "openai", fake)
    cache = MagicMock()
    cache.get.return_value = None
    mgr = _manager(
        cache=cache,
        config={"api_keys": {"openai": "sk-test"}, "cache_ttl": 9},
    )
    out = mgr.embed(["a", "b"])
    assert out == [[1.0, 0.0], [0.0, 1.0]]
    cache.set.assert_called()
    assert cache.set.call_args.kwargs["expire"] == 9


def test_embed_uses_env_api_key_without_cache(monkeypatch):
    class _Item:
        def __init__(self, index, embedding):
            self.index = index
            self.embedding = embedding

    class _Resp:
        data = [_Item(0, [0.0, 2.0])]

    class _OpenAI:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.embeddings = types.SimpleNamespace(
                create=lambda model, input: _Resp()
            )

    fake = types.ModuleType("openai")
    fake.OpenAI = _OpenAI
    monkeypatch.setitem(sys.modules, "openai", fake)
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")
    mgr = _manager(cache=None, config={})
    out = mgr.embed("hello", use_cache=True)
    assert out == [[0.0, 2.0]]
