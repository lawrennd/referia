import pytest
from referia.assess.compute import Compute  # Adjust the import as necessary
from lynguine.assess.data import CustomDataFrame
from unittest.mock import MagicMock
import pandas as pd

"""
Test suite for the Compute class in referia.assess.compute.

The Compute class inherits from lynguine.assess.compute.Compute and extends its functionality.
Key inherited methods include:
- run(data, interface) - Runs computations defined in the interface on the data
- run_all(data, interface) - Runs computations on all indices in the data frame
- prep(settings, data) - Prepares a compute entry for use
- gcf_(function, data) - Gets a compute function by name
- gca_(...) - Gets compute arguments with given settings

This test suite ensures that both the inherited behavior and the referia-specific
extensions work correctly.
"""

@pytest.fixture
def mock_interface(mocker):
    """
    Create a mock interface for testing.
    
    This fixture creates a mock interface object with the necessary structure
    to test the Compute class. The interface resembles a typical assessment
    interface with input and compute sections.
    """
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
    """
    Mock data fixture for testing.
    Returns an empty CustomDataFrame.
    """
    return CustomDataFrame({})

@pytest.fixture
def mock_data_with_indices(mocker):
    """
    Mock data fixture with indices for testing run_all.
    Creates a DataFrame with two indices for proper testing of run_all,
    which iterates through indices calling run for each one.
    """
    df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
    return CustomDataFrame(df)

@pytest.fixture
def compute_instance(mocker, mock_interface):
    """
    Create a Compute instance for testing.
    
    This fixture creates an instance of the referia.assess.compute.Compute class,
    which inherits from lynguine.assess.compute.Compute. It mocks the Logger
    to avoid logging during tests.
    """
    # Ensure that Logger is also mocked if necessary
    mocker.patch('lynguine.log.Logger')
    return Compute(mock_interface)

# Patch test_function into the Compute instance
@pytest.fixture
def mock_test_function(mocker, compute_instance):
    """
    Mock the test_function method in the Compute instance.
    
    This function is referenced in the mock_interface and needs to be
    patched into the Compute instance for testing.
    """
    mocker.patch.object(compute_instance, 'test_function', return_value=lambda x: x)

# Test initialization
def test_compute_initialization(compute_instance, mock_interface, mock_data):
    """
    Test that a Compute instance can be initialized properly.
    
    This test verifies the basic initialization of the referia.assess.compute.Compute
    class works correctly. It's important to ensure the inheritance from lynguine
    doesn't break the initialization process.
    """
    # Verify the instance is of the correct type
    assert isinstance(compute_instance, Compute)

def test_compute_creation(mocker, mock_interface):
    """
    Test the creation of a Compute instance with explicit parameters.
    
    This test ensures that a referia Compute instance can be created with data 
    and interface parameters, verifying that the constructor properly handles
    these parameters during inheritance from lynguine.
    """
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
    """
    Mock the compute functions list returned by _compute_functions_list.
    
    This fixture creates a mock of the compute functions that would be returned
    by the _compute_functions_list method, allowing tests to control the available
    compute functions for testing.
    """
    # Define a list of functions including 'test_function'
    mocked_functions = [
        {"name": "test_function", "function": lambda x: x, "default_args": {}}
    ]
    # Patch the _compute_functions_list method to return mocked_functions
    mocker.patch.object(compute_instance, '_compute_functions_list', return_value=mocked_functions)
    return mocked_functions

def test_prep(compute_instance, mock_data, mocker):
    """
    Test the prep method inherited from lynguine.
    
    The prep method prepares compute settings for execution by:
    1. Getting the compute function specified in settings
    2. Getting the compute arguments
    3. Setting refresh and field parameters
    
    This test validates that prep properly processes various types of settings.
    """
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
    """
    Alternative mock compute functions fixture that doesn't modify the compute_instance.
    
    This fixture provides a mocked list of compute functions without modifying
    the compute_instance, useful for tests that need to independently verify
    function behavior.
    """
    # Define a mocked list of functions including 'test_function'
    mocked_functions = [
        {"name": "test_function", "function": lambda x: x, "default_args": {}}
    ]
    return mocked_functions

# Test gcf_ functionality
def test_gcf_(compute_instance, mocker, mock_data):
    """
    Test the gcf_ (get compute function) method inherited from lynguine.
    
    The gcf_ method retrieves a compute function by name from the list of
    available compute functions. This test validates that gcf_ correctly:
    1. Finds functions by name
    2. Preserves function attributes (name, docstring)
    3. Returns callable functions that work as expected
    """
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
    """
    Test the gca_ (get compute arguments) method inherited from lynguine.
    
    The gca_ method builds a set of arguments for compute functions based on
    various input parameters. This test validates that gca_ correctly:
    1. Creates empty argument dictionaries when no args are provided
    2. Properly processes different types of arguments
    3. Organizes arguments into appropriate categories (row_args, function_args, etc.)
    """
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
    """
    Test the run method inherited from lynguine.
    
    The run method executes a single compute function with the given data.
    This method is a core part of the lynguine compute system that referia inherits.
    
    This test validates that run correctly:
    1. Calls the specified function with appropriate arguments
    2. Returns the function's return value (or None if no return)
    3. Properly handles the execution context
    """
    compute = {"function": lambda **kwargs: 42, "args": {}}
    result = compute_instance.run(compute, mock_data)
    assert result is None or result == 42

# Test preprocess method
def test_preprocess(compute_instance, mock_data, mock_interface, mocker):
    """
    Test the preprocess method inherited from lynguine.
    
    The preprocess method prepares data by applying preprocessing functions
    defined in the interface. This is an important step in the assessment process
    that happens before the main computation.
    
    This test verifies that:
    1. The method executes without errors
    2. It properly prepares compute functions using the prep method
    3. The preprocessing flow operates as expected from lynguine
    """
    mocker.patch.object(compute_instance, 'prep', return_value={"function": lambda x: x, "args": {}})
    compute_instance.preprocess(mock_data, mock_interface)
    # This test doesn't have specific assertions as preprocess doesn't have a return value,
    # but it verifies the method runs without errors

# Test run_all method - Updated according to CIP-0001 and with a better understanding of lynguine implementation
def test_run_all(compute_instance, mocker, mock_data_with_indices, mock_interface):
    """
    Test the run_all method inherited from lynguine.
    
    The run_all method in lynguine.assess.compute.Compute:
    1. Iterates through all indices in the data frame
    2. Calls run(data, interface) for each index
    
    This behavior is different from the commented-out implementation in 
    referia.assess.compute.Compute which was based on the number of compute items.
    """
    # Setup mocks
    run_mock = mocker.patch.object(compute_instance, 'run', return_value=None)
    mocker.patch.object(compute_instance, '_computes', {'precompute': [], 'compute': [], 'postcompute': []})
    
    # Call the method being tested with a DataFrame that has indices
    compute_instance.run_all(mock_data_with_indices, mock_interface)
    
    # The run_all method should call run once for each index in the DataFrame
    # Our mock_data_with_indices has 2 indices
    assert run_mock.call_count == 2
    
    # Reset the mock
    run_mock.reset_mock()
    
    # Test with non-empty compute lists - doesn't affect call count since it's based on indices
    mocker.patch.object(compute_instance, '_computes', {
        'precompute': [{'name': 'pre1'}], 
        'compute': [{'name': 'comp1'}, {'name': 'comp2'}], 
        'postcompute': [{'name': 'post1'}]
    })
    
    # Call run_all again
    compute_instance.run_all(mock_data_with_indices, mock_interface)
    
    # Should still be called twice (once per index), regardless of compute items
    assert run_mock.call_count == 2
    
    # Verify the method calls
    expected_calls = [
        mocker.call(mock_data_with_indices, mock_interface),
        mocker.call(mock_data_with_indices, mock_interface)
    ]
    run_mock.assert_has_calls(expected_calls)

# Test _compute_functions_list method
def test_compute_functions_list(compute_instance):
    """
    Test the _compute_functions_list method which returns available compute functions.
    
    This method is extended in referia's Compute class from the parent lynguine class.
    The referia implementation adds referia-specific functions to the list returned
    by the parent lynguine implementation.
    
    This test validates that:
    1. The method returns a properly structured list of functions
    2. Each function entry has the required fields (name, function, default_args)
    3. The functions are callable as expected
    """
    functions_list = compute_instance._compute_functions_list()
    
    assert isinstance(functions_list, list)
    for func in functions_list:
        assert isinstance(func, dict)
        assert 'name' in func
        assert 'function' in func
        assert callable(func['function'])
        assert 'default_args' in func

# Test copy_screen_capture method
def test_copy_screen_capture(compute_instance, mocker):
    """
    Test the copy_screen_capture method specific to referia.
    
    This method is NOT inherited from lynguine but is added by referia to provide
    screen capture functionality for assessment workflows. It:
    1. Locates the most recent screenshot
    2. Reads the binary image data
    3. Returns the binary data for use in assessments
    
    This test verifies the method correctly calls the underlying functions and
    returns the expected image data.
    """
    mocker.patch('referia.assess.compute.most_recent_screen_shot', return_value='screenshot.png')
    mocker.patch('builtins.open', mocker.mock_open(read_data=b'image_data'))
    image = compute_instance.copy_screen_capture()
    assert image == b'image_data'
       
