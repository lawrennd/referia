# tests/test_assess_data_compute.py
# integrated tests of data and compute

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
    # Return a sample interface object that is valid
    return referia.config.interface.Interface({
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
            
    })

@pytest.fixture
def local_name_inputs():

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
    # Read in dictionaary from yaml text
    return referia.config.interface.Interface.from_yaml(input_yaml_text)


# test from_flow with a valid setting that specifies local data.
def test_from_flow_with_compute(valid_local_data):
    cdf = referia.assess.data.CustomDataFrame.from_flow(valid_local_data)
    today = datetime.datetime.now().strftime(format="%Y-%m-%d")
    assert isinstance(cdf, referia.assess.data.CustomDataFrame)
    assert cdf == referia.assess.data.CustomDataFrame(pd.DataFrame([{'key1': 'value1', 'key2' : 'value2', 'key3': 'value3', 'today' : today}, {'key1': 'value1row2', 'key2' : 'value2row2', 'key3': 'value3row3', 'today' : today}], index=pd.Index(['indexValue', 'indexValue2'], name='index')))
    assert cdf.colspecs == {"input" : ["key1", "key2", "key3", "today"]}


# test from_flow with a valid setting that specifies local data.
def test_from_flow_with_compute_liquid(local_name_inputs):
    cdf = referia.assess.data.CustomDataFrame.from_flow(local_name_inputs)
    assert isinstance(cdf, referia.assess.data.CustomDataFrame)
    assert cdf == referia.assess.data.CustomDataFrame(pd.DataFrame([{'familyName': 'Xing', 'givenName' : 'Pei','candidateId' : '7123234', 'applicationPDF' : 'Xing, Pei (7123234).pdf'}, {'familyName': 'Venkatasubramanian', 'givenName' : 'Siva', 'candidateId' : '71232345', 'applicationPDF' : 'Venkatasubramanian, Siva (71232345).pdf'}, {'familyName': 'Paz Luiz', 'givenName' : 'Miguel', 'candidateId' : '71232346', 'applicationPDF' : 'Paz Luiz, Miguel (71232346).pdf'}], index=pd.Index(['Xing_Pei', 'Venkatasubramanian_Siva', 'Paz-Luiz_Miguel'], name='fullName')))
    assert cdf.colspecs == {"input" : ["familyName", "givenName", "candidateId", "applicationPDF"]}
