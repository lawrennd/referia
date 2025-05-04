# tests/test_assess_data_compute.py
# integrated tests of data and compute

"""
Test suite for the integration of the Data and Compute functionalities.

This test suite focuses on how the CustomDataFrame and Compute classes work together,
particularly in data preparation and transformation through compute functions.
These tests validate that data can be properly transformed and augmented using
various compute functions, including liquid template rendering.
"""

import pytest
import referia.assess.data
import referia.config.interface
import yaml
import pandas as pd
import numpy as np
import datetime

from deepdiff import DeepDiff


    
@pytest.fixture
def valid_local_data():
    """
    Create a fixture with a valid Interface object containing local data and a compute definition.
    
    This fixture creates an Interface with:
    1. Local data with two rows and an index
    2. A compute definition that adds a 'today' field with the current date
    
    :return: A configured Interface object
    :rtype: referia.config.interface.Interface
    """
    # Return a sample interface object that is valid
    return referia.config.interface.Interface(
        {
            "allocation":
            {
                "type" : "local",
                "index" : "index",
                "select" : "indexValue2",
                "data" : [
                    {
                        'index': 'indexValue',
                        'key1': 'value1',
                        'key2': 'value2',
                        'key3': 'value3',
                    },
                    {
                        'index': 'indexValue2',
                        'key1': 'value1row2',
                        'key2': 'value2row2',
                        'key3': 'value3row2',
                    }],
                "compute" : {
                    "field" : "today",
                    "function" : "today",
                    "args" : {
                        "format" : "%d %B %Y",
                    }
                }
            }
        },
        directory=".",
        user_file="test.yml",
    )

@pytest.fixture
def local_name_inputs():
    """
    Create a fixture with an Interface object that uses liquid templates for name formatting.
    
    This fixture creates an Interface from YAML that:
    1. Contains local data with candidate information
    2. Has compute definitions that use liquid templates to format names
    3. Creates formatted fields for fullName and applicationPDF
    
    :return: A configured Interface object from YAML
    :rtype: referia.config.interface.Interface
    """
    input_yaml_text="""allocation:
  type: local
  index: fullName
  data:
  - familyName: Xing
    givenName: Pei
    candidateId: 71232344
  - familyName: Venkatasubramanian
    givenName: Siva
    candidateId: 71232345
  - familyName: Paz Luiz
    givenName: Miguel
    candidateId: 71232346
  compute:
  - field: fullName
    function: render_liquid
    args:
      template: '{{familyName | replace: " ", "-"}}_{{givenName | replace: " ", "-"}}'
    row_args:
      givenName: givenName
      familyName: familyName
  - field: applicationPDF
    function: render_liquid
    args:
      template: '{{familyName}}, {{givenName}} ({{candidateId}}).pdf'
    row_args:
      givenName: givenName
      familyName: familyName
      candidateId: candidateId
"""
    # Read in dictionary from yaml text
    return referia.config.interface.Interface.from_yaml(input_yaml_text)


# test from_flow with a valid setting that specifies local data.
def test_from_flow_with_compute(valid_local_data):
    """
    Test that CustomDataFrame.from_flow correctly applies compute functions.
    
    This test validates that:
    1. The from_flow method creates a CustomDataFrame
    2. The compute function 'today' is correctly applied to add a new column
    3. The resulting data structure has the expected format and content
    4. The colspecs property correctly identifies input columns
    
    :param valid_local_data: Fixture containing a valid Interface object
    :type valid_local_data: referia.config.interface.Interface
    """
    # Create a CustomDataFrame from the interface using from_flow
    cdf = referia.assess.data.CustomDataFrame.from_flow(valid_local_data)
    
    # Get today's date in the expected format for comparison
    today = datetime.datetime.now().strftime(format="%Y-%m-%d")
    
    # Verify basic instance type
    assert isinstance(cdf, referia.assess.data.CustomDataFrame), "Result should be a CustomDataFrame"
    
    # Verify the data content matches expectations
    expected_df = referia.assess.data.CustomDataFrame(
        pd.DataFrame([
            {'key1': 'value1', 'key2': 'value2', 'key3': 'value3', 'today': today}, 
            {'key1': 'value1row2', 'key2': 'value2row2', 'key3': 'value3row3', 'today': today}
        ], 
        index=pd.Index(['indexValue', 'indexValue2'], name='index'))
    )
    assert cdf == expected_df, "DataFrame content should match the expected data with today's date"
    
    # Verify the colspecs property is correctly set
    assert cdf.colspecs == {"input": ["key1", "key2", "key3", "today"]}, "Colspecs should include all input columns"


# test from_flow with a valid setting that specifies local data.
def test_from_flow_with_compute_liquid(local_name_inputs):
    """
    Test that CustomDataFrame.from_flow correctly applies liquid template compute functions.
    
    This test validates that:
    1. The from_flow method creates a CustomDataFrame
    2. The liquid template compute functions are correctly applied to format names
    3. The fullName field is used as the index and is correctly formatted
    4. The applicationPDF field is correctly generated using the template
    5. The colspecs property correctly identifies input columns
    
    :param local_name_inputs: Fixture containing an Interface with liquid template computations
    :type local_name_inputs: referia.config.interface.Interface
    """
    # Create a CustomDataFrame from the interface using from_flow
    cdf = referia.assess.data.CustomDataFrame.from_flow(local_name_inputs)
    
    # Verify basic instance type
    assert isinstance(cdf, referia.assess.data.CustomDataFrame), "Result should be a CustomDataFrame"
    
    # Verify the data content matches expectations
    expected_df = referia.assess.data.CustomDataFrame(
        pd.DataFrame([
            {'familyName': 'Xing', 'givenName': 'Pei', 'candidateId': '7123234', 'applicationPDF': 'Xing, Pei (7123234).pdf'}, 
            {'familyName': 'Venkatasubramanian', 'givenName': 'Siva', 'candidateId': '71232345', 'applicationPDF': 'Venkatasubramanian, Siva (71232345).pdf'}, 
            {'familyName': 'Paz Luiz', 'givenName': 'Miguel', 'candidateId': '71232346', 'applicationPDF': 'Paz Luiz, Miguel (71232346).pdf'}
        ], 
        index=pd.Index(['Xing_Pei', 'Venkatasubramanian_Siva', 'Paz-Luiz_Miguel'], name='fullName'))
    )
    assert cdf == expected_df, "DataFrame content should match the expected data with formatted names"
    
    # Verify the colspecs property is correctly set
    assert cdf.colspecs == {"input": ["familyName", "givenName", "candidateId", "applicationPDF"]}, "Colspecs should include all input columns"
    
    # Verify the space replacement in names worked correctly
    assert 'Paz-Luiz_Miguel' in cdf.index, "Space replacement should have worked in the fullName index"
