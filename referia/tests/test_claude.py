import pytest
from unittest.mock import MagicMock
from referia.util.widgets import ReferiaStatefulWidget
import ipywidgets

@pytest.fixture
def mock_observer(mocker):
    return MagicMock()

@pytest.fixture
def mock_textarea(mocker, mock_observer):
    mock_widget = mocker.Mock(spec=ipywidgets.Textarea)
    mock_widget.value = "default"
    
    mock_widget._trait_notifiers = {'value': {'change': [mock_observer]}}
    mocker.patch('ipywidgets.Textarea', return_value=mock_widget)
    return mock_widget

@pytest.fixture
def mock_conversion():
    return lambda x: f"converted_{x}"


def test_stateful_widget_set_get_value(mock_textarea, mock_conversion):
    test_value = "test value"
    
    widget = ReferiaStatefulWidget(conversion=mock_conversion)
    
    widget.set_value(test_value)
    
    assert mock_textarea.value == f"converted_{test_value}"
    mock_textarea.unobserve.assert_not_called()
    assert widget.get_value() == f"converted_{test_value}"



# def test_stateful_widget_set_value_silently(mock_textarea, mock_conversion, mock_observer):
#     test_value = "silent test value"
    
#     widget = ReferiaStatefulWidget(conversion=mock_conversion)
    
#     # Check that observe was called once during initialization
#     assert mock_textarea.observe.call_count == 1
#     assert mock_textarea.observe.call_args_list[0][0][0].__func__.__name__ == 'on_value_change'
#     assert mock_textarea.observe.call_args_list[0][1] == {'names': 'value'}

#     widget.set_value_silently(test_value)
#     assert mock_textarea.value == f"converted_{test_value}"

#     # Check that unobserve was called with the widget's observer
#     mock_textarea.unobserve.assert_called_once()
#     assert mock_textarea.unobserve.call_args[0][0] == mock_observer
#     assert mock_textarea.unobserve.call_args[1] == {'names': 'value'}

#     # Check that observe was called again after set_value_silently
#     assert mock_textarea.observe.call_count == 2
#     assert mock_textarea.observe.call_args_list[0][0][0].__func__.__name__ == 'on_value_change'
#     assert mock_textarea.observe.call_args_list[0][1] == {'names': 'value'}
    
#     # Check the third call (attaching the MagicMock)
#     assert mock_textarea.observe.call_args_list[1][0][0] == mock_observer
#     assert mock_textarea.observe.call_args_list[1][1] == {'names': 'value'}


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

# def test_stateful_widget_observers(mocker):
#     mock_widget = mocker.Mock(spec=ipywidgets.Textarea)
#     mock_widget._trait_notifiers = {'value': {'change': [mocker.Mock(), mocker.Mock()]}}
#     mocker.patch('ipywidgets.Textarea', return_value=mock_widget)

#     widget = ReferiaStatefulWidget()
#     widget.set_value_silently("test")

#     for observer in mock_widget._trait_notifiers['value']['change']:
#         mock_widget.unobserve.assert_any_call(observer, names='value')
#         mock_widget.observe.assert_any_call(observer, names='value')    


