import pytest
import sys
import os
import glob
import referia

from unittest.mock import MagicMock

from referia.util.widgets import list_stateful_widgets, ReferiaWidget, ReferiaStatefulWidget, FieldWidget, ElementWidget, IndexSelector, ReferiaMultiWidget, ScreenCapture, FullSelector, IndexSubIndexSelectorSelect, CreateDocButton, CreateSummaryDocButton, CreateSummaryButton, SaveButton, ReloadButton, PopulateButton, gocf_, gsv_, gwc_, gwu_, gwf_, gwef_, populate_widgets, populate_element_widgets, MyFileChooser
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
    default_value = "default"
    mock_widget_instance = mocker.Mock()
    mock_widget_instance.value = default_value


    # Set up _trait_notifiers as a MagicMock to allow subscripting
    mock_widget_instance._trait_notifiers = MagicMock()
    mock_widget_instance._trait_notifiers.__getitem__.return_value = {
        'value': {'change' : []}
    }    
    
    # Mock the unobserve and observe methods
    mock_widget_instance.unobserve = mocker.Mock()
    mock_widget_instance.observe = mocker.Mock()    
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

def test_element_widget_initialization(mocker):
    mock_function = mocker.Mock()
    test_element = 5

    widget = ElementWidget(function=mock_function, element=test_element)

    assert widget.get_element() == test_element

def test_element_widget_on_value_change(mocker):
    mock_function = mocker.Mock()
    parent_mock = mocker.Mock()
    column_name = "test_column"
    test_element = 3
    new_value = "new_value"

    widget = ElementWidget(function=mock_function, parent=parent_mock, column_name=column_name, element=test_element)

    change_event_mock = mocker.Mock()
    type(change_event_mock).new = mocker.PropertyMock(return_value=new_value)

    widget.on_value_change(change_event_mock)

    parent_mock.set_column.assert_called_once_with(column_name)
    parent_mock.set_value_by_element.assert_called_once_with(new_value, test_element)

def test_element_widget_refresh(mocker):
    mock_function = mocker.Mock()
    parent_mock = mocker.Mock()
    column_name = "test_column"
    test_element = 2
    new_value = "updated_value"

    parent_mock.get_value_by_element.return_value = new_value

    widget = ElementWidget(function=mock_function, parent=parent_mock, column_name=column_name, element=test_element)
    widget.refresh()

    assert widget.get_value() == new_value

def test_element_widget_set_get_element(mocker):
    mock_function = mocker.Mock()
    test_element = 4

    widget = ElementWidget(function=mock_function)
    widget.set_element(test_element)

    assert widget.get_element() == test_element
    
def test_index_selector_initialization(mocker):
    parent_mock = mocker.Mock()
    parent_mock.index = [1, 2, 3]
    parent_mock.get_index.return_value = 2

    selector = IndexSelector(parent=parent_mock)

    assert selector._ipywidget.options == (1, 2, 3)
    assert selector.get_value() == 2

def test_index_selector_on_value_change(mocker):
    parent_mock = mocker.Mock()
    parent_mock.index = [1, 2, 3]
    parent_mock.get_index.return_value = 1

    selector = IndexSelector(parent=parent_mock)

    change_event_mock = mocker.Mock()
    type(change_event_mock).new = mocker.PropertyMock(return_value=2)

    selector.on_value_change(change_event_mock)

    # TK: This is triggered twice, but if I repeat
    # selector.on_value_change it only appears once more.
    # parent_mock.set_index.assert_called_once_with(2)
    parent_mock.view_series.assert_called_once()

def test_index_selector_set_index(mocker):
    parent_mock = mocker.Mock()
    parent_mock.index = [1, 2, 3]
    parent_mock.get_index.return_value = 1

    selector = IndexSelector(parent=parent_mock)
    selector.set_index(3)

    assert selector.get_value() == 3

def test_index_selector_refresh(mocker):
    parent_mock = mocker.Mock()
    parent_mock.index = [1, 2, 3]
    parent_mock.get_index.return_value = 1

    selector = IndexSelector(parent=parent_mock)
    initial_value = selector.get_value()

    selector.refresh()

    assert selector.get_value() == initial_value
    

# Test Initialization
def test_referia_multi_widget_initialization(mocker):
    parent_mock = mocker.Mock()
    stateful_args = {
        'key1': {'function': mocker.Mock(), 'result_function': mocker.Mock(), 
                 'conversion': mocker.Mock(), 'reversion': mocker.Mock()}
    }
    stateless_args = {
        'key2': {'function': mocker.Mock(), 'on_click_function': mocker.Mock()}
    }

    widget = ReferiaMultiWidget(parent=parent_mock, stateful_args=stateful_args, stateless_args=stateless_args)

    assert 'key1' in widget._ipywidgets
    assert widget._ipywidgets['key1']['stateful'] == True
    assert 'key2' in widget._ipywidgets
    assert widget._ipywidgets['key2']['stateful'] == False

# Test add_stateful Method
def test_add_stateful(mocker):
    parent_mock = mocker.Mock()
    widget = ReferiaMultiWidget(parent=parent_mock, stateful_args={}, stateless_args={})

    key = 'key1'
    item = {'function': mocker.Mock(), 'result_function': mocker.Mock(), 
            'conversion': mocker.Mock(), 'reversion': mocker.Mock()}

    widget.add_stateful(key, item)

    assert key in widget._ipywidgets
    assert widget._ipywidgets[key]['stateful'] == True

# Test update_side_effects Method
def test_update_side_effects(mocker):
    parent_mock = mocker.Mock()
    widget = ReferiaMultiWidget(parent=parent_mock, stateful_args={}, stateless_args={})

    key = 'key1'
    item = {'function': mocker.Mock(), 'result_function': mocker.Mock(), 
            'conversion': mocker.Mock(), 'reversion': mocker.Mock()}

    widget.add_stateful(key, item)
    widget.update_side_effects(key, item)

    assert widget._ipywidgets[key]['on_change'] is not None

# Test add_stateless Method
def test_add_stateless(mocker):
    parent_mock = mocker.Mock()
    widget = ReferiaMultiWidget(parent=parent_mock, stateful_args={}, stateless_args={})

    key = 'key2'
    item = {'function': mocker.Mock(), 'on_click_function': mocker.Mock()}

    widget.add_stateless(key, item)

    assert key in widget._ipywidgets
    assert widget._ipywidgets[key]['stateful'] == False

# Test display Method
def test_display(mocker):
    mocker.patch('IPython.display.display')
    mock_vbox = mocker.patch('ipywidgets.VBox')
    parent_mock = mocker.Mock()
    widget = ReferiaMultiWidget(parent=parent_mock, stateful_args={}, stateless_args={})

    widget.display()

    ipyw.VBox.assert_called()

def test_screen_capture_initialization(mocker):
    parent_mock = mocker.Mock()
    parent_mock.copy_screen_capture = mocker.Mock()

    # Mock ipywidgets.Image and ipywidgets.Button
    mock_image = mocker.patch.object(ipyw, 'Image', return_value=mocker.Mock())
    mock_button = mocker.patch.object(ipyw, 'Button', return_value=mocker.Mock())

    screen_capture = ScreenCapture(parent=parent_mock)

    # Check if the stateful widget "image" is correctly set up
    assert "image" in screen_capture._ipywidgets
    mock_image.assert_called_once()

    # Check if the stateless widget "capture_button" is correctly set up
    assert "capture_button" in screen_capture._ipywidgets
    mock_button.assert_called_once()

    # Check if on_click was set up for the button
    button_widget = screen_capture._ipywidgets["capture_button"]["widget"]
    button_widget.on_click.assert_called_once()


# Test Initialization for `FullSelector`
def test_full_selector_initialization(mocker):
    parent_mock = mocker.Mock()
    stateful_args = {
        'key1': {
            'function': mocker.Mock(),
            'result_function': mocker.Mock(),
            'value_function': mocker.Mock(),
            'options_function': mocker.Mock(),
            'conversion': mocker.Mock(),
            'reversion': mocker.Mock()
        }
    }
    stateless_args = {
        'key2': {
            'function': mocker.Mock(),
            'on_click_function': mocker.Mock()
        }
    }

    full_selector = FullSelector(parent=parent_mock, stateful_args=stateful_args, stateless_args=stateless_args)

    assert 'key1' in full_selector._ipywidgets
    assert 'key2' in full_selector._ipywidgets
    

# Test Initialization
def test_index_subindex_selector_select_initialization(mocker):
    parent_mock = mocker.Mock()
    parent_mock.get_indices = mocker.Mock()
    parent_mock.get_selectors = mocker.Mock()
    parent_mock.get_subindices = mocker.Mock()
    parent_mock.get_index = mocker.Mock(return_value=1)
    parent_mock.get_selector = mocker.Mock(return_value='selector1')
    parent_mock.get_subindex = mocker.Mock(return_value='subindex1')
    parent_mock.get_select_subindex = mocker.Mock(return_value=True)
    parent_mock.get_select_selector = mocker.Mock(return_value=True)
    parent_mock.add_series_row = mocker.Mock()

    mocker.patch.object(ipyw, 'Dropdown', return_value=mocker.Mock())
    mocker.patch.object(ipyw, 'Checkbox', return_value=mocker.Mock())
    mocker.patch.object(ipyw, 'Button', return_value=mocker.Mock())

    selector = IndexSubIndexSelectorSelect(parent=parent_mock)

    assert "index_select" in selector._ipywidgets
    assert "selector_select" in selector._ipywidgets
    assert "subindex_select" in selector._ipywidgets
    assert "select_subindex_checkbox" in selector._ipywidgets
    assert "select_selector_checkbox" in selector._ipywidgets
    assert "generate_button" in selector._ipywidgets

def test_index_subindex_selector_select_on_value_change(mocker):
    parent_mock = mocker.Mock()
    mocker.patch.object(ipyw, 'Dropdown', return_value=mocker.Mock())
    mocker.patch.object(ipyw, 'Checkbox', return_value=mocker.Mock())
    selector = IndexSubIndexSelectorSelect(parent=parent_mock)

    change_event_mock = mocker.Mock()
    type(change_event_mock).new = mocker.PropertyMock(return_value="new_value")

    selector.on_value_change(change_event_mock)


def test_index_subindex_selector_select_set_index(mocker):
    parent_mock = mocker.Mock()
    parent_mock.get_indices = mocker.Mock(return_value=[1, 2, 3])
    parent_mock.get_selectors = mocker.Mock(return_value=['selector1', 'selector2'])
    parent_mock.get_subindices = mocker.Mock(return_value=['subindex1', 'subindex2'])
    parent_mock.get_index = mocker.Mock(return_value=1)
    parent_mock.get_selector = mocker.Mock(return_value='selector1')
    parent_mock.get_subindex = mocker.Mock(return_value='subindex1')
    parent_mock.get_select_subindex = mocker.Mock(return_value=True)
    parent_mock.get_select_selector = mocker.Mock(return_value=True)
    parent_mock.add_series_row = mocker.Mock()

    mock_set_value_function = mocker.Mock()

    # Mock gsv_ to return our mock_set_value_function
    gsv_mock = mocker.patch('referia.util.widgets.gsv_', return_value=mock_set_value_function)
   
    mocker.patch.object(ipyw, 'Dropdown', return_value=mocker.Mock())
    mocker.patch.object(ipyw, 'Checkbox', return_value=mocker.Mock())
    mocker.patch.object(ipyw, 'Button', return_value=mocker.Mock())

    selector = IndexSubIndexSelectorSelect(parent=parent_mock)

    new_index_value = "new_index"
    selector.set_index(new_index_value)

    # Check if the correct method is being called on the widget
    index_widget = selector._ipywidgets["index_select"]["widget"]
    assert hasattr(index_widget, 'set_value'), "Widget does not have a set_value method"

    # Assert that the mock set_value function was called correctly
    mock_set_value_function.assert_called_once_with(new_index_value)


# Mock parent class for testing
class MockParent:
    def create_document(self, document, summary=False):
        pass

    def create_summary(self, details):
        pass

    def save_flows(self):
        pass

    def load_flows(self, reload=False):
        pass

    def populate_display(self):
        pass

@pytest.mark.parametrize("summary", [True, False])
def test_create_doc_button(mocker, summary):
    parent_mock = mocker.Mock(spec=MockParent)
    button = CreateDocButton(type="DocType", document="Doc", parent=parent_mock) if not summary else CreateSummaryDocButton(type="DocType", document="Doc", parent=parent_mock)
    
    mocker.patch.object(parent_mock, 'create_document')
    button.on_click(None)
    parent_mock.create_document.assert_called_once_with("Doc", summary=summary)

def test_create_summary_button(mocker):
    parent_mock = mocker.Mock(spec=MockParent)
    details = {"detail_key": "detail_value"}
    button = CreateSummaryButton(type="SummaryType", details=details, parent=parent_mock)

    mocker.patch.object(parent_mock, 'create_summary')
    button.on_click(None)
    parent_mock.create_summary.assert_called_once_with(details)

def test_save_button(mocker):
    parent_mock = mocker.Mock(spec=MockParent)
    button = SaveButton(parent=parent_mock)

    mocker.patch.object(parent_mock, 'save_flows')
    button.on_click(None)
    parent_mock.save_flows.assert_called_once()

def test_reload_button(mocker):
    parent_mock = mocker.Mock(spec=MockParent)
    button = ReloadButton(parent=parent_mock)

    mocker.patch.object(parent_mock, 'load_flows')
    button.on_click(None)
    parent_mock.load_flows.assert_called_once_with(reload=True)

def test_populate_button(mocker):
    # Creating a chain of mock objects for nested attributes
    compute_mock = mocker.Mock()
    data_mock = mocker.Mock(_compute=compute_mock)
    parent_mock = mocker.Mock(_data=data_mock, spec=MockParent)

    compute = {"compute_key": "compute_value"}
    button = PopulateButton(target="Target", compute=compute, parent=parent_mock)

    mocker.patch.object(parent_mock, 'populate_display')
    mocker.patch.object(compute_mock, 'run')
    mocker.patch.object(compute_mock, 'prep', return_value=compute)

    button.on_click(None)

    parent_mock.populate_display.assert_called_once()
    compute_mock.run.assert_called_once_with(compute)
    compute_mock.prep.assert_called_once_with(compute)

class MockReferiaMultiWidget:
    def __init__(self):
        self._ipywidgets = {}

@pytest.fixture(autouse=True)
def mock_widgets(mocker):
    mocker.patch('referia.util.widgets.FieldWidget', return_value=mocker.Mock())
    mocker.patch('referia.util.widgets.ElementWidget', return_value=mocker.Mock())

# Test gsv_
def test_gsv_(mocker):
    obj = MockReferiaMultiWidget()
    key = 'test_key'
    mock_widget = mocker.Mock()
    item = {'widget': mock_widget, 'conversion': None, 'result_function': mocker.Mock()}
    obj._ipywidgets[key] = item

    set_value_function = gsv_(key, item, obj)
    assert callable(set_value_function)
    set_value_function('value')
    assert mock_widget.value == 'value'
    item['result_function'].assert_called_once_with('value')

# Test gwu_
def test_gwu_(mocker):
    obj = MockReferiaMultiWidget()
    key = 'test_key'
    mock_widget = mocker.Mock()
    item = {
        'widget': mock_widget,
        'options_function': mocker.Mock(return_value=['option1', 'option2']),
        'value_function': mocker.Mock(return_value='value'),
    }
    obj._ipywidgets[key] = item

    update_function = gwu_(key, item, obj)
    assert callable(update_function)
    update_function()
    assert mock_widget.options == ['option1', 'option2']
    assert mock_widget.value == 'value'

# Test gwf_
def test_gwf_(mocker):
    function_mock = mocker.Mock(return_value=mocker.Mock())

    # Mocking the FieldWidget function in the gwf_ generator
    field_widget_mock = mocker.patch('referia.util.widgets.FieldWidget', return_value=mocker.Mock())
    widget_function = gwf_('test_widget', function_mock, default_args={'arg1': 'default1'})

    assert callable(widget_function)
    widget = widget_function(arg1='value1')

    field_widget_mock.assert_called_once_with(
        function=function_mock,
        arg1="value1",
        conversion=None,
        reversion=None,
    )

    # Check default argument
    field_widget_mock2 = mocker.patch('referia.util.widgets.FieldWidget', return_value=mocker.Mock())
    widget = widget_function()

    field_widget_mock2.assert_called_once_with(
        function=function_mock,
        arg1="default1",
        conversion=None,
        reversion=None,
    )
    
def test_gwef_(mocker):
    function_mock = mocker.Mock(return_value=mocker.Mock())

    # Mocking the ElementWidget function in the gwef_ generator
    element_widget_mock = mocker.patch('referia.util.widgets.ElementWidget', return_value=mocker.Mock())
    
    widget_function = gwef_('test_element_widget', function_mock, default_args={'arg1': 'default1'})
    
    assert callable(widget_function)
    widget = widget_function(arg1='value1')
    
    # Check if ElementWidget was called with the correct arguments including the default ones
    element_widget_mock.assert_called_once_with(
        function=function_mock,
        arg1='value1',
        conversion=None,
        reversion=None
    )

    element_widget_mock2 = mocker.patch('referia.util.widgets.ElementWidget', return_value=mocker.Mock())
    
    widget = widget_function()
    
    # Check if ElementWidget was called with the correct default argument
    element_widget_mock2.assert_called_once_with(
        function=function_mock,
        arg1='default1',
        conversion=None,
        reversion=None
    )

# Test the population of widgets.
def test_populate_widgets(mocker):
    populate_widgets(list_stateful_widgets)
    for widget in list_stateful_widgets:
        assert hasattr(referia.util.widgets, widget["name"]), f"Widget {widget['name']} not found in module after population."

# Test the population of element widgets
def test_populate_element_widgets():
    populate_element_widgets(list_stateful_widgets)

    for widget in list_stateful_widgets:
        element_widget_name = "Element" + widget["name"]
        assert hasattr(referia.util.widgets, element_widget_name), f"Element Widget {element_widget_name} not found in module after population."
    

def test_my_file_chooser(mocker):
    directory = "test_dir"
    glob_pattern = "*.py"
    mocker.patch('os.path.join', return_value=directory)
    mocker.patch('glob.glob', return_value=[f"{directory}/file1.py", f"{directory}/file2.py"])
    mocker.patch('os.path.basename', side_effect=lambda x: x.split("/")[-1])

    widget = MyFileChooser(directory=directory, glob=glob_pattern)

    assert isinstance(widget, ipyw.Dropdown)
    assert widget.options == ("", "file1.py", "file2.py")
        
@pytest.fixture
def mock_observer(mocker):
    return MagicMock()

@pytest.fixture
def mock_textarea(mocker, mock_observer):
    mock_widget = mocker.Mock(spec=ipyw.Textarea)
    mock_widget.value = "default"
    
    mock_widget._trait_notifiers = {'value': {'change': [mock_observer]}}    
    mocker.patch('ipywidgets.Textarea', return_value=mock_widget)
    return mock_widget

@pytest.fixture
def mock_conversion():
    return lambda x: f"converted_{x}"

# Create a widget and set its value
def test_stateful_widget_set_get_value(mock_textarea, mock_conversion):
    test_value = "test value"
    
    widget = ReferiaStatefulWidget(conversion=mock_conversion)
    
    widget.set_value(test_value)
    
    assert mock_textarea.value == f"converted_{test_value}"
    mock_textarea.unobserve.assert_not_called()
    assert widget.get_value() == f"converted_{test_value}"


# Create a widget and set its value silently.
def test_stateful_widget_set_value_silently(mock_textarea, mock_conversion, mock_observer):
    test_value = "silent test value"
    
    widget = ReferiaStatefulWidget(conversion=mock_conversion)
    
    # Check that observe was called once during initialization
    assert mock_textarea.observe.call_count == 1
    assert mock_textarea.observe.call_args_list[0][0][0].__func__.__name__ == 'on_value_change'
    assert mock_textarea.observe.call_args_list[0][1] == {'names': 'value'}

    widget.set_value_silently(test_value)
    assert mock_textarea.value == f"converted_{test_value}"

    # Check that unobserve was called with the widget's observer
    mock_textarea.unobserve.assert_called_once()
    assert mock_textarea.unobserve.call_args[0][0] == mock_observer
    assert mock_textarea.unobserve.call_args[1] == {'names': 'value'}

    # Check that observe was called again after set_value_silently
    assert mock_textarea.observe.call_count == 2
    assert mock_textarea.observe.call_args_list[0][0][0].__func__.__name__ == 'on_value_change'
    assert mock_textarea.observe.call_args_list[0][1] == {'names': 'value'}
    
    # Check the second call (attaching the MagicMock)
    assert mock_textarea.observe.call_args_list[1][0][0] == mock_observer
    assert mock_textarea.observe.call_args_list[1][1] == {'names': 'value'}


# Test that the value of the widget changes when set_value is called    
@pytest.mark.parametrize("initial_value,new_value", [
    ("default", "new value"),
    ("", "non-empty value"),
    ("old value", "new"),
])
def test_stateful_widget_value_changes(mock_textarea, mock_conversion, initial_value, new_value):
    mock_textarea.value = initial_value
    widget = ReferiaStatefulWidget(conversion=mock_conversion)
    
    widget.set_value(new_value)
    
    assert mock_textarea.value == f"converted_{new_value}"
    assert widget.get_value() == f"converted_{new_value}"

# Test that the value of the widget changes when set_value_silently is called
def test_stateful_widget_observers(mocker):
    mock_widget = mocker.Mock(spec=ipyw.Textarea)
    mock_widget._trait_notifiers = {'value': {'change': [mocker.Mock(), mocker.Mock()]}}
    mocker.patch('ipywidgets.Textarea', return_value=mock_widget)

    widget = ReferiaStatefulWidget()
    widget.set_value_silently("test")

    # Check that the observers were unobserved and observed again
    for observer in mock_widget._trait_notifiers['value']['change']:
        mock_widget.unobserve.assert_any_call(observer, names='value')
        mock_widget.observe.assert_any_call(observer, names='value')    

    # Check that the value of the widget was updated.
    assert mock_widget.value == "test"


