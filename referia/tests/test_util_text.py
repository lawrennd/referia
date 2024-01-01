import pytest
from referia.util.text import (
    split_into_sentences, render_liquid, comment_list, word_count,
    paragraph_split, sentence_split, list_lengths, named_entities,
    text_summarizer, pdf_extract_comments
)
from unittest.mock import patch, mock_open

# Mocking external dependencies
@pytest.fixture(autouse=True)
def mock_external_dependencies(mocker):
    mocker.patch("referia.util.text.nlp", autospec=True)
    mocker.patch("referia.util.text.WordCloud", autospec=True)
    mocker.patch("referia.util.text.nltk.RegexpTokenizer", autospec=True)
    mocker.patch("referia.util.text.sent_tokenize", autospec=True)
    mocker.patch("referia.util.text.os.path.exists", return_value=True)
    mocker.patch("referia.util.text.open", mock_open(read_data="dummy data"), create=True)

# Tests for each function
def test_split_into_sentences():
    text = "This is a sentence. This is another one."
    sentences = split_into_sentences(text)
    assert len(sentences) == 2

def test_render_liquid():
    # Assuming render_liquid function is calling data.liquid_to_value internally
    # Mock data object and its liquid_to_value method
    data_mock = patch("referia.util.text.data")
    with data_mock as mock_data:
        mock_data.liquid_to_value.return_value = "rendered template"
        result = render_liquid(data_mock, "template")
        assert result == "rendered template"

def test_comment_list():
    text = "[comment]{.comment-start id=\"1\" author=\"author\" date=\"date\"}text[]{.comment-end id=\"1\"}"
    comments = comment_list(text)
    assert len(comments) == 7

def test_word_count():
    text = "This is a test."
    assert word_count(text) == 4

def test_paragraph_split():
    text = "Paragraph one\nParagraph two"
    paragraphs = paragraph_split(text, "\n")
    assert len(paragraphs) == 2

def test_sentence_split():
    text = "This is a sentence. This is another one."
    sentences = sentence_split(text)
    assert len(sentences) == 2

def test_list_lengths():
    entries = ["entry1", "entry2"]
    lengths = list_lengths(entries)
    assert lengths == [6, 6]

def test_named_entities():
    text = "John Doe went to New York."
    entities = named_entities(text, "PERSON")
    assert "John Doe" in entities

def test_text_summarizer():
    text = "This is a long text that needs summarization."
    summary = text_summarizer(text, 0.5)
    assert isinstance(summary, str)

def test_pdf_extract_comments():
    comments = pdf_extract_comments("filename.pdf")
    assert isinstance(comments, str)

