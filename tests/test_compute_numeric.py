"""Unit tests for YAML numeric compute primitives."""

import numpy as np
import pandas as pd
import pytest

from referia.assess.compute import Compute
from referia.assess.compute.numeric import (
    add,
    subtract,
    multiply,
    gte,
    lte,
    matmul,
    dot,
)
from lynguine.assess.data import CustomDataFrame


NUMERIC_NAMES = ("add", "subtract", "multiply", "gte", "lte", "matmul", "dot")


def test_scalar_arithmetic():
    assert add(2, 3) == 5
    assert subtract(10, 4) == 6
    assert multiply(3, 5) == 15


def test_list_and_series_elementwise():
    assert np.allclose(add([1, 2], [3, 4]), [4, 6])
    assert np.allclose(multiply([2, 3], 4), [8, 12])
    s = pd.Series([1.0, 2.0])
    out = subtract(s, 0.5)
    assert np.allclose(out, [0.5, 1.5])


def test_threshold_compare():
    assert gte(10, 10) is True
    assert gte(9, 10) is False
    assert lte(5, 5) is True
    assert lte(6, 5) is False
    flags = gte([1, 5, 10], 5)
    assert list(np.asarray(flags)) == [False, True, True]


def test_matmul_and_dot():
    criteria = [[1.0, 2.0], [3.0, 4.0]]
    weights = [0.5, 0.5]
    assert np.allclose(matmul(criteria, weights), [1.5, 3.5])
    assert dot([1, 2, 3], [4, 5, 6]) == 32


def test_registry_lists_numeric_primitives():
    compute = Compute({"input": {}})
    names = {entry["name"] for entry in compute._compute_functions_list()}
    for name in NUMERIC_NAMES:
        assert name in names
    for entry in compute._compute_functions_list():
        if entry["name"] in NUMERIC_NAMES:
            assert "vongole" in (entry.get("docstr") or "").lower()


def test_gcf_multiply_and_gte_from_row_args():
    compute = Compute({"input": {}})
    df = CustomDataFrame(
        pd.DataFrame({"score": [8, 3], "weight": [2, 4]}, index=["a", "b"])
    )
    df.set_index("a")
    mul = compute.gcf_("multiply", df)
    product = mul(
        df,
        row_args={"a": "score", "b": "weight"},
        default_args={},
    )
    assert product == 16

    cmp_fn = compute.gcf_("gte", df)
    passed = cmp_fn(
        df,
        row_args={"value": "score"},
        args={"threshold": 5},
        default_args={},
    )
    assert passed is True

    df.set_index("b")
    passed_b = cmp_fn(
        df,
        row_args={"value": "score"},
        args={"threshold": 5},
        default_args={},
    )
    assert passed_b is False


def test_gcf_matmul_from_args():
    compute = Compute({"input": {}})
    df = CustomDataFrame(pd.DataFrame({"x": [0]}, index=["row"]))
    df.set_index("row")
    fn = compute.gcf_("matmul", df)
    result = fn(
        df,
        args={"a": [[1, 0], [0, 1]], "b": [2, 3]},
        default_args={},
    )
    assert np.allclose(result, [2, 3])
