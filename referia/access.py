import os
import glob

import sys
import re
import tempfile

import yaml

import frontmatter

import numpy as np
import pandas as pd

    
from .log import Logger
from .config import *

try:
    import gspread_pandas as gspd
except ImportError:
    GSPREAD_AVAILABLE=False
# This file accesses the data

"""Place commands in this file to access the data electronically. Don't remove any missing values, or deal with outliers. Make sure you have legalities correct, both intellectual property and personal data privacy rights. Beyond the legal side also think about the ethical issues around this data. """

log = Logger(
    name=__name__,
    level=config["logging"]["level"],
    filename=config["logging"]["filename"]
)


def str_type():
    return str

def bool_type():
    return pd.BooleanDtype()

def int_type():
    return pd.Int32Dtype()

def float_type():
    return pd.Float64Dtype()

def extract_dtypes(details):
    """Extract dtypes from directory."""
    dtypes = {}
    if "dtypes" in details:
        if details["dtypes"] is not None:
            for dtype in details["dtypes"]:
                dtypes[dtype["field"]] = globals()[dtype["type"]]()
    return dtypes

def extract_sheet(details, gsheet=True):
    """Extract the sheet name from details"""
    if "sheet" in details:
        return details["sheet"]
    else:
        if gsheet:
            return 0
        else:
            return None

def extract_full_filename(details):
    """Return the filename from the details of directory and filename"""
    if "directory" not in details or details["directory"] is None:
        return details["filename"]
    return os.path.join(
        os.path.expandvars(details["directory"]),
        details["filename"],
    )

    
def read_yaml(details):
    """Read data from a yaml file."""
    filename = os.path.join(
        os.path.expandvars(details["directory"]),
        details["filename"],
    )
    data =  read_yaml_file(filename)
    return data
    


def read_directory(details, read_file=None, read_file_args={}, default_glob="*.yaml"):
    """Read scoring data from a directory of files."""
    if "glob" in details:
        glob_text = details["glob"]
    else:
        glob_text = default_glob

    directory = os.path.expandvars(details["directory"])
    globname = os.path.join(
        directory,
        glob_text,
    )
    filenames = glob.glob(globname)
    if len(filenames) == 0:
        log.warning(f"No files in {globname}")
    
    log.info(f"Reading directory {globname}")
    data = []
    for filename in filenames:
        if read_file is None:
            data.append({})
        else:
            data.append(read_file(filename, **read_file_args))
        data[-1]["Source Root"] = directory
        if os.path.isdir(filename):
            data[-1]["Source Directory Name"] = os.path.basename(filename)
        elif os.path.isfile(filename):
            data[-1]["Source File Name"] = os.path.basename(filename)
        else:
            log.warning(f"File {filename} is not a file or a directory.")
    return pd.json_normalize(data)

        
def read_yaml_file(filename):
    """Read a yaml file and return a python dictionary."""
    with open(filename, "r") as stream:
        try:
            log.info(f"Reading yaml file {filename}")
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            data = {}
    return data

    
def read_markdown_file(filename, include_content=True):
    """Read a markdown file and return a python dictionary."""
    with open(filename, "r") as stream:
        try:
            log.info(f"Reading markdown file {filename}")
            post = frontmatter.load(stream)
            data = post.metadata
            if include_content:
                data["content"] = post.content
        except yaml.YAMLError as exc:
            print(exc)
            data = {}
            
    return data

def write_markdown_file(data, filename, include_content=True):
    """Read a markdown file and return a python dictionary."""
    if include_content:
        content = data["content"]
        del data["content"]
    else:
        with open(filename, "r") as stream:
            try:
                content = frontmatter.load(stream).content
            except yaml.YAMLError as exc:
                print(exc)
                content = ""
        
            
    log.info(f"Writing markdown file {filename}")
    post = frontmatter.Post(content, **data)
    with open(filename, "w") as stream:
        frontmatter.dump(post, stream)
            
    return data



def read_excel(details):
    """Read data from an excel spreadsheet."""
    dtypes = extract_dtypes(details)
    filename = extract_full_filename(details)
    log.info(f"Reading excel file {filename}")
    data =  pd.read_excel(
        filename,
        sheet_name=details["sheet"],
        dtype=dtypes,
        header=details["header"],
    )
    return data

if GSPREAD_AVAILABLE:
    def read_gsheet(details):
        """Read data from a Google sheet."""
        dtypes = extract_dtypes(details)
        filename = extract_full_filename(details)
        log.info(f"Reading Google sheet named {filename}")
        sheet = extract_sheet(details)
        gsheet = gspd.Spread(
            spread=filename,
            sheet=sheet,
            config=config["gspread_pandas"],
        )
        data= gsheet.sheet_to_df(
            index=None,
            header_rows=details["header"]+1,
            start_row=details["header"]+1,
        )
        return data
    



def write_excel(df, details):
    """Write data to an excel spreadsheet."""
    filename = extract_full_filename(details)
    log.info(f"Writing excel file {filename}")
        
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
    
if GSPREAD_AVAILABLE:
    def write_gsheet(df, details):
        """Read data from a Google sheet."""
        filename = extract_full_filename(details)
        sheet = extract_sheet(details)
        log.info(f"Writing Google sheet named {filename}")
        gsheet = gspd.Spread(
            spread=filename,
            sheet=sheet,
            create_spread=True,
            config=config["gspread_pandas"],
        )
        gsheet.df_to_sheet(
            df=df,
            index=False,
            headers=True,
            replace=True,
            sheet=sheet,
            start=(details["header"]+1,1),
        )

def read_data(details):
    globname = None
    if "glob" in details:
        globname = details["glob"]
    if details["type"] == "excel":
        df = read_excel(details)
    elif details["type"] == "gsheet":
        df = read_gsheet(details)
    elif details["type"] == "yaml":
        df = read_yaml(details)
    elif details["type"] == "markdown":
        df = read_markdown(details)
    elif details["type"] == "yaml_directory":
        if globname is None or globname == "":
            default_glob = "*.yaml"
        else:
            default_glob = globname
        df = read_directory(
            details=details,
            read_file=read_yaml_file,
            default_glob=default_glob,
        )
    elif details["type"] == "markdown_directory":
        if globname is None or globname == "":
            default_glob = "*.md"
        else:
            default_glob = globname
        df = read_directory(
            details=details,
            read_file=read_markdown_file,
            default_glob=globname,
        )
    elif details["type"] == "directory":
        if globname is None or globname == "":
            default_glob = "*"
        else:
            default_glob = globname
        df = read_directory(
            details=details,
            read_file=None,
            default_glob=globname,
        )

    return df

def allocation():
    """Load in the allocation spread sheet to data frames."""
    return read_data(config["allocation"])


def scores(index=None):
    """Load in the scoring spread sheet to data frames."""
    filename = extract_full_filename(config["scores"])
    if config["scores"]["type"] == "gsheet":
        return read_data(config["scores"])
    elif os.path.exists(filename):
        return read_data(config["scores"])
    elif index is not None:
        log.info(f"Creating new DataFrame for write data from index as {filename} is not found.")
        return pd.DataFrame(index=index, data=index)
    else:
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT), filename
            )


def series(source):
    """Load in a series to data frame"""
    filename = extract_full_filename(config["series"])
    if config["series"]["type"] == "gsheet":
        return read_data(config["series"])
    elif os.path.exists(filename):
        return read_data(config["series"])
    elif index is not None:
        log.info(f"Creating new DataFrame for write data from index as {filename} is not found.")
        return pd.DataFrame(index=index, data=index)
    else:
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT), filename
            )

def additional(source):
    """Load in the additional spread sheet to data frames."""
    return read_data(source)

def write_data(df, details):
    if details["type"] == "excel":
        write_excel(df, details)
    elif details["type"] == "gsheet":
        write_gsheet(df, details)


def write_scores(df):
    """Write the scoring spread sheet to data frames."""
    write_data(df, config["scores"])

def write_series(df):
    """Load in the series spread sheet to data frames."""
    write_data(df, config["series"])
