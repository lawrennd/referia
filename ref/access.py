import os
import sys
import pandas as pd
from .config import *

# This file accesses the data

"""Place commands in this file to access the data electronically. Don't remove any missing values, or deal with outliers. Make sure you have legalities correct, both intellectual property and personal data privacy rights. Beyond the legal side also think about the ethical issues around this data. """


def read_excel(details):
    """Read scoring data from an excel spreadsheet."""
    data =  pd.read_excel(
        os.path.expandvars(
            os.path.join(details["directory"],
                         details["filename"])),
        sheet_name=details["sheet"],
        converters=details["converters"],
        header=details["header"]
    )
    for key in CONVERTERS:
        if key in data.columns:
            data[key].fillna('', inplace=True)
    return data
    

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
    
