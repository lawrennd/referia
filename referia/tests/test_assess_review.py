import pytest

from referia.assess.review import extract_widget

def test_extract_widget_with_different_widget_types(mocker):
    mock_reviewer = mocker.Mock()
    mock_widgets = mocker.Mock()
    mock_reviewer._column_names_dict = {}
    mock_reviewer._default_field_vals = {}

    # Assuming 'IntSlider' is a valid type in global_variables
    details_int_slider = {"type": "IntSlider", "field": "test_field"}
    extract_widget(details_int_slider, mock_reviewer, mock_widgets)

    # Check if the widget was added correctly
    assert mock_widgets.add.called
    assert "test_field" in mock_reviewer._default_field_vals

def test_extract_widget_with_field_and_cache(mocker):
    mock_reviewer = mocker.Mock()
    mock_widgets = mocker.Mock()
    mock_reviewer._column_names_dict = {}
    mock_reviewer._default_field_vals = {}

    details_with_field = {"type": "IntSlider", "field": "test_field"}
    extract_widget(details_with_field, mock_reviewer, mock_widgets)

    # Test with 'cache' instead of 'field'
    details_with_cache = {"type": "IntSlider", "cache": "test_cache"}
    extract_widget(details_with_cache, mock_reviewer, mock_widgets)

    # Check if the widget was added correctly for both cases
    assert mock_widgets.add.called
    
