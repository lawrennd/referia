# File: tests/test_review.py

import sys
import pytest
import pandas as pd
from unittest.mock import Mock, patch, create_autospec, MagicMock

from lynguine.assess.display import WidgetCluster

from referia.assess.review import (
    Reviewer, LoadWidgetCluster, GroupWidgetCluster,
    CompositeWidgetCluster, DynamicWidgetCluster, LoopWidgetCluster,
    set_default_values, process_layout_and_local_args, extract_widget,
    extract_review, extract_load_review, extract_group_review,
    expand_composite_review, extract_loop_review
)

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



@pytest.fixture
def mock_data():
    return Mock()

@pytest.fixture
def mock_interface():
    return {
        "viewer": {"type": "Markdown", "value": "Test viewer"},
        "review": [{"type": "Checkbox", "field": "test_field"}],
        "documents": [{"type": "CreateDocButton", "name": "Test Doc"}],
        "summary": [{"type": "CreateSummaryButton", "name": "Test Summary"}],
        "summary_documents": [{"type": "CreateSummaryDocButton", "name": "Test Summary Doc"}],
    }

@pytest.fixture
def reviewer(mock_data, mock_interface):
    mock_interface["scored"] = True  # Add this line
    return Reviewer(data=mock_data, interface=mock_interface, system=Mock())


def test_process_layout_and_local_args():
    process_details = {
        "layout": {"width": "100px"},
        "local": {"test": "value"},
        "args": {"existing": "arg"}
    }
    result = process_layout_and_local_args(process_details)
    assert "layout" in result
    assert result["local"] == {"test": "value"}
    assert result["existing"] == "arg"

def test_extract_widget_with_different_widget_types(mocker):
    mock_reviewer = create_autospec(Reviewer, instance=True)
    mock_reviewer._column_names_dict = {}
    mock_reviewer._default_field_vals = {}
    mock_widgets = mocker.Mock()

    details_int_slider = {"type": "IntSlider", "field": "test_field"}
    
    # Create a mock IntSlider
    mock_int_slider = MagicMock()
    mock_int_slider.return_value.get_value.return_value = 0

    # Inject the mock into the global namespace of the module under test
    import referia.assess.review as review_module
    original_int_slider = getattr(review_module, 'IntSlider', None)
    setattr(review_module, 'IntSlider', mock_int_slider)

    try:
        extract_widget(details_int_slider, mock_reviewer, mock_widgets)

        assert mock_widgets.add.called
        assert "test_field" in mock_reviewer._default_field_vals
        assert mock_int_slider.called
    finally:
        # Restore the original IntSlider if it existed
        if original_int_slider:
            setattr(review_module, 'IntSlider', original_int_slider)
        else:
            delattr(review_module, 'IntSlider')

def test_extract_widget_interaction_with_reviewer_and_widgets(mocker):
    mock_reviewer = create_autospec(Reviewer, instance=True)
    mock_reviewer._column_names_dict = {}
    mock_reviewer._default_field_vals = {}
    mock_widgets = mocker.Mock()

    details = {"type": "IntSlider", "field": "test_field"}
    
    # Create a mock IntSlider
    mock_int_slider = MagicMock()
    mock_int_slider.return_value.get_value.return_value = 0

    # Inject the mock into the global namespace of the module under test
    import referia.assess.review as review_module
    original_int_slider = getattr(review_module, 'IntSlider', None)
    setattr(review_module, 'IntSlider', mock_int_slider)

    try:
        extract_widget(details, mock_reviewer, mock_widgets)

        assert "test_field" in mock_reviewer._column_names_dict
        assert "test_field" in mock_reviewer._default_field_vals
        assert mock_int_slider.called
    finally:
        # Restore the original IntSlider if it existed
        if original_int_slider:
            setattr(review_module, 'IntSlider', original_int_slider)
        else:
            delattr(review_module, 'IntSlider')
            
def test_set_default_values():
    reviewer = MagicMock()
    reviewer._default_field_vals = {}
    reviewer._default_field_source = {}
    reviewer._data.columns = ["test_column"]

    details = {"field": "test_field", "default": {"value": "test_value", "source": "test_column"}}
    widget_type = MagicMock()
    widget_type.return_value.get_value.return_value = "default_value"

    set_default_values(details, widget_type, reviewer)

    assert reviewer._default_field_vals["test_field"] == "test_value"
    assert reviewer._default_field_source["test_field"] == "test_column"

def test_extract_widget():
    reviewer = create_autospec(Reviewer, instance=True)
    reviewer._data = MagicMock()
    reviewer._data.columns = []
    reviewer._column_names_dict = {}
    reviewer._default_field_vals = {}
    widgets = MagicMock()
    details = {
        "type": "Checkbox",
        "field": "test_field",
        "args": {"value": True}
    }
    
    with patch("referia.assess.review.Checkbox") as mock_checkbox:
        mock_checkbox.return_value.get_value.return_value = False
        extract_widget(details, reviewer, widgets)
        
    assert "test_field" in reviewer._default_field_vals
    assert mock_checkbox.called
    assert widgets.add.called
    
def test_reviewer_init(reviewer):
    assert isinstance(reviewer._widgets, WidgetCluster)
    assert reviewer._write_score == True
    assert reviewer._select_subindex == False
    assert reviewer._select_selector == False


def test_reviewer_create_widgets(reviewer):
    reviewer._create_widgets()
    assert reviewer._widgets.has("_progress_label")
    assert reviewer._widgets.has("_reload_button")
    assert reviewer._widgets.has("_save_button")

def test_reviewer_run(reviewer):
    with patch.object(reviewer, 'select_index') as mock_select_index, \
         patch.object(reviewer._widgets, 'display') as mock_display, \
         patch.object(reviewer, 'populate_display') as mock_populate_display, \
         patch.object(reviewer, 'view_series') as mock_view_series:
        
        reviewer.run()
        
        mock_select_index.assert_called_once()
        mock_display.assert_called_once()
        mock_populate_display.assert_called_once()
        mock_view_series.assert_called_once()

def test_load_widget_cluster():
    load_cluster = LoadWidgetCluster(name="test", parent=Mock())
    assert isinstance(load_cluster, WidgetCluster)

def test_group_widget_cluster():
    group_cluster = GroupWidgetCluster(name="test", parent=Mock())
    assert isinstance(group_cluster, WidgetCluster)

def test_composite_widget_cluster():
    composite_cluster = CompositeWidgetCluster(name="test", parent=Mock())
    assert isinstance(composite_cluster, WidgetCluster)

def test_dynamic_widget_cluster():
    details = {"type": "loop", "start": 0, "stop": 5, "body": []}
    dynamic_cluster = DynamicWidgetCluster(details=details, name="test", parent=Mock())
    assert isinstance(dynamic_cluster, WidgetCluster)
    assert dynamic_cluster._details == details

def test_loop_widget_cluster():
    details = {"type": "loop", "start": 0, "stop": 5, "body": []}
    loop_cluster = LoopWidgetCluster(details=details, name="test", parent=Mock())
    assert isinstance(loop_cluster, DynamicWidgetCluster)

def test_extract_review(reviewer):
    widgets = Mock()
    details = {"type": "Checkbox", "field": "test_field"}
    
    with patch("referia.assess.review.extract_widget") as mock_extract_widget:
        extract_review(details, reviewer, widgets)
        mock_extract_widget.assert_called_once_with(details, reviewer, widgets)

def test_extract_load_review():
    reviewer = Mock()
    widgets = Mock()
    details = {"details": "test_file.csv"}
    
    with patch("referia.assess.review.access.io.read_data") as mock_read_data, \
         patch("referia.assess.review.extract_review") as mock_extract_review:
        
        mock_read_data.return_value = (pd.DataFrame({"col": [1, 2, 3]}), {})
        
        extract_load_review(details, reviewer, widgets)
        
        mock_read_data.assert_called_once_with("test_file.csv")
        assert mock_extract_review.call_count == 3

def test_extract_group_review():
    reviewer = Mock()
    widgets = Mock()
    details = {
        "children": [
            {"type": "Checkbox", "field": "test_field1"},
            {"type": "Checkbox", "field": "test_field2"}
        ]
    }
    
    with patch("referia.assess.review.extract_review") as mock_extract_review:
        extract_group_review(details, reviewer, widgets)
        assert mock_extract_review.call_count == 2

def test_expand_composite_review():
    reviewer = Mock()
    widgets = Mock()
    details = {
        "type": "CriterionComment",
        "prefix": "test",
        "width": "500px"
    }

    with patch("referia.assess.review.extract_review") as mock_extract_review:
        expanded_details = expand_composite_review(details)
        for detail in expanded_details:
            mock_extract_review(detail, reviewer, widgets)
        
        # Check that extract_review was called twice
        assert mock_extract_review.call_count == 2
        
        # Check the first call (criterion)
        first_call_args = mock_extract_review.call_args_list[0][0]
        assert first_call_args[0]["type"] == "Criterion"
        assert first_call_args[0]["prefix"] == "test"
        assert first_call_args[0]["width"] == "500px"
        
        # Check the second call (comment)
        second_call_args = mock_extract_review.call_args_list[1][0]
        assert second_call_args[0]["type"] == "Textarea"
        assert second_call_args[0]["field"] == "test Comment"
        assert second_call_args[0]["args"]["layout"]["width"] == "500px"

    # Test with default width
    details = {
        "type": "CriterionComment",
        "prefix": "test"
    }

    with patch("referia.assess.review.extract_review") as mock_extract_review:
        expanded_details = expand_composite_review(details)
        for detail in expanded_details:
            mock_extract_review(detail, reviewer, widgets)
        
        # Check the second call (comment) for default width
        second_call_args = mock_extract_review.call_args_list[1][0]
        assert second_call_args[0]["args"]["layout"]["width"] == "800px"

def test_extract_loop_review():
    reviewer = Mock()
    widgets = Mock()
    details = {
        "start": 0,
        "stop": 3,
        "body": {"type": "Checkbox", "field": "test_field"}
    }
    
    with patch("referia.assess.review.extract_review") as mock_extract_review:
        extract_loop_review(details, reviewer, widgets)
        assert mock_extract_review.call_count == 3    
