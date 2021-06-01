import os
import sys
from datetime import date
import re
import pandas as pd
from .config import *

# This file accesses the data

"""Place commands in this file to access the data electronically. Don't remove any missing values, or deal with outliers. Make sure you have legalities correct, both intellectual property and personal data privacy rights. Beyond the legal side also think about the ethical issues around this data. """


import clexp.expenses as exp

def outputs():
    """Load in the allocation spread sheet to data frames."""
    return pd.read_excel(os.path.expandvars(os.path.join(config['datadirectory'], config['allocation'])), sheet_name=config['outputs_sheet'], header=3)

def additional():
    return pd.read_excel(os.path.expandvars(os.path.join(config['datadirectory'], config['allocation'])), sheet_name=config['additional_data_sheet'], header=2)    
