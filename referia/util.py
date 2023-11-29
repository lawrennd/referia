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
    return input

def filename_to_binary(filename):
    """Convert a filename to a binary by loading it"""
    return open(filename, 'rb').read()

def yyyymmddToDatetime(string):
    """Convert from YYYY-MM-DD string to a datetime.datetime object."""
    if type(string) is str: 
        return datetime.strptime(string, "%Y-%m-%d")
    elif type(string) is pd.Timestamp:
        return string.date()

def datetimeToYyyymmdd(date):
    """Convert from YYYY-MM-DD string to a datetime.datetime object."""
    return datetime.strftime(date, "%Y-%m-%d")

def add_one_to_max(values=None, default=1):
    """Add one to the maximum value of a column."""
    if values is None:
        return default
    mv=values.max()
    if pd.isna(mv):
        return default
    else:
        return values.max() + 1

def markdown2html(text):
    return markdown.markdown(text)

def html2markdown(text, **args):
    return markdownify.markdownify(text, **args)

def renderable(view):
    """Check if a field is rendarable"""
    valid_views = ["display", "liquid", "join", "list", "compute"]
    for v in valid_views:
        if v in view:
            return True
    return False

def tallyable(view):
    """Check if a field is rendarable"""
    valid_views = ["tally"]
    for v in valid_views:
        if v in view:
            return True
    return False


def notempty(val):
    return pd.notna(val) and val!=""
                                
def draft_combinator(fieldname, columns):
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
    print("mapping:")
    for column in columns:
        print("  {field}: {fieldContent}".format(field=to_camel_case(column), fieldContent=column))          
    
def draft_skills(dtypes, width="800px"):
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
    return max(lst, key=len)

def return_shortest(lst):
    return min(lst, key=len)
