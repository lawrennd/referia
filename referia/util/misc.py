from datetime import datetime
import re

from pandas.api.types import is_bool_dtype, is_integer_dtype, is_float_dtype, is_string_dtype

import pandas as pd
import markdown
import markdownify

import wget

"""Utility functions for helping, e.g. to create the relevant yaml files quickly."""
# Identity function for testing 
def identity(input):
    """
    Identity function for testing

    :param input: The input to be returned.
    :type input: any
    :return: The input.
    """
    
    return input

def filename_to_binary(filename):
    """
    Convert a filename to a binary by loading it

    :param filename: The filename to be converted.
    :type filename: str
    :return: The binary.
    :rtype: bytes
    """
    return open(filename, 'rb').read()

def yyyymmddToDatetime(string):
    """
    Convert from YYYY-MM-DD string to a datetime.datetime object.

    :param string: The string to be converted.
    :type string: str
    :return: The datetime object.
    :rtype: datetime.datetime
    """
    if type(string) is str: 
        return datetime.strptime(string, "%Y-%m-%d")
    elif type(string) is pd.Timestamp:
        return string.to_pydatetime()

def datetimeToYyyymmdd(date):
    """
    Convert from YYYY-MM-DD string to a datetime.datetime object.

    :param date: The datetime object to be converted.
    :type date: datetime.datetime
    :return: The string.
    :rtype: str
    """
    return datetime.strftime(date, "%Y-%m-%d")

def add_one_to_max(values=None, default=1):
    """
    Add one to the maximum value of a column.

    :param values: The values to be used.
    :type values: pandas.Series
    :param default: The default value to be used if the maximum value is NaN.
    :type default: int
    :return: The maximum value plus one.
    :rtype: int
    """
    if values is None:
        return default
    mv=values.max()
    if pd.isna(mv):
        return default
    else:
        return values.max() + 1

def markdown2html(text):
    """
    Convert markdown to HTML.

    :param text: The markdown text to be converted.
    :type text: str
    :return: The HTML.
    :rtype: str
    """
    
    return markdown.markdown(text)

def html2markdown(text, **args):
    """
    Convert HTML to markdown.

    :param text: The HTML text to be converted.
    :type text: str
    :return: The markdown.
    :rtype: str
    """
    
    return markdownify.markdownify(text, **args)

def renderable(view):
    """
    Check if a field is rendarable

    :param view: The view to be checked.
    :type view: str
    :return: Whether the field is rendarable.
    :rtype: bool
    """
    valid_views = ["display", "liquid", "join", "list", "compute"]
    for v in valid_views:
        if v in view:
            return True
    return False

def tallyable(view):
    """
    Check if a field is tallyable

    :param view: The view to be checked.
    :type view: str
    :return: Whether the field is tallyable.
    :rtype: bool
    """
    valid_views = ["tally"]
    for v in valid_views:
        if v in view:
            return True
    return False

def notempty(val):
    """
    Check if a value is not empty

    :param val: The value to be checked.
    :type val: any
    :return: Whether the value is not empty.
    :rtype: bool
    """
    return pd.notna(val) and val!=""
                                
def draft_combinator(fieldname, columns):
    """
    Draft a combinator

    :param fieldname: The fieldname to be used.
    :type fieldname: str
    :param columns: The columns to be used.
    :type columns: list
    """
    
    print("combinator:")
    print("- field: {fieldname}".format(fieldname=fieldname))
    print("  display: \"")
    for column in columns:
        print("{fieldContent}: {o}{field}{c}\\n".format(field=to_camel_case(column), fieldContent=column, o ="{", c="}"))
    print("\"")
    print("  format:")
    for column in columns:
        print("    {field}: {fieldContent}".format(field=to_camel_case(column), fieldContent=column))


def mapping(fieldname, columns):
    """
    Draft a mapping

    :param fieldname: The fieldname to be used.
    :type fieldname: str
    :param columns: The columns to be used.
    :type columns: list
    """
    
    print("mapping:")
    for column in columns:
        print("  {field}: {fieldContent}".format(field=to_camel_case(column), fieldContent=column))          
    
def draft_skills(dtypes, width="800px"):
    """
    Draft a skills section

    :param dtypes: The dtypes to be used.
    :type dtypes: dict
    :param width: The width to be used.
    :type width: str
    """
    print("scorer:")
    for column, dtype in dtypes.items():
        print("""- type: HTML
  args:
    value: "<h3>{column}</h3>

<p></p>"
  layout:
    max_width: {width}
- field: "{column}" """.format(column=column, width=width))
        if is_string_dtype(dtype):
            print("""  type: Textarea
  args:
    value: ""
    description: "{column}"
  layout:
    max_width: {width}""".format(column=column, width=width))
        elif is_integer_dtype(dtype):
            print("""  type: IntSlider
  args:
    value: 0
    min: 0
    max: 5
    step: 1
    description: "{column}"
  layout:
    max_width: {width}""".format(column=column, width=width))  
        elif is_float_dtype(dtype):
            print("""  type: FloatSlider
  args:
    value: 0
    min: 0
    max: 5
    step: 0.5
    description: "{column}"
  layout:
    max_width: {width}""".format(column=column, width=width))  
        elif is_bool_dtype(dtype):
            print("""  type: MyCheckbox
  args:
    value: False
    description: "{column}" """.format(column=column))  
        
def return_longest(lst):
    """
    Return the longest string/list in a list

    :param lst: The list to be used.
    :type lst: list
    :return: The longest string.
    :rtype: str
    """
    
    return max(lst, key=len)

def return_shortest(lst):
    """
    Return the shortest string/list in a list

    :param lst: The list to be used.
    :type lst: list
    :return: The shortest string.
    :rtype: str
    """
    return min(lst, key=len)
