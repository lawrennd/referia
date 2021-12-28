import os
import glob

import sys
import yaml

import frontmatter

import numpy as np
import pandas as pd
from .log import Logger
from .config import *

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

    log.info("Reading directory {globname}".format(globname=globname))
    data = []
    for filename in filenames:
        data.append(read_file(filename, **read_file_args))
        data[-1]["source_filename"] = filename
    return finalize_df(pd.json_normalize(data), details)

def read_yaml_file(filename):
    """Read a yaml file and return a python dictionary."""
    with open(filename, "r") as stream:
        try:
            log.info("Reading yaml file {filename}".format(filename=filename))
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            data = {}
    return data

def read_markdown_file(filename, include_content=True):
    """Read a markdown file and return a python dictionary."""
    with open(filename, "r") as stream:
        try:
            log.info("Reading markdown file {filename}".format(filename=filename))
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
        
            
    log.info("Writing markdown file {filename}".format(filename=filename))
    post = frontmatter.Post(content, **data)
    with open(filename, "w") as stream:
        frontmatter.dump(post, stream)
            
    return data


def read_excel(details):
    """Read scoring data from an excel spreadsheet."""
    dtypes = extract_dtypes(details)
    filename = os.path.join(
        os.path.expandvars(details["directory"]),
        details["filename"],
    )
    log.info("Reading excel file {filename}".format(filename=filename))
    data =  pd.read_excel(
        filename,
        sheet_name=details["sheet"],
        dtype=dtypes,
        header=details["header"]
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
    filename = os.path.join(
        os.path.expandvars(details["directory"]),
        details["filename"],
    )
    log.info("Writing excel file {filename}".format(filename=filename))
        
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
    

def read_data(details):
    if details["type"] == "excel":
        return read_excel(details)
    elif details["type"] == "yaml":
        return read_yaml(details)
    elif details["type"] == "yaml_directory":
        return read_directory(
            details=details,
            read_file=read_yaml_file,
            default_glob="*.yaml",
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


def scores():
    """Load in the scoring spread sheet to data frames."""
    return read_data(config["scores"])


def additional():
    """Load in the additional spread sheet to data frames."""
    return read_data(config["additional"])
    
def write_scores(df):
    """Load in the scoring spread sheet to data frames."""
    if config["scores"]["type"] == "excel":
        data = write_excel(df, config["scores"])
    return data 
