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
    

def test_extract_widget_error_unknown_widget_type(mocker):
    mock_reviewer = mocker.Mock()
    mock_widgets = mocker.Mock()

    details_unknown_widget = {"type": "UnknownWidget", "field": "test_field"}

    with pytest.raises(Exception) as excinfo:
        extract_widget(details_unknown_widget, mock_reviewer, mock_widgets)
    assert "Cannot find UnknownWidget interaction type" in str(excinfo.value)
    
def test_extract_widget_key_generation_and_argument_processing(mocker):
    mock_reviewer = mocker.Mock()
    mock_widgets = mocker.Mock()
    mock_reviewer._column_names_dict = {}
    mock_reviewer._default_field_vals = {}

    # Mock the globals function to return a mock for IntSlider
    int_slider_mock = mocker.Mock()
    globals_mock = mocker.patch('builtins.globals', return_value={'IntSlider': int_slider_mock})

    details = {"type": "IntSlider", "field": "test_field", "args": {"some_arg": "some_value"}}
    extract_widget(details, mock_reviewer, mock_widgets)

    # Verify if the mock IntSlider was called with the correct arguments
    assert int_slider_mock.called
    called_args, called_kwargs = int_slider_mock.call_args
    assert called_kwargs['some_arg'] == "some_value"
    assert 'parent' in called_kwargs and 'field_name' in called_kwargs

    # Verify if the widget was added correctly
    assert mock_widgets.add.called

def test_extract_widget_interaction_with_reviewer_and_widgets(mocker):
    mock_reviewer = mocker.Mock()
    mock_widgets = mocker.Mock()
    mock_reviewer._column_names_dict = {}
    mock_reviewer._default_field_vals = {}

    details = {"type": "IntSlider", "field": "test_field"}
    extract_widget(details, mock_reviewer, mock_widgets)

    # Verify interaction with reviewer and widgets
    assert "test_field" in mock_reviewer._column_names_dict
    assert "test_field" in mock_reviewer._default_field_vals
    assert mock_widgets.add.called

def test_extract_widget_layout_and_local_argument_processing(mocker):
    mock_reviewer = mocker.Mock()
    mock_widgets = mocker.Mock()
    mock_reviewer._column_names_dict = {}
    mock_reviewer._default_field_vals = {}

    details = {
        "type": "IntSlider",
        "field": "test_field",
        "layout": {"width": "50%"},
        "local": True
    }
    extract_widget(details, mock_reviewer, mock_widgets)

    # Assume widget_instance is the instance of the widget created
    widget_instance = mock_widgets.add.call_args[1]["test_field"]

    # Check if the layout is set correctly
    assert widget_instance.get_layout().width == "50%"


