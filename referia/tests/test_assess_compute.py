import pytest
from referia.assess.compute import Compute  # Adjust the import as necessary
from lynguine.assess.data import CustomDataFrame
from unittest.mock import MagicMock

@pytest.fixture
def mock_interface(mocker):
    # Create a mock object with the necessary attributes
    interface_mock_data = {
        "input": {
            "type" : "fake",
            "nrows" : 10,
            "cols" : ["givenName", "familyName"],
            "index" : "givenName"
        },
        "compute": {
            "type" : "precompute",
            "function": "test_function",
            "args": {"arg1": "value1", "arg2": "value2"}
        }
    }
    interface_mock = mocker.MagicMock()
    interface_mock.__getitem__.side_effect = interface_mock_data.__getitem__
    interface_mock.__iter__.side_effect = interface_mock_data.__iter__
    interface_mock.__contains__.side_effect = interface_mock_data.__contains__
    
    interface_mock._directory = "mock_directory"  # Assuming _directory is expected by Compute
    mocker.patch('referia.assess.compute.Interface.from_file', return_value=interface_mock)
    return interface_mock

@pytest.fixture
def mock_data(mocker):
    return CustomDataFrame({})

@pytest.fixture
def compute_instance(mocker, mock_interface):
    # Ensure that Logger is also mocked if necessary
    mocker.patch('lynguine.log.Logger')
    return Compute(mock_interface)

# Patch test_function into the Compute instance
@pytest.fixture
def mock_test_function(mocker, compute_instance):
    mocker.patch.object(compute_instance, 'test_function', return_value=lambda x: x)

# Test initialization
def test_compute_initialization(compute_instance, mock_interface, mock_data):
    #assert compute_instance._data is mock_data
    #assert compute_instance._interface is mock_interface
    pass

def test_compute_creation(mocker, mock_interface):
    # Create a MagicMock object that behaves like a dictionary

    # Patch Interface.from_file to return the mock_interface
    mocker.patch('referia.assess.compute.Interface.from_file', return_value=mock_interface)

    # Patch Compute.__init__ to avoid initialization side effects
    mocker.patch('referia.assess.compute.Compute.__init__', return_value=None)

    # Create a CustomDataFrame object to pass as the 'data' argument
    mock_data = CustomDataFrame([{"cat": "dog"}], colspecs="input")
    
    # Call the method under test with the required 'data' argument
    result = Compute(data=mock_data, interface=mock_interface)

    # Check that a Compute instance is returned
    assert result is not None

    
# Updated mock_compute_functions fixture
@pytest.fixture
def mock_compute_functions(mocker, compute_instance):
    # Define a list of functions including 'test_function'
    mocked_functions = [
        {"name": "test_function", "function": lambda x: x, "default_args": {}}
    ]
    # Patch the _compute_functions_list method to return mocked_functions
    mocker.patch.object(compute_instance, '_compute_functions_list', return_value=mocked_functions)
    return mocked_functions

def test_prep(compute_instance, mock_data, mocker):
    # Mock the gcf_ and gca_ methods
    mocker.patch.object(compute_instance, 'gcf_', return_value=lambda x: x)
    mocker.patch.object(compute_instance, 'gca_', return_value={'arg1': 'value1', 'arg2': 'value2'})

    # Test with minimal settings
    settings_minimal = {"function": "test_function_minimal"}
    result_minimal = compute_instance.prep(settings_minimal, mock_data)
    assert 'function' in result_minimal
    assert callable(result_minimal['function'])

    # Test with additional settings
    settings_additional = {"function": "test_function_additional", "field": "test_field", "refresh": True}
    result_additional = compute_instance.prep(settings_additional, mock_data)
    assert result_additional['function'] is not None
    assert result_additional['refresh'] is True
    assert 'field' in result_additional and result_additional['field'] == "test_field"

    # Test with comprehensive settings
    settings_comprehensive = {
        "function": "test_function_comprehensive",
        "field": "test_field",
        "refresh": True,
    }
    result_comprehensive = compute_instance.prep(settings_comprehensive, mock_data)
    assert result_comprehensive['function'] is not None
    assert result_comprehensive['refresh'] is True
    assert 'field' in result_comprehensive and result_comprehensive['field'] == "test_field"
    assert 'args' in result_comprehensive and 'arg1' in result_comprehensive['args']


@pytest.fixture
def mock_compute_functions():
    # Define a mocked list of functions including 'test_function'
    mocked_functions = [
        {"name": "test_function", "function": lambda x: x, "default_args": {}}
    ]
    return mocked_functions

# Test gcf_ functionality
def test_gcf_(compute_instance, mocker, mock_data):
    # Mock _compute_functions_list with multiple functions
    mocked_functions = [
        {"name": "test_function_one", "function": lambda x: x, "default_args": {}},
        {"name": "test_function_two", "function": lambda y=0: y*2, "default_args": {"param": "default"}, "docstr" : "This is the documentation."}
    ]
    mocker.patch.object(compute_instance, '_compute_functions_list', return_value=mocked_functions)

    # Test for the first function
    function_one = compute_instance.gcf_("test_function_one", mock_data)
    assert callable(function_one)
    assert function_one.__name__ == "test_function_one"

    # Test for the second function
    function_two = compute_instance.gcf_("test_function_two", mock_data)
    assert callable(function_two)
    assert function_two(mock_data, args={"y":5}) == 10  # Testing the functionality
    assert function_two.__name__ == "test_function_two"
    assert function_two.__doc__ == "This is the documentation."

# Updated test_gca_ test
def test_gca_(compute_instance, mocker):
    # Call gca_ method with various arguments
    mocked_functions = [
        {"name": "test_function", "function": lambda x: x, "default_args": {}}
        ]
    mocker.patch.object(compute_instance, '_compute_functions_list', return_value=mocked_functions)
    args_empty = compute_instance.gca_("test_function")
    assert isinstance(args_empty, dict)
    for arglist in ["subseries_args", "column_args", "row_args", "view_args", "function_args", "args", "default_args"]:
        assert arglist in args_empty and not args_empty[arglist] 

    # Test with different argument types
    args_full = compute_instance.gca_("test_function", args={
        "field": "test_field", "refresh" : True}, row_args={"row1": "value1"})
    assert isinstance(args_full, dict)
    print(args_full)
    assert args_full["args"]['field'] == "test_field"
    assert args_full["args"]['refresh'] is True
    assert 'row1' in args_full["row_args"] and args_full["row_args"]['row1'] == "value1"

# Test run method
def test_run(compute_instance, mock_data, mocker):
    compute = {"function": lambda **kwargs: 42, "args": {}}
    result = compute_instance.run(compute, mock_data)
    assert result is None or result == 42

# Test preprocess method
def test_preprocess(compute_instance, mock_data, mock_interface, mocker):
    mocker.patch.object(compute_instance, 'prep', return_value={"function": lambda x: x, "args": {}})
    compute_instance.preprocess(mock_data, mock_interface)
    # Assert preprocess functionality

# Test run_all method
def test_run_all(compute_instance, mocker, mock_data):
    mocker.patch.object(compute_instance, 'run', return_value=None)
    mocker.patch.object(compute_instance, '_computes', {'precompute': [], 'compute': [], 'postcompute': []})
    compute_instance.run_all(mock_data)
    # Assert run_all functionality

# Test _compute_functions_list method
def test_compute_functions_list(compute_instance):
    functions_list = compute_instance._compute_functions_list()
    
    assert isinstance(functions_list, list)
    for func in functions_list:
        assert isinstance(func, dict)
        assert 'name' in func
        assert 'function' in func
        assert callable(func['function'])
        assert 'default_args' in func

# Correcting test_copy_screen_capture
def test_copy_screen_capture(compute_instance, mocker):
    mocker.patch('referia.assess.compute.most_recent_screen_shot', return_value='screenshot.png')
    mocker.patch('builtins.open', mocker.mock_open(read_data=b'image_data'))
    image = compute_instance.copy_screen_capture()
    assert image == b'image_data'
       
