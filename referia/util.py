from pandas.api.types import is_bool_dtype, is_integer_dtype, is_float_dtype, is_string_dtype

import pandas as pd
import markdown
import os

"""Utility functions for helping, e.g. to create the relevant yaml files quickly."""

def markdown2html(text):
    return markdown.markdown(text)

def extract_full_filename(details):
    """Return the filename from the details of directory and filename"""
    if "directory" not in details or details["directory"] is None:
        return details["filename"]
    return os.path.join(
        os.path.expandvars(details["directory"]),
        details["filename"],
    )

def camel_capitalize(text):
    if text == text.upper():
        return text
    else:
        return text.capitalize()
    
def notempty(val):
    return pd.notna(val) and val!=""

def to_camel_case(text):
    """Remove non alpha-numeric characters and camelize capitalisation"""
    text = text.replace("/", " or ")
    text = text.replace("@", " at ")
    non_alpha_chars = set([ch for ch in set(list(text)) if not ch.isalnum()])
    if len(non_alpha_chars) > 0:
        for ch in non_alpha_chars:
            text = text.replace(ch, " ")
        s = text.split()
        if len(text) == 0:
            return A
        if s[0] == s[0].upper():
            start = s[0]
        else:
            start = s[0].lower()

        return start + ''.join(camel_capitalize(i) for i in s[1:])
    else:
        return text

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

          


        
