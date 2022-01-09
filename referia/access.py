import os
import glob

import sys
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
    """Read scoring data from a yaml file."""
    filename = os.path.join(
        os.path.expandvars(details["directory"]),
        details["filename"],
    )
    data =  read_yaml_file(filename)
    return finalize_df(data, details)
    

def read_directory(details, read_file, read_file_args={}, default_glob="*.yaml"):
    """Read scoring data from a directory of yaml files."""
    if "glob" in details:
        glob_text = details["glob"]
    else:
        glob_text = default_glob

    globname = os.path.join(
        os.path.expandvars(details["directory"]),
        glob_text,
    )
    filenames = glob.glob(globname)

    log.info(f"Reading directory {globname}")
    data = []
    for filename in filenames:
        data.append(read_file(filename, **read_file_args))
        data[-1]["source_filename"] = filename
    return finalize_df(pd.json_normalize(data), details)

def read_moodle_directory(details):
    """Read scoring data from a directory of yaml files."""
    glob_text = "Participant_*_assignsubmission_file_"
    globname = os.path.join(
        os.path.expandvars(details["directory"]),
        glob_text,
    )
    directorynames = glob.glob(globname)

    # log.info(f"Reading directory {globname}")
    # data = []
    # for filename in filenames:
    #     data.append(read_file(filename, **read_file_args))
    #     data[-1]["source_filename"] = filename
    # return finalize_df(pd.json_normalize(data), details)

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
    return finalize_df(data, details)

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
        return finalize_df(data, details)
    

def finalize_df(df, details):
    """for field in dtypes:
        if dtypes[field] is str_type:
            data[field].fillna("", inplace=True)"""
    df.set_index(df[details["index"]], inplace=True)
    return df


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
    if details["type"] == "excel":
        return read_excel(details)
    elif details["type"] == "gsheet":
        return read_gsheet(details)
    elif details["type"] == "yaml":
        return read_yaml(details)
    elif details["type"] == "yaml_directory":
        return read_directory(
            details=details,
            read_file=read_yaml_file,
            default_glob="*.yaml",
                              )
    elif details["type"] == "moodle_directory":
        return read_moodle_directory(
            details=details,
        )
    elif details["type"] == "markdown":
        return read_markdown(details)
    elif details["type"] == "markdown_directory":
        return read_directory(
            details=details,
            read_file=read_markdown_file,
            default_glob="*.md"
                              )
    
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


def additional():
    """Load in the additional spread sheet to data frames."""
    if type(config["additional"]) is list:
        for i, source in enumerate(config["additional"]):
            if i == 0:
                additional = read_data(source)
            else:
                additional = additional.join(read_data(source), rsuffix="_" + str(i))
    else:
        additional = read_data(config["additional"])

    return additional
    
def write_scores(df):
    """Load in the scoring spread sheet to data frames."""
    if config["scores"]["type"] == "excel":
        write_excel(df, config["scores"])
    elif config["scores"]["type"] == "gsheet":
        write_gsheet(df, config["scores"])
