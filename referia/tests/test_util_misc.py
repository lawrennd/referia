import pytest
from datetime import datetime
import pandas as pd
from referia.util.misc import (
    identity, filename_to_binary, yyyymmddToDatetime, datetimeToYyyymmdd,
    add_one_to_max, renderable, tallyable, notempty,
    return_longest, return_shortest, document_action_label,
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


def test_document_action_label_prefers_name():
    assert document_action_label({"type": "docx", "name": "Create draft"}) == "Create draft"


def test_document_action_label_from_title_liquid():
    assert document_action_label(
        {"type": "docx", "title": {"liquid": "Draft Thesis Review"}}
    ) == "Create Draft Thesis Review"
    assert document_action_label(
        {"type": "docx", "title": {"liquid": "Conversation: {{title}}"}}
    ) == "Create Conversation"
    assert document_action_label(
        {"type": "email", "subject": {"liquid": "Draft Thesis Review"}},
        summary=True,
    ) == "Create Summary Draft Thesis Review"


def test_document_action_label_falls_back_to_type():
    assert document_action_label({"type": "email"}) == "Create email"
    assert document_action_label({"type": "letter"}, summary=True) == "Create Summary letter"
