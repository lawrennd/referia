import os
import sys
import pandas as pd
from .config import *

# This file accesses the data

"""Place commands in this file to access the data electronically. Don't remove any missing values, or deal with outliers. Make sure you have legalities correct, both intellectual property and personal data privacy rights. Beyond the legal side also think about the ethical issues around this data. """

def str_type(val):
    return str(val)

def read_excel(details):
    """Read scoring data from an excel spreadsheet."""
    converters = {}
    for converter in details["converters"]:
        converters[converter["field"]] = globals()[converter["type"]]
    data =  pd.read_excel(
        os.path.expandvars(
            os.path.join(details["directory"],
                         details["filename"])),
        sheet_name=details["sheet"],
        converters=converters,
        header=details["header"]
    )
    for field in converters:
        data[field].fillna("", inplace=True)
    data.set_index(data[details["index"]], inplace=True)
    return data
    

def write_excel(df, details):
    """Write data to an excel spreadsheet."""
    filename = os.path.expandvars(
        os.path.join(
            details["directory"], details["filename"]
        )
    )
        
    writer = pd.ExcelWriter(
        filename,
        engine="xlsxwriter",
        datetime_format="YYYY-MM-DD HH:MM:SS"
    )
    sheet_name=details["sheet"]
    df.to_excel(
        writer,
        sheet_name=sheet_name,
        startrow=details["header"],
        index=False
    )
    writer.save()
    

def allocation():
    """Load in the allocation spread sheet to data frames."""
    if config["allocation"]["type"] == "excel":
        data = read_excel(config["allocation"])
    return data 


def scores():
    """Load in the scoring spread sheet to data frames."""
    if config["scores"]["type"] == "excel":
        data = read_excel(config["scores"])
    return data 


def additional():
    """Load in the additional spread sheet to data frames."""
    if config["additional"]["type"] == "excel":
        data = read_excel(config["additional"])
    return data 
    
def write_scores(df):
    """Load in the scoring spread sheet to data frames."""
    if config["scores"]["type"] == "excel":
        data = write_excel(df, config["scores"])
    return data 
