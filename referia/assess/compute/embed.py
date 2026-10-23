"""Stateless embedding compute for dialogue phrase rows (CIP-0015)."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from ...exceptions import ComputeError

__all__ = ["l2_normalize_vector", "llm_embed", "llm_embed_extraction_phrases"]


def l2_normalize_vector(vector: Sequence[float], eps: float = 1e-12) -> list[float]:
    """Return an L2 unit vector as a JSON-serialisable list."""
    arr = np.asarray(vector, dtype=float).ravel()
    if arr.size == 0:
        return []
    norm = float(np.linalg.norm(arr))
    if norm < eps:
        return arr.tolist()
    return (arr / norm).tolist()


def _as_texts(phrase: Any) -> list[str]:
    if phrase is None:
        return []
    if isinstance(phrase, str):
        return [phrase] if phrase.strip() else []
    return [str(p) for p in phrase if str(p).strip()]


def _pca_reduce(X: np.ndarray, pca_dim: int) -> np.ndarray:
    n, d = X.shape
    dim = min(int(pca_dim), n, d)
    if dim < 1 or dim >= d:
        return X
    from sklearn.decomposition import PCA

    return PCA(n_components=dim, random_state=0).fit_transform(X)


def _embed_client(client: Any, texts: list[str], model: str) -> list[list[float]]:
    if client is None:
        from ...util.llm import get_llm_manager

        client = get_llm_manager()
    if hasattr(client, "embed"):
        return client.embed(texts, model=model)
    raise ComputeError(
        "llm_embed client has no embed(). Inject LLMManager or a stub."
    )


def llm_embed(
    phrase: Any,
    *,
    model: str = "text-embedding-3-large",
    pca_dim: int | None = None,
    client: Any = None,
    **_kwargs,
) -> list[float] | list[list[float]]:
    """Embed phrase text; write an L2-normalised list of floats.

    ``pca_dim`` applies only when more than one text is passed in one call
    (row-local single phrases skip PCA). Client is injected.
    """
    texts = _as_texts(phrase)
    if not texts:
        return []

    vectors = _embed_client(client, texts, model)
    X = np.asarray(vectors, dtype=float)
    if X.ndim == 1:
        X = X.reshape(1, -1)
    dim = _coerce_pca_dim(pca_dim)
    if dim is not None and X.shape[0] > 1:
        X = _pca_reduce(X, dim)
    unit = [l2_normalize_vector(row) for row in X]
    if isinstance(phrase, str) or len(unit) == 1:
        return unit[0]
    return unit


def _phrase_text(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("phrase") or item.get("text") or "").strip()
    return str(item).strip() if item is not None else ""


def _is_missing_scalar(value: Any) -> bool:
    """True for None, '', pandas/NumPy NA, or NaN (empty cache cells)."""
    if value is None or value == "":
        return True
    if isinstance(value, (list, tuple, dict, str, bytes)):
        return False
    if isinstance(value, (float, np.floating)):
        return bool(np.isnan(value))
    return False


def _as_phrase_items(extraction_phrases: Any) -> list:
    if _is_missing_scalar(extraction_phrases):
        return []
    if isinstance(extraction_phrases, dict):
        return [extraction_phrases]
    if isinstance(extraction_phrases, (list, tuple)):
        return list(extraction_phrases)
    return []


def _coerce_pca_dim(pca_dim: Any) -> int | None:
    if _is_missing_scalar(pca_dim) or pca_dim in ("null",):
        return None
    try:
        return int(pca_dim)
    except (TypeError, ValueError):
        return None


def llm_embed_extraction_phrases(
    extraction_phrases: Any,
    *,
    model: str = "text-embedding-3-large",
    pca_dim: int | None = None,
    client: Any = None,
    **_kwargs,
) -> list[dict]:
    """Embed each phrase dict on a chunk row; write ``embedding`` on the dict.

    Chunk-grain listing (``02_embed``) holds phrases as a list-in-one-field.
    Explode copies ``embedding`` onto tall rows for pack. YAML cache/output
    omit those vectors on write; ``records.parquet`` is the vector store.
    Empty input is a no-op so **Embed all** can run before every chunk is
    extracted.
    """
    items = _as_phrase_items(extraction_phrases)
    if not items:
        return []
    texts = [_phrase_text(item) for item in items]
    nonempty = [t for t in texts if t]
    if not nonempty:
        return [dict(item) if isinstance(item, dict) else {"phrase": item} for item in items]

    vectors = llm_embed(
        nonempty, model=model, pca_dim=_coerce_pca_dim(pca_dim), client=client
    )
    if vectors and isinstance(vectors[0], (int, float)):
        vectors = [vectors]
    vec_iter = iter(vectors)
    out: list[dict] = []
    for item, text in zip(items, texts):
        row = dict(item) if isinstance(item, dict) else {"phrase": item}
        if text:
            row["embedding"] = next(vec_iter)
        out.append(row)
    return out
