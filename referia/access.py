import os
import glob

import sys
import re
import tempfile

import yaml

import frontmatter

import numpy as np
import pandas as pd

from .util import extract_full_filename
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

    
def read_yaml(details):
    """Read data from a yaml file."""
    filename = extract_full_filename(details)
    data =  read_yaml_file(filename)
    return pd.DataFrame(data)

def write_yaml(df, details):
    """Write data to a yaml file."""
    filename = extract_full_filename(details)
    write_yaml_file(df.to_dict("records"), filename)
    
def read_directory(details, read_file=None, read_file_args={}, default_glob="*"):
    """Read scoring data from a directory of files."""
    filenames = []
    dirnames = []
    if "source" in details:
        sources = details["source"]
        if type(sources) is not list:
            sources = [sources]

        for source in sources:
            if "glob" in source:
                glob_text = source["glob"]
            else:
                glob_text = default_glob

            if "directory" in source:
                directory = os.path.expandvars(source["directory"])
            else:
                directory = "."
            globname = os.path.join(
                directory,
                glob_text,
            )
            log.info(f"Reading directory \"{globname}\"")
            newfiles = glob.glob(globname)
            newdirs = [directory]*len(newfiles)
            if len(newfiles) == 0:
                log.warning(f"No files match \"{globname}\"")
            if "regexp" in source:
                regexp = source["regexp"]
                addfiles = []
                adddirs = []
                for filename, dirname in zip(newfiles, newdirs):
                    if re.match(regexp, os.path.basename(filename)):
                        addfiles.append(filename)
                        adddirs.append(dirname)
                if len(addfiles) == 0:
                    log.warning(f"No files match \"regexp\"")
            else:
                addfiles = newfiles
                adddirs = newdirs
            filenames += addfiles
            dirnames += adddirs
    if len(filenames) == 0:
        log.warning(f"No files in \"{sources}\"")
        
    filenames.sort()
    data = []
    for filename, dirname in zip(filenames, dirnames):
        if read_file is None:
            data.append({})
        else:
            data.append(read_file(filename, **read_file_args))
        split_path = os.path.split(filename)
        if not os.path.exists(filename):
            log.warning(f"File \"{filename}\" is not a file or a directory.")
        if "sourceRoot" not in data[-1]:
            data[-1]["sourceRoot"] = dirname
        if "sourceDirectory" not in data[-1]:
            data[-1]["sourceDirectory"] = split_path[0]
        if "sourceFilename" not in data[-1]:
            data[-1]["sourceFilename"] = split_path[1]
    return pd.json_normalize(data)

def write_directory(df, details, write_file=None, write_file_args={}):
    """Write scoring data to a directory of files."""
    
    if "directory" in details:
        directory = os.path.expandvars(details["directory"])
    else:
        directory = "."

    if "sourceRoot" not in df:
        df["sourceRoot"] = directory
    if not os.path.exists(directory):
        os.makedirs(directory)
                
    if "filename" in details:
        filename_column = details["filename"]
    else: 
        filename_column = "sourceFilename"
    
    for index, row in df.iterrows():
        filename = os.path.join(directory, row[filename_column])
        row_dict = row.to_dict()        
        write_file(row_dict, filename, **write_file_args)
        
def read_yaml_file(filename):
    """Read a yaml file and return a python dictionary."""
    with open(filename, "r") as stream:
        try:
            log.info(f"Reading yaml file \"{filename}\"")
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            log.warning(exc)
            data = {}
    return data

def write_yaml_file(data, filename):
    """Write a yaml file from a python dictionary."""
    with open(filename, "w") as stream:
        try:
            log.info(f"Writing yaml file {filename}")
            yaml.dump(data, stream, sort_keys=False)
        except yaml.YAMLError as exc:
            log.warning(exc)

def read_yaml_meta_file(filename):
    """Read meta information associated with a file as a yaml and return a python dictionary if it exists."""
    metafile = filename + ".yml"
    if os.path.exists(metafile):
        return read_yaml_file(metafile)
    else:
        return {}

def write_yaml_meta_file(data, filename):
    """Write meta information associated with a file to a yaml."""
    metafile = filename + ".yml"
    write_yaml_file(data, metafile)

    
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
            log.warning(exc)
            data = {}
            
    return data

def write_markdown_file(data, filename, include_content=True, content="content"):
    """Write a markdown file from a python dictionary"""
    if include_content and content in data:
        write_data = {key: item for (key, item) in data.items() if key != content}
        content = data[content]
    else:
        write_data = data
        content = ""
    log.info(f"Writing markdown file \"{filename}\"")
    post = frontmatter.Post(content, **write_data)
    with open(filename, "wb") as stream:
        frontmatter.dump(post, stream, sort_keys=False)



def read_excel(details):
    """Read data from an excel spreadsheet."""
    dtypes = extract_dtypes(details)
    filename = extract_full_filename(details)
    log.info(f"Reading excel file \"{filename}\"")
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
        datetime_format="YYYY-MM-DD HH:MM:SS.000"
    )
    sheet_name=details["sheet"]
    df.to_excel(
        writer,
        sheet_name=sheet_name,
        startrow=details["header"],
        index=False
    )
    writer.close()
    
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


directory_readers = [
    {
        "default_glob": "*.yaml",
        "read_file": read_yaml_file,
        "name": "read_yaml_directory",
        "docstr": "Read a directory of yaml files.",
    },
    {
        "default_glob": "*.md",
        "read_file": read_markdown_file,
        "name": "read_markdown_directory",
        "docstr": "Read a directory of markdown files.",
    },
    {
        "default_glob": "*",
        "read_file": None,
        "name": "read_plain_directory",
        "docstr": "Read a directory of files.",
    },
    {
        "default_glob": "*",
        "read_file": read_yaml_meta_file,
        "name": "read_meta_directory",
        "docstr": "Read a directory of files.",
    },
]

directory_writers =[
    {
        "write_file": write_yaml_file,
        "name": "write_yaml_directory",
        "docstr": "Write a directory of yaml files.",
    },
    {
        "write_file": write_markdown_file,
        "name": "write_markdown_directory",
        "docstr": "Write a directory of markdown files.",
    },
    {
        "write_file": write_yaml_meta_file,
        "name": "write_meta_directory",
        "docstr": "Write a directory of markdown files.",
    },
]

def gdrf_(default_glob, read_file, name="", docstr=""):
    """Function generator for different directory readers."""
    def directory_reader(details):
        globname = None
        if "glob" in details:
            globname = details["glob"]
        if globname is None or globname == "":
            globname = default_glob
        return read_directory(
            details=details,
            read_file=read_file,
            default_glob=globname,
        )
            
    directory_reader.__name__ = name
    directory_reader.__docstr__ = docstr
    return directory_reader

def gdwf_(write_file, name="", docstr=""):
    """Function generator for different directory writers."""
    def directory_writer(df, details):
        return write_directory(
            df=df,
            details=details,
            write_file=write_file,
        )
    directory_writer.__name__ = name
    directory_writer.__docstr__ = docstr
    return directory_writer

def populate_directory_readers(readers):
    """populate_directory_readers: automatically create functions for reading directories."""
    this_module = sys.modules[__name__]
    for reader in readers:
        setattr(
            this_module,
            reader["name"],
            gdrf_(**reader),
        )
def populate_directory_writers(writers):
    """populate_directory_readers: automatically create functions for reading directories."""
    this_module = sys.modules[__name__]
    for writer in writers:
        setattr(
            this_module,
            writer["name"],
            gdwf_(**writer),
        )

populate_directory_readers(directory_readers)
populate_directory_writers(directory_writers)

def read_data(details):
    """Read in the data from the details given in configuration."""
    if "type" in details:
        ftype = details["type"]
    else:
        log.error("Field \"type\" missing in data source details for read_data.")
        return
    
    if ftype == "excel":
        df = read_excel(details)
    elif ftype == "gsheet":
        df = read_gsheet(details)
    elif ftype == "yaml":
        df = read_yaml(details)
    elif ftype == "yaml_directory":
        df = read_yaml_directory(details)
    elif ftype == "markdown_directory":
        df = read_markdown_directory(details)
    elif ftype == "directory":
        df = read_plain_directory(details)
    elif ftype == "meta_directory":
        df = read_meta_directory(details)
    else:
        log.error("Unknown type \"{ftype}\" in read_data.")

    return df

def allocation():
    """Load in the allocation spread sheet to data frames."""
    return read_data(config["allocation"])

def data_exists(details):
    """Check if a particular data structure exists or needs to be created."""
    if "filename" in details:
        filename = extract_full_filename(details)
        if os.path.exists(filename):
            return True
        else:
            return False
    if details["type"] in "gsheet":
        raise NotImplementedError("Haven't yet implemented check for existence fo particular google sheets.")

    if "source" in details:
        sources = details["source"]
        available = True
        if type(sources) is not list:
            sources = [sources]
        for source in sources:
            directory = source["directory"]
            if not os.path.exists(directory):
                log.error("Missing directory \"{directory}\".")
                available = False
        return available

    else:
        log.error("Unhandled data source availability type.")
        return False

def scores(index=None):
    """Load in the scoring spread sheet to data frames."""
    scores = config["scores"]
    if data_exists(scores):
        return read_data(scores)
    elif index is not None:
        log.info(f"Creating new DataFrame for write data from index as \"{scores}\" is not found.")
        return pd.DataFrame(index=index, data=index)
    else:
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT), filename
            )


def series(index=None):
    """Load in a series to data frame"""
    series = config["series"]
    if data_exists(series):
        return read_data(series)
    elif index is not None:
        log.info(f"Creating new DataFrame for write data from index as \"{series}\" is not found.")
        return pd.DataFrame(index=index, data=index)
    else:
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT), series
            )

def additional(source):
    """Load in the additional spread sheet to data frames."""
    return read_data(source)

def write_data(df, details):
    """Write the data using the details given in configuration."""
    if "type" in details:
        ftype = details["type"]
    else:
        log.error("Field \"type\" missing in data source details for write_data.")
        return
    if ftype == "excel":
        write_excel(df, details)
    elif ftype == "gsheet":
        write_gsheet(df, details)
    elif ftype == "gsheet":
        write_gsheet(df, details)
    elif ftype == "yaml":
        write_yaml(df, details)
    elif ftype == "yaml_directory":
        write_yaml_directory(df, details)
    elif ftype == "markdown_directory":
        write_markdown_directory(df, details)
    elif ftype == "meta_directory":
        write_meta_directory(df, details)
    else:
        log.error("Unknown type \"{ftype}\" in read_data.")


def write_scores(df):
    """Write the scoring spread sheet to data frames."""
    write_df = pd.concat([pd.Series(list(df.index), index=df.index, name=df.index.name), df], axis=1)    
    write_data(write_df, config["scores"])

def write_series(df):
    """Load in the series spread sheet to data frames."""
    write_df = pd.concat([pd.Series(list(df.index), index=df.index, name=df.index.name), df], axis=1)    
    write_data(write_df, config["series"])

