"""YAML-callable numeric primitives for scoring arithmetic.

Interim assessment compute in referia pending vongole (lynguine CIP-0007).
Do not promote these into lynguine's access registry.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _as_array(x: Any) -> np.ndarray:
    """Convert scalars/lists/Series to an ndarray without copying unnecessarily."""
    if isinstance(x, np.ndarray):
        return x
    return np.asarray(x)


def _maybe_scalar(result: Any) -> Any:
    """Return a Python scalar for 0-d arrays and numpy scalar types."""
    if isinstance(result, np.generic):
        return result.item()
    if isinstance(result, np.ndarray) and result.ndim == 0:
        return result.item()
    return result


def add(a: Any, b: Any) -> Any:
    """Element-wise or scalar addition (``a + b``).

    Interim assessment compute pending vongole.
    """
    return _maybe_scalar(_as_array(a) + _as_array(b))


def subtract(a: Any, b: Any) -> Any:
    """Element-wise or scalar subtraction (``a - b``).

    Interim assessment compute pending vongole.
    """
    return _maybe_scalar(_as_array(a) - _as_array(b))


def multiply(a: Any, b: Any) -> Any:
    """Element-wise or scalar multiplication (``a * b``).

    Interim assessment compute pending vongole.
    """
    return _maybe_scalar(_as_array(a) * _as_array(b))


def gte(value: Any, threshold: Any) -> Any:
    """Return whether ``value >= threshold`` (scalar or element-wise).

    Interim assessment compute pending vongole. Suitable for pass/fail fields.
    """
    result = _as_array(value) >= _as_array(threshold)
    return _maybe_scalar(result)


def lte(value: Any, threshold: Any) -> Any:
    """Return whether ``value <= threshold`` (scalar or element-wise).

    Interim assessment compute pending vongole. Suitable for pass/fail fields.
    """
    result = _as_array(value) <= _as_array(threshold)
    return _maybe_scalar(result)


def matmul(a: Any, b: Any) -> Any:
    """Matrix product (``a @ b``). Accepts lists or ndarrays.

    Interim assessment compute pending vongole. Useful for criteria×weights.
    """
    return _maybe_scalar(_as_array(a) @ _as_array(b))


def dot(a: Any, b: Any) -> Any:
    """Dot product of two 1-d arrays (or last axes for higher ranks).

    Interim assessment compute pending vongole.
    """
    return _maybe_scalar(np.dot(_as_array(a), _as_array(b)))
