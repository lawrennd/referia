import pytest
from referia.util.widgets import ReferiaWidget, ReferiaStatefulWidget, FieldWidget
import ipywidgets as ipyw

def test_widget_initialization_with_default_function(mocker):
    # Mock the ipywidgets.Button
    mock_button = mocker.patch.object(ipyw, 'Button')

    # Create an instance of ReferiaWidget without passing the function
    widget = ReferiaWidget()

    # Assert that the default widget function (Button) is used
    assert widget._ipywidget_function == mock_button

def test_widget_initialization_with_custom_function(mocker):
    custom_function = mocker.Mock()

    # Create an instance of ReferiaWidget with a custom function
    widget = ReferiaWidget(function=custom_function)

    # Assert that the custom function is set correctly
    assert widget._ipywidget_function == custom_function

def test_widget_parent_assignment(mocker):
    parent_mock = mocker.Mock()

    # Create widget with a parent argument
    widget = ReferiaWidget(parent=parent_mock)

    # Assert that the parent is set correctly
    assert widget._parent == parent_mock

def test_widget_private_property_default():
    widget = ReferiaWidget()

    # Assert that the private property is True by default
    assert widget.private is True

def test_widget_close_method(mocker):
    mock_close = mocker.patch.object(ipyw.Widget, 'close')

    widget = ReferiaWidget()
    widget.close()

    # Assert that the close method is called
    mock_close.assert_called_once()

def test_widget_display_method(mocker):
    mock_display = mocker.patch('IPython.display.display')

    widget = ReferiaWidget()
    widget.display()

    # Assert that the IPython display function is called with the widget
    mock_display.assert_called_once_with(widget._ipywidget)
    
def test_stateful_widget_initialization_with_conversion_reversion(mocker):
    conversion_function = mocker.Mock()
    reversion_function = mocker.Mock()

    widget = ReferiaStatefulWidget(conversion=conversion_function, reversion=reversion_function)

    assert widget._conversion == conversion_function
    assert widget._reversion == reversion_function

def test_stateful_widget_initialization_with_viewer_options(mocker):
    viewer_options = {
        "display": mocker.Mock(),
        "tally": mocker.Mock(),
        # Add other viewer options as necessary
    }

    widget = ReferiaStatefulWidget(**viewer_options)

    for key in viewer_options:
        assert widget._viewer[key] == viewer_options[key]

def test_stateful_widget_set_get_value(mocker):
    test_value = "test value"
    mock_conversion = mocker.Mock(return_value=test_value)

    # Create a mock widget with a 'value' attribute
    mock_widget_instance = mocker.Mock()
    mock_widget = mocker.patch('ipywidgets.Textarea', return_value=mock_widget_instance)

    widget = ReferiaStatefulWidget(conversion=mock_conversion)
    widget.set_value(test_value)

    # Assert that the widget's value attribute was set correctly
    assert mock_widget_instance.value == test_value
    # Assert that the conversion function was called with the test value
    mock_conversion.assert_called_once_with(test_value)

def test_stateful_widget_reset_value(mocker):
    default_value = "default"
    
    # Create a mock widget with a 'value' attribute
    mock_widget_instance = mocker.Mock(value=default_value)
    mocker.patch('ipywidgets.Textarea', return_value=mock_widget_instance)

    widget = ReferiaStatefulWidget()
    widget.reset_value()

    # Assert that the widget's value attribute was reset to the default value
    assert widget._ipywidget.value == default_value

def test_stateful_widget_get_column():
    column_name = "test_column"
    widget = ReferiaStatefulWidget(column_name=column_name)

    assert widget.get_column() == column_name

def test_stateful_widget_to_markdown():
    description = "Test Description"
    value = "Test Value"
    widget = ReferiaStatefulWidget(description=description)
    widget.set_value(value)

    expected_markdown = f"#### {description}\n\n{value}"
    assert widget.to_markdown() == expected_markdown
    
def test_field_widget_initialization(mocker):
    function_mock = mocker.Mock()
    conversion_mock = mocker.Mock()
    reversion_mock = mocker.Mock()

    widget = FieldWidget(function=function_mock, conversion=conversion_mock, reversion=reversion_mock)

    assert widget._ipywidget_function == function_mock
    assert widget._conversion == conversion_mock
    assert widget._reversion == reversion_mock

def test_field_widget_on_value_change(mocker):
    # Mock the widget function
    mock_widget_function = mocker.Mock()
    parent_mock = mocker.Mock()
    column_name = "test_column"
    new_value = "new_value"

    # Create a FieldWidget instance with the mocked widget function
    widget = FieldWidget(function=mock_widget_function, parent=parent_mock, column_name=column_name)

    # Mock the change event as an object with a 'new' attribute
    change_event_mock = mocker.Mock()
    type(change_event_mock).new = mocker.PropertyMock(return_value=new_value)

    # Call the on_value_change method with the mocked change event
    widget.on_value_change(change_event_mock)

    # Assertions to verify the behavior
    parent_mock.set_column.assert_called_once_with(column_name)
    parent_mock.set_value.assert_called_once_with(new_value)

def test_field_widget_has_viewer(mocker):
    # Mock the necessary widget function for initialization
    mock_widget_function = mocker.Mock()

    # Initialize FieldWidget with the necessary mocked function
    widget = FieldWidget(function=mock_widget_function)

    # Initially, widget should not have a viewer
    assert not widget.has_viewer()

    # Mock a viewer and simulate a condition where the widget would have a viewer
    widget._viewer["test_viewer"] = mocker.Mock()

    # Now the widget should have a viewer
    assert widget.has_viewer()

def test_field_widget_refresh(mocker):
    # Mock the widget creation function
    mock_widget_function = mocker.Mock(return_value=mocker.Mock())
    
    # Mock parent and set necessary attributes or methods
    parent_mock = mocker.Mock()
    column_name = "test_column"
    new_value = "updated_value"

    # Set up mocks for parent's methods or attributes used in refresh
    parent_mock.get_value.return_value = new_value

    # Create a FieldWidget instance with the necessary arguments
    widget = FieldWidget(function=mock_widget_function, parent=parent_mock, column_name=column_name)

    # Perform the action to be tested
    widget.refresh()

    assert widget.get_value() == new_value
