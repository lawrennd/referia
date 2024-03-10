import pytest
from datetime import datetime
import pandas as pd
from referia.util.misc import (
    identity, filename_to_binary, yyyymmddToDatetime, datetimeToYyyymmdd,
    add_one_to_max, renderable, tallyable, notempty,
    return_longest, return_shortest
)

def test_identity():
    assert identity(123) == 123
    assert identity("test") == "test"
    assert identity([1, 2, 3]) == [1, 2, 3]

def test_filename_to_binary(mocker):
    mocker.patch('builtins.open', mocker.mock_open(read_data=b'file content'))
    assert filename_to_binary('dummy.txt') == b'file content'

def test_yyyymmddToDatetime():
    assert yyyymmddToDatetime("2023-01-01") == datetime(2023, 1, 1, 0, 0)
    with pytest.raises(ValueError):
        yyyymmddToDatetime("2023-01-01 12:34:56")
    assert yyyymmddToDatetime(pd.Timestamp("2023-01-01")) == datetime(2023, 1, 1, 0, 0)
    with pytest.raises(ValueError):
        yyyymmddToDatetime("not formatted date")
        
def test_renderable():
    assert renderable("display")
    assert not renderable("unknown")

def test_tallyable():
    assert tallyable("tally")
    assert not tallyable("other")

def test_notempty():
    assert notempty("text")
    assert not notempty("")
    assert not notempty(None)

def test_return_longest():
    assert return_longest(["short", "medium", "longest"]) == "longest"

def test_return_shortest():
    assert return_shortest(["short", "medium", "longest"]) == "short"
