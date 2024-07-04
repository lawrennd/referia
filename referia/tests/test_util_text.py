import pytest
import ndlpy
import referia

from referia.util.text import (
    split_into_sentences, render_liquid, comment_list, word_count,
    paragraph_split, sentence_split, list_lengths, named_entities,
    text_summarizer, pdf_extract_comments
)
from unittest.mock import patch, mock_open

# Mocking external dependencies
@pytest.fixture(autouse=True)
def mock_external_dependencies(mocker):
    mocker.patch("referia.util.text.WordCloud", autospec=True)

# Mocking path.exists for pdf_extract_comments
@pytest.fixture
def mock_path_exists(mocker):
    return mocker.patch("referia.util.text.os.path.exists", return_value=True)

# Mocking open for pdf_extract_comments
@pytest.fixture
def mock_text_open(mocker):
    return mocker.patch("referia.util.text.open", mock_open(read_data="dummy data"), create=True)

# Mocking json.load for pdf_extract_comments
@pytest.fixture
def mock_json_load(mocker):
    return mocker.patch("referia.util.text.json.load", return_value=[{"type": "FreeText", "page": 12, "contents": "dummy data"}, {"type": "Highlight", "page": 12, "text" : "Some text", "contents": "A highlight"}])


# Mocking spacy.load for a document summarisation.
#@pytest.fixture
#def mock_spacy_load(mocker):
#    return mocker.patch("referia.util.text.spacy.load", return_value={"token" : ["a", "series", "of", "words", "which", "can", "be", "be", "repeated", ".", "Or", "maybe", "not", "."]})
    
# Tests for each function
def test_split_into_sentences():
    text = "This is a sentence. This is another one."
    sentences = split_into_sentences(text)
    assert len(sentences) == 2

def test_render_liquid():
    # Assuming render_liquid function is calling data.liquid_to_value internally
    # Mock data object and its liquid_to_value method
    values = {"key1" : "value1", "key2" : "value2"}
    template = "{{key1}} {{key2}}"
    interface = referia.config.interface.Interface({}) # Mock interface
    data = referia.assess.data.CustomDataFrame(data=[values], colspecs="data")
    data._augment_column_names(data) # Necessary to map liquid keys to column names
    data.compute = referia.assess.compute.Compute(interface)
    result = render_liquid(data, template)
    assert result == "value1 value2"
    mapping = {"key1" : "key1", "key2" : "key2"}
    result = render_liquid(data, template, kwargs=mapping)
    assert result == "value1 value2"
    

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
    text = "John Doe went to New York. He bought some Nike shoes for 30 dollars. John spoke English when he was buying 15 shoes. This all happened on 3rd December, he thought he was overcharged by 20%"
    entities = named_entities(text, "PERSON")
    assert "John Doe" in entities
    entities = named_entities(text, "GPE")
    assert "New York" in entities
    entities = named_entities(text, "ORG")
    assert "Nike" in entities
    entities = named_entities(text, "MONEY")
    assert "30 dollars" in entities
    entities = named_entities(text, "LANGUAGE")
    assert "English" in entities
    entities = named_entities(text, "CARDINAL")
    assert "15" in entities
    entities = named_entities(text, "DATE")
    assert "3rd December" in entities
    entities = named_entities(text, "PERCENT")
    assert "20%" in entities

def test_text_summarizer():
    text = "Machine learning (ML) is a field of study in artificial intelligence concerned with the development and study of statistical algorithms that can learn from data and generalize to unseen data, and thus perform tasks without explicit instructions. Recently, generative artificial neural networks have been able to surpass many previous approaches in performance. While machine learning algorithms have shown remarkable performances on various tasks, they are susceptible to inheriting and amplifying biases present in their training data. This can manifest in skewed representations or unfair treatment of different demographics, such as those based on race, gender, language, and cultural groups."
    summary = text_summarizer(text, 0.5)
    assert summary == "Machine learning (ML) is a field of study in artificial intelligence concerned with the development and study of statistical algorithms that can learn from data and generalize to unseen data, and thus perform tasks without explicit instructions. While machine learning algorithms have shown remarkable performances on various tasks, they are susceptible to inheriting and amplifying biases present in their training data."

    summary = text_summarizer(text, 0.25)
    assert summary == "Machine learning (ML) is a field of study in artificial intelligence concerned with the development and study of statistical algorithms that can learn from data and generalize to unseen data, and thus perform tasks without explicit instructions."
    
def test_pdf_extract_comments(mock_json_load, mock_text_open, mock_path_exists):
    comments = pdf_extract_comments("filename.pdf", comment_types=["FreeText"])
    assert comments == "dummy data\n\n"

    comments = pdf_extract_comments("filename.pdf", comment_types=["Highlight"])
    assert comments == "* Page 12:\n\n> Some text\n\nA highlight\n\n"
    
