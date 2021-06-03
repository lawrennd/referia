import os
import sys
import pandas as pd
from .config import *

# This file accesses the data

"""Place commands in this file to access the data electronically. Don't remove any missing values, or deal with outliers. Make sure you have legalities correct, both intellectual property and personal data privacy rights. Beyond the legal side also think about the ethical issues around this data. """

CONVERTERS = converters={'Comment':str,'Comment 2':str, 'Comment 4':str}

def outputs():
    """Load in the allocation spread sheet to data frames."""
    data =  pd.read_excel(os.path.expandvars(os.path.join(config['datadirectory'], config['allocation'])), sheet_name=config['outputs_sheet'], converters=CONVERTERS, header=3)
    for key in CONVERTERS:
        if key in data.columns:
            data[key].fillna('', inplace=True)	
    return data 

def upload():
    """Load in the upload spread sheet to data frames."""
    data =  pd.read_excel(os.path.expandvars(os.path.join(config['datadirectory'], config['upload'])), sheet_name=config['outputs_sheet'], converters=CONVERTERS, header=3)
    for key in CONVERTERS:
        if key in data.columns:
            data[key].fillna('', inplace=True)	
    return data 

def additional():
    
    data = pd.read_excel(os.path.expandvars(os.path.join(config['datadirectory'], config['allocation'])), sheet_name=config['additional_data_sheet'],  converters=CONVERTERS, header=2)    
    for key in CONVERTERS:
        if key in data.columns:
            data[key].fillna('', inplace=True)	
    return data
