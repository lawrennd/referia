# tests/test_assess_data.py

import pytest
import referia.assess.data
import pandas as pd
import numpy as np
import lynguine

from deepdiff import DeepDiff

# Utility function to create test DataFrames
def create_test_dataframe(colspecs="data"):
    return referia.assess.data.CustomDataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]}, colspecs=colspecs)

def create_test_dataframe2(colspecs="data"):
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]}, index=[3, 4, 5])
    return referia.assess.data.CustomDataFrame(df, colspecs=colspecs)

def create_merged_dataframe():
    # Sample data for creating a CustomDataFrame instance
    data = {"A": [1, 2], "B": [3, 4], "C": [5, 5], "D": [6, 6], "E": [7, 7], "F": [8, 8]}
    colspecs = {"data": ["A", "B"], "writedata": ["C", "D"], "globals": ["E", "F"]}
    
    return referia.assess.data.CustomDataFrame(data, colspecs=colspecs)
    
def create_series_dataframe():
    # Sample data for creating a CustomDataFrame instance
    data = {"A": [1, 2], "B": [3, 4], "C": [5, 5], "D": [6, 6], "E": [7, 7], "F": [8, 8]}
    colspecs = {"input": ["A", "B"], "output": ["C", "D"], "writeseries": ["E", "F"]}
    
    return lynguine.assess.data.CustomDataFrame(data, colspecs=colspecs)

# Basic Functionality
def test_dataframe_creation():
    df = create_test_dataframe()
    assert isinstance(df, referia.assess.data.CustomDataFrame)
    assert df.shape == (3, 2)

def test_column_access():
    df = create_test_dataframe()
    assert all(df['A'] == pd.Series(data=[1, 2, 3], index=df.index, name="A"))

def test_row_access():
    df = create_test_dataframe()
    assert all(df.loc[0] == [1, 4])

# Mathematical Operations
def test_sum():
    df = create_test_dataframe()
    assert df.sum().equals(referia.assess.data.CustomDataFrame({'A': 6, 'B': 15}))

def test_mean():
    df = create_test_dataframe()
    assert df.mean().equals(referia.assess.data.CustomDataFrame({'A': 2.0, 'B': 5.0}))

# Merging and Joining
def test_concat():
    df1 = create_test_dataframe()
    df2 = create_test_dataframe()
    result = lynguine.assess.data.concat([df1, df2])
    # Because the two dataframes have the same indices
    assert list(result.colspecs.keys()) == ["series_cache"]
    assert result.colspecs["series_cache"] == ["A", "B"]
    assert result.shape == (3, 2) # TK Assuming we are counting one row per index.

    df2 = create_test_dataframe2()
    result = lynguine.assess.data.concat([df1, df2])
    # Because the two dataframes have different indices
    assert list(result.colspecs.keys()) == ["cache"]
    assert result.colspecs["cache"] == ["A", "B"]
    assert result.shape == (6, 2) 

def test_merge():
    df1 = referia.assess.data.CustomDataFrame({'key': ['K0', 'K1', 'K2'], 'A': ['A0', 'A1', 'A2']}, colspecs="input")
    df2 = referia.assess.data.CustomDataFrame({'key': ['K0', 'K1', 'K2'], 'A': ['A0', 'A1', 'A2'], 'B': ["B0", "B1", "B2"]}, colspecs="output")
    
    result = df1.merge(df2, on='key')
    assert result.equals(referia.assess.data.CustomDataFrame({'key': ['K0', 'K1', 'K2'], 'A_x': ['A0', 'A1', 'A2'], 'A_y': ['A0', 'A1', 'A2'], 'B': ['B0', 'B1', 'B2']}))
    diff = DeepDiff(result.colspecs, {"input" : ["key", "A_x"], "output" : ["A_y", "B"]})
    assert not diff, "The column specifications don't match in merge"

# test join
def test_join():
    df1 = referia.assess.data.CustomDataFrame({'key': ['K0', 'K1', 'K2'], 'A': ['A0', 'A1', 'A2']}, colspecs="input")
    df2 = referia.assess.data.CustomDataFrame({'key': ['K0', 'K1', 'K2'], 'A': ['A0', 'A1', 'A2'], 'B': ["B0", "B1", "B2"]}, colspecs="output")
    
    result = df1.join(df2, lsuffix="_1", rsuffix="_2")
    assert result.equals(referia.assess.data.CustomDataFrame({'key_1': ['K0', 'K1', 'K2'], 'A_1': ['A0', 'A1', 'A2'], 'key_2': ['K0', 'K1', 'K2'], 'A_2': ['A0', 'A1', 'A2'], 'B': ['B0', 'B1', 'B2']}))
    diff = DeepDiff(result.colspecs, {"input" : ["key_1", "A_1"], "output" : ["key_2", "A_2", "B"]})
    assert not diff, "The column specifications don't match in merge"
    
# Grouping and Sorting
def test_groupby_sum():
    df = referia.assess.data.CustomDataFrame({'A': ['foo', 'bar', 'foo', 'bar'], 'B': [1, 2, 3, 4]})
    grouped = df.groupby('A').sum()
    assert grouped.equals(pd.DataFrame({'B': [6, 4]}, index=pd.Index(['bar', 'foo'], name="A")))

def test_sort_values():
    df = create_test_dataframe()
    sorted_df = df.sort_values(by='B', ascending=False)
    assert sorted_df.equals(referia.assess.data.CustomDataFrame(pd.DataFrame({'A': [3, 2, 1], 'B': [6, 5, 4]}, index=sorted_df.index)))

# I/O Operations (Example: CSV)
def test_to_csv(tmpdir):
    df = create_test_dataframe()
    file_path = tmpdir.join('test.csv')
    df.to_csv(file_path)
    loaded_df = referia.assess.data.CustomDataFrame.from_csv(file_path, index_col=0)
    assert df.equals(loaded_df)

# Handling Missing Data
def test_fillna():
    df = referia.assess.data.CustomDataFrame({'A': [1, np.nan, 2], 'B': [np.nan, 2, 3]})
    filled_df = df.fillna(0)
    assert filled_df.equals(referia.assess.data.CustomDataFrame(pd.DataFrame({'A': [1.0, 0.0, 2.0], 'B': [0.0, 2.0, 3.0]}, index=df.index)))

# Advanced Features (Example: Pivot Table)
def test_pivot_table():
    df = referia.assess.data.CustomDataFrame({'A': ['foo', 'foo', 'foo', 'bar', 'bar', 'bar'],
                         'B': ['one', 'one', 'two', 'two', 'one', 'one'],
                         'C': np.random.randn(6),
                         'D': np.random.randn(6)})
    table = df.pivot_table(values='D', index=['A', 'B'], columns=['C'])
    assert isinstance(table, referia.assess.data.CustomDataFrame)
    diff = DeepDiff(table.to_pandas(), df.to_pandas().pivot_table(values="D", index=["A", "B"], columns=["C"]))
    assert not diff, "DataFrames don't match in pivot_table"
    
# Edge Cases and Error Handling
def test_invalid_data_creation():
    with pytest.raises(ValueError):
        df = referia.assess.data.CustomDataFrame({'A': [1, 2], 'B': [3, 4, 5]})

# Test get_selectors()
def test_get_selectors():
    custom_df = create_merged_dataframe()
    assert custom_df.get_selectors() == []

    custom_df = create_series_dataframe()
    assert custom_df.get_selectors() == ["E", "F"]


# Test loc accessor
def test_loc_accessor():
    # Test accessing and setting multiple elements
    custom_df = create_merged_dataframe()
    custom_df.loc[0, ["C", "D"]] = [10, 20]
    assert all(custom_df.loc[0, ["C", "D"]] == [10, 20])

    # Test accessing 'parameters' type data
    assert custom_df.loc[0, "E"] == 7

    # Test error when modifying 'parameters' with different values
    with pytest.raises(ValueError):
        custom_df.loc[:, "E"] = [2, 3]

    # Test setting value in 'output' type
    custom_df.loc[1, "C"] = 30
    assert custom_df.loc[1, "C"] == 30

    # Test error when modifying 'input' type
    with pytest.raises(KeyError):
        custom_df.loc[0, "A"] = 50

# Test iloc accessor
def test_iloc_accessor():
    # Test accessing multiple elements by integer location
    custom_df = create_merged_dataframe()
    assert all(custom_df.iloc[0, [2, 3]] == [10, 20])

    # Test error on invalid index
    with pytest.raises(IndexError):
        _ = custom_df.iloc[2, 0]

    # Test accessing 'parameters' type data
    assert custom_df.iloc[1, 4] == 7

    # Test error when modifying 'parameters' with different values
    with pytest.raises(ValueError):
        custom_df.iloc[:, 4] = [2, 3]

    # Test setting value in 'output' type
    custom_df.iloc[1, 2] = 30
    assert custom_df.loc[1, "C"] == 30

    # Test error when modifying 'input' type
    with pytest.raises(KeyError):
        custom_df.iloc[0, 0] = 50
        

# Test at accessor
def test_at_accessor():
    # Test accessing single element
    custom_df = create_merged_dataframe()
    assert custom_df.at[0, "A"] == 1

    # Test setting single element in 'output' type
    custom_df.at[1, "C"] = 40
    assert custom_df.at[1, "C"] == 40

    # Test error when modifying 'input' type
    with pytest.raises(KeyError):
        custom_df.at[0, "B"] = 60


def test_iloc():
    df = create_test_dataframe()
    assert df.iloc[1].equals(referia.assess.data.CustomDataFrame(pd.DataFrame({'A': 2, 'B': 5}, index=df.index[1:2])))

def test_boolean_indexing():
    df = create_test_dataframe()
    result = df[df['A'] > 1]
    assert result.equals(referia.assess.data.CustomDataFrame(pd.DataFrame({'A': [2, 3], 'B': [5, 6]}, index=result.index)))

# Handling Time Series Data
def test_time_series_indexing():
    time_index = pd.date_range('2020-01-01', periods=3)
    df = referia.assess.data.CustomDataFrame(pd.DataFrame({'A': [1, 2, 3]}, index=time_index))
    result = df.loc['2020-01']
    assert len(result) == 3  # Assuming daily data for January 2020

# Data Cleaning
def test_drop_duplicates():
    df = referia.assess.data.CustomDataFrame({'A': [1, 1, 2], 'B': [3, 3, 4]})
    result = df.drop_duplicates()
    assert result.equals(referia.assess.data.CustomDataFrame(pd.DataFrame({'A': [1, 2], 'B': [3, 4]}, index=result.index)))

# Performance Testing
@pytest.mark.slow
def test_large_dataframe_performance():
    large_df = referia.assess.data.CustomDataFrame({'A': range(1000000)})
    result = large_df.sum()
    # Include some form of performance assertion or benchmarking here

# Compatibility with Pandas
def test_compatibility_with_pandas():
    pandas_df = pd.DataFrame({'A': [1, 2, 3]})
    ndl_df = referia.assess.data.CustomDataFrame({'A': [1, 2, 3]})
    assert pandas_df.equals(ndl_df.to_pandas())  # Assuming to_pandas() converts lynguine DataFrame to Pandas DataFrame

# Testing for Exceptions
def test_out_of_bounds_access():
    df = create_test_dataframe()
    with pytest.raises(IndexError):
        _ = df.iloc[10]


# Test __len__ with different sizes of data
def test_len_empty_df():
    data = {}  # Assuming empty DataFrame
    custom_df = referia.assess.data.CustomDataFrame(data)
    assert len(custom_df) == 0

def test_len_non_empty_df():
    data = {"col1": [1, 2, 3], "col2": [4, 5, 6]}
    custom_df = referia.assess.data.CustomDataFrame(data)
    assert len(custom_df) == 3

def test_len_single_row_df():
    data = {"col1": [1], "col2": [2]}
    custom_df = referia.assess.data.CustomDataFrame(data)
    assert len(custom_df) == 1

def test_len_with_series_data():
    data = {"col1": pd.Series([1, 2, 3]), "col2": pd.Series([4, 5, 6])}
    custom_df = referia.assess.data.CustomDataFrame(data)
    assert len(custom_df) == 3

def test_len_with_mixed_data_types():
    data = {
        "col1": [1, 2, 3],
        "col2": pd.Series([4, 5, 6]),
        "col3": ["two", "four", "six"],
    }
    custom_df = referia.assess.data.CustomDataFrame(data)
    assert len(custom_df) == 3

@pytest.fixture
def valid_local_settings():
    # Return a sample interface object that is valid
    return referia.config.interface.Interface(
        {
            "input":
            {
                "type" : "local",
                "index" : "index",
                "data" : [
                    {
                        'index': 'indexValue',
                        'key1': 'value1',
                        'key2': 'value2',
                        'key3': 'value3',
                    }],
                "select" : 'indexValue'
            },
        },
        user_file="test.yml",
        directory="."
    )
@pytest.fixture
def valid_local_select_settings():
    # Return a sample interface object that is valid
    return referia.config.interface.Interface(
        {
            "parameters":
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
            }
        },
        user_file="test.yml",
        directory="."
    )

    
# test from_flow with a valid setting that specifies local data.
def test_from_flow_with_valid_settings(valid_local_settings):
    cdf = referia.assess.data.CustomDataFrame.from_flow(valid_local_settings)
    assert isinstance(cdf, referia.assess.data.CustomDataFrame)
    assert cdf == referia.assess.data.CustomDataFrame(pd.DataFrame({'key1': 'value1', 'key2' : 'value2', 'key3': 'value3'}, index=['indexValue']))
    assert cdf.colspecs == {"input" : ["key1", "key2", "key3"]}

# test from_flow with a valid setting that specifies local data.
def test_from_flow_with_valid_select_settings(valid_local_select_settings):
    cdf = referia.assess.data.CustomDataFrame.from_flow(valid_local_select_settings)
    assert isinstance(cdf, referia.assess.data.CustomDataFrame)
    assert cdf == referia.assess.data.CustomDataFrame(pd.DataFrame({'key1': 'value1row2', 'key2' : 'value2row2', 'key3': 'value3row2'}, index=[0]))
    assert cdf.colspecs == {"parameters" : ["key1", "key2", "key3"]}
    
def test_from_flow_with_invalid_type():
    with pytest.raises(ValueError):
        referia.assess.data.CustomDataFrame.from_flow("not-a-dictionary")

def test_from_flow_with_missing_keys():
    incomplete_settings = referia.config.interface.Interface(
        {
            # Settings with missing keys
            "key1": "value1",
        },
        user_file="test.yml",
        directory="."
    )
    with pytest.raises(ValueError):
        referia.assess.data.CustomDataFrame.from_flow(incomplete_settings)

def test_from_flow_with_empty_settings():
    cdf = referia.assess.data.CustomDataFrame.from_flow(
        referia.config.interface.Interface(
            {
                "globals":
                {
                    "type" : "local",
                    "data" : {},
                    "index" : "index"
                }
            },
            user_file="test.yml",
            directory="."
        )
    )
    # Assert the result is as expected (empty dataframe, etc.)
    assert isinstance(cdf, referia.assess.data.CustomDataFrame)
    assert cdf.empty

@pytest.fixture
def local_name_inputs():

    input_yaml_text="""input:
  type: local
  index: fullName
  data:
  - familyName: Xing
    givenName: Pei
  - familyName: Venkatasubramanian
    givenName: Siva
  - familyName: Paz Luiz
    givenName: Miguel
  compute:
    field: fullName
    function: render_liquid
    args:
      template: '{{familyName | replace: " ", "-"}}_{{givenName | replace: " ", "-"}}'
    row_args:
      givenName: givenName
      familyName: familyName"""
    # Read in dictionaary from yaml text
    input_dict = yaml.safe_load(input_yaml_text)
    return lynguine.config.interface.Interface(input_dict, user_file="test.yml", directory=".")
@pytest.fixture
def valid_local_input_compute_settings():
    # Return a sample interface object that is valid
    return referia.config.interface.Interface(
        {
            "input":
            {
                "type" : "local",
                "index" : "index",
                "data" : [
                    {
                        'givenName': 'Jim',
                        'familyName': 'Gonzalez',
                        'title': 'Professor',
                    }],
                "compute" : [
                    {
                        'field': index,
                        'function' : render_liquid,
                        'args' : {
                            'template' : '{{givenName}}_{{familyName}}',
                        }
                    }],
            }
        },
        user_file="test.yml",
        directory="."
    )
# test from_flow with a valid setting that specifies local data and a compute field
def test_from_flow_with_valid_settings(valid_local_settings):
    cdf = referia.assess.data.CustomDataFrame.from_flow(valid_local_settings)
    assert isinstance(cdf, referia.assess.data.CustomDataFrame)
    assert cdf == referia.assess.data.CustomDataFrame(pd.DataFrame({'key1': 'value1', 'key2' : 'value2', 'key3': 'value3'}, index=['indexValue']))
    assert cdf.colspecs == {"input" : ["key1", "key2", "key3"]}
    
# Test the to_score() method 
#def test_data_scored_count():
#    # Create a CustomDataFrame object
#    cdf = 

       # The number of scored elements is the number of filed in maching "scored:field" in the interface
