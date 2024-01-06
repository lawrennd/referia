import pytest
from referia.util.liquid import url_escape, markdownify, relative_url, absolute_url, to_i

def test_url_escape():
    assert url_escape("https://www.example.com/test?param=value") == "https%3A//www.example.com/test%3Fparam%3Dvalue"
    assert url_escape(" ") == "%20"
    with pytest.raises(ValueError):
        url_escape("\ud800")  # Unencodable character

def test_markdownify(mocker):
    # Mock the markdown2html function
    mocker.patch('referia.util.misc.markdown2html', return_value="<h1>Test</h1>")
    assert markdownify("# Test") == "<h1>Test</h1>"
    # Test for error handling
    mocker.patch('referia.util.misc.markdown2html', side_effect=Exception('mock error'))
    with pytest.raises(ValueError) as exc_info:
        markdownify("# Test")
    assert str(exc_info.value) == "Error converting markdown to HTML: mock error"
def test_relative_url():
    assert relative_url("test/notebook.ipynb") == "/notebooks/test/notebook.ipynb"
    assert relative_url("/test/notebook.ipynb") == "/notebooks/test/notebook.ipynb"

def test_absolute_url():
    assert absolute_url("test/notebook.ipynb") == "http://localhost:8888/notebooks/test/notebook.ipynb"
    assert absolute_url("/test/notebook.ipynb") == "http://localhost:8888/notebooks/test/notebook.ipynb"

def test_to_i():
    assert to_i("123") == 123
    assert to_i("123.45") == 123
    assert to_i("") == 0
    with pytest.raises(ValueError):
        to_i("abc")

