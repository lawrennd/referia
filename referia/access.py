import os
import glob

import sys
import re
import tempfile

import yaml
import json

import frontmatter

import pypandoc

import numpy as np
import pandas as pd

from .util import extract_full_filename, get_path_env, remove_nan
from .log import Logger
from .config import *

GSPREAD_AVAILABLE=True
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



class EnvTag(yaml.YAMLObject):
    yaml_tag = u'!ENV'

    def __init__(self, env_var):
        self.env_var = env_var

    def __repr__(self):
        v = os.environ.get(self.env_var) or ''
        return 'EnvTag({}, contains={})'.format(self.env_var, v)

    @classmethod
    def from_yaml(cls, loader, node):
        return EnvTag(node.value)

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar(cls.yaml_tag, data.env_var)

# Required for safe_load
yaml.SafeLoader.add_constructor('!ENV', EnvTag.from_yaml)
# Required for safe_dump
yaml.SafeDumper.add_multi_representer(EnvTag, EnvTag.to_yaml)


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

def read_json(details):
    """Read data from a json file."""
    filename = extract_full_filename(details)
    data = read_json_file(filename)
    return pd.DataFrame(data)

def write_json(df, details):
    """Write data to a json file."""
    filename = extract_full_filename(details)
    write_json_file(df.to_dict("records"), filename)
    
def read_yaml(details):
    """Read data from a yaml file."""
    filename = extract_full_filename(details)
    data =  read_yaml_file(filename)
    return pd.DataFrame(data)

def write_yaml(df, details):
    """Write data to a yaml file."""
    filename = extract_full_filename(details)
    write_yaml_file(df.to_dict("records"), filename)


def read_directory(details, read_file=None, read_file_args={}, default_glob="*", source=None):
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
            log.warning(f"No files in \"{sources}\".")
    else:
        log.warning(f"No source in \"{details}\".")
        
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
        root_field = details["store_fields"]["root"]
        directory_field = details["store_fields"]["directory"]
        filename_field = details["store_fields"]["filename"]
        if root_field not in data[-1]:
            data[-1][root_field] = get_path_env()
        if directory_field not in data[-1]:
            direc = split_path[0].replace(dirname, '')
            if direc == "": # ensure at least a "." for directory
                direc = "."
            data[-1][directory_field] = direc
        if filename_field not in data[-1]:
            data[-1][filename_field] = split_path[1]
    return pd.json_normalize(data)

def write_directory(df, details, write_file=None, write_file_args={}):
    """Write scoring data to a directory of files."""
    filename_field = details["store_fields"]["filename"]
    directory_field = details["store_fields"]["directory"]
    root_field = details["store_fields"]["root"]

    for index, row in df.iterrows():
        # Don't write a file that contains only nulls
        if not row.isnull().values.all():
            
            directoryname = os.path.expandvars(
                os.path.join(
                    row[root_field],
                    row[directory_field],
                )
            )
            if not os.path.exists(directoryname):
                os.makedirs(directoryname)

            fullfilename = os.path.join(directoryname, row[filename_field])
            row_dict = row.to_dict()
            row_dict = remove_empty(row_dict)
            write_file(row_dict, fullfilename, **write_file_args)

def remove_empty(row_dict):
    """Remove any empty fields in the dictionary to tidy up saved files."""
    delete_keys = []
    for key, item in row_dict.items():
        if type(item) is not list and pd.isna(item):
            delete_keys.append(key)

    for key in delete_keys:
        del row_dict[key]
    return row_dict

def read_json_file(filename):
    """Read a json file and return a python dictionary."""
    with open(filename, "r") as stream:
        try:
            log.info(f"Reading json file \"{filename}\"")
            data = json.load(stream)
        except json.JSONDecodeError as exc:
            log.warning(exc)
            data = {}
    return data

def write_json_file(data, filename):
    """Write a json file from a python dicitonary."""
    with open(filename, "w") as stream:
        try:
            log.info(f"Writing json file \"{filename}\".")
            json.dump(data, stream, sort_keys=False)
        except json.JSONDecodeError as exc:
            log.warning(exc)
            
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

def yaml_prep(data):
    """Prepare any fields for writing in yaml"""
    writedata = data.copy()
    if type(writedata) is list:
        for num, el in enumerate(writedata):
            writedata[num] = yaml_prep(el)
        return writedata
    
    for key, item in writedata.items():
        if pd.api.types.is_datetime64_dtype(item) or type(item) is pd.Timestamp:
            writedata[key] = item.strftime("%Y-%m-%d %H:%M:%S.%f")
    return writedata

    
def write_yaml_file(data, filename):
    """Write a yaml file from a python dictionary."""
    writedata = yaml_prep(data)
    with open(filename, "w") as stream:
        try:
            log.info(f"Writing yaml file \"{filename}\".")
            yaml.dump(writedata, stream, sort_keys=False)
        except yaml.YAMLError as exc:
            log.warning(exc)

def read_yaml_meta_file(filename):
    """Read meta information associated with a file as a yaml and return a python dictionary if it exists."""
    metafile = filename + ".yml"
    if os.path.exists(metafile):
        data = read_yaml_file(metafile)
    else:
        data = {}
    return data

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

def read_docx_file(filename, include_content=True):
    """Read information from a docx file."""
    directory = tempfile.gettempdir()
    tmpfile = os.path.join(directory, "tmp.md")
    extra_args = []
    extra_args.append("--standalone")
    pypandoc.convert_file(filename, "markdown", outputfile=tmpfile, extra_args=extra_args)
    data = read_markdown_file(tmpfile, include_content)
    return remove_nan(data)

def write_url_file(data, filename, content, include_content=True):
    """Write a url to a file"""
    # This is with writing links to prefilled google forms in mind.
    raise NotImplemented("The write url file function has not been implemented.")

def write_markdown_file(data, filename, content=None, include_content=True):
    """Write a markdown file from a python dictionary"""
    if content is None:
        if include_content and "content" in data:
            write_data = {key: item for (key, item) in data.items() if key != "content"}
            content = data["content"]
        else:
            if not include_content:
                content = ""
            write_data = data
    else:
        write_data = data.copy()
        if "content" in data:
            del write_data["content"]
    log.info(f"Writing markdown file \"{filename}\"")
    post = frontmatter.Post(content, **write_data)
    with open(filename, "wb") as stream:
        frontmatter.dump(post, stream, sort_keys=False)

def create_letter(document, **args):
    """Create a markdown letter."""
    data, filename, content = create_document_content(document, **args)
    access.write_letter_file(data=data, filename=filename, content=content)
    open_localfile(filename)
def write_letter_file(data, filename, content, include_content=True):
    """Write a letter file from a python dictionary"""
    if include_content and content in data:
        write_data = {key: item for (key, item) in data.items() if key != "content"}
        content = data[content]
    else:
        if not include_content:
            content = ""
        write_data = data
        
    log.info(f"Writing markdown letter file \"{filename}\"")
    post = frontmatter.Post(content, **write_data)
    with open(filename, "wb") as stream:
        frontmatter.dump(post, stream, sort_keys=False)

def create_letter(document, **args):
    """Create a markdown letter."""
    data, filename, content = create_document_content(document, **args)
    access.write_letter_file(data=data, filename=filename, content=content)
    open_localfile(filename)

def write_letter_file(data, filename, content, include_content=True):
    """Write a letter file from a python dictionary"""
    if include_content and content in data:
        write_data = {key: item for (key, item) in data.items() if key != "content"}
        content = data[content]
    else:
        if not include_content:
            content = ""
        write_data = data
        
    log.info(f"Writing markdown letter file \"{filename}\"")
    post = frontmatter.Post(content, **write_data)
    with open(filename, "wb") as stream:
        frontmatter.dump(post, stream, sort_keys=False)
        
def write_formlink(data, filename, content, include_content=True):
    """Write a url to prepopulate a Google form"""
    write_url_file(data, filename, content, include_content)
    
    
def write_docx_file(data, filename, content, include_content=True):
    """Write a docx file from a python dictionary."""
    directory = tempfile.gettempdir()
    tmpfile = os.path.join(directory, "tmp.md")
    write_markdown_file(data, tmpfile, content, include_content)
    log.info(f"Converting markdown file \"{tmpfile}\" to docx file \"{filename}\"")
    extra_args=[]
    if "reference-doc" in data:
        extra_args.append("--reference-doc=" + data["reference-doc"])
    pypandoc.convert_file(tmpfile, "docx", outputfile=filename, extra_args=extra_args)

    
def write_tex_file(data, filename, content, include_content=True):
    """Write a docx file from a python dictionary."""
    directory = tempfile.gettempdir()
    tmpfile = os.path.join(directory, "tmp.md")
    write_markdown_file(data, tmpfile, content, include_content)
    log.info(f"Converting markdown file \"{tmpfile}\" to tex file \"{filename}\"")
    extra_args=[]
    pypandoc.convert_file(tmpfile, "tex", outputfile=filename, extra_args=extra_args)
    
def read_csv(details):
    """Read data from a csv file."""
    dtypes = extract_dtypes(details)
    filename = extract_full_filename(details)
    if "header" in details:
        header = details["header"]
    else:
        header = 0

    if "delimiter" in details:
        delimiter = details["delimiter"]
    else:
        delimiter = ","

    if "quotechar" in details:
        quotechar = details["quotechar"]
    else:
        quotechar = "\""
    log.info(f"Reading csv file \"{filename}\" from row \"{header}\" with quote character {quotechar} and delimiter \"{delimiter}\"")
        
    data = pd.read_csv(
        filename,
        dtype=dtypes,
        header=header,
        delimiter=delimiter,
        quotechar=quotechar,
    )
    return data
    
def read_excel(details):
    """Read data from an excel spreadsheet."""
    dtypes = extract_dtypes(details)
    filename = extract_full_filename(details)
    if "header" in details:
        header = details["header"]
    else:
        header = 0

    if "sheet" in details:
        sheet_name = details["sheet"]
    else:
        sheet_name = "Sheet1"
    log.info(f"Reading excel file \"{filename}\" sheet \"{sheet_name}\" from row \"{header}\"")
        
    data =  pd.read_excel(
        filename,
        sheet_name=sheet_name,
        dtype=dtypes,
        header=header,
    )
    
    return data

if GSPREAD_AVAILABLE:
    def read_gsheet(details):
        """Read data from a Google sheet."""
        dtypes = extract_dtypes(details)
        filename = extract_full_filename(details)
        log.info(f"Reading Google sheet named {filename}")
        sheet = extract_sheet(details)
        gconfig = {}
        for key, val in config["google_oauth"].items():
            gconfig[key] = os.path.expandvars(val)
        gsheet = gspd.Spread(
            spread=filename,
            sheet=sheet,
            config=gconfig,
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
    if "header" in details:
        header = details["header"]
    else:
        header = 0

    if "sheet" in details:
        sheet_name = details["sheet"]
    else:
        sheet_name = "Sheet1"
    
    log.info(f"Writing excel file \"{filename}\" sheet \"{sheet_name}\" header at row \"{header}\".")
    
    writer = pd.ExcelWriter(
        filename,
        engine="xlsxwriter",
        datetime_format="YYYY-MM-DD HH:MM:SS.000"
    )
    sheet_name=details["sheet"]
    df.to_excel(
        writer,
        sheet_name=sheet_name,
        startrow=header,
        index=False
    )
    writer.close()

def write_csv(df, details):
    """Write data to an csv spreadsheet."""
    filename = extract_full_filename(details)
    if "delimiter" in details:
        delimiter = details["delimiter"]
    else:
        delimiter = ","

    if "quotechar" in details:
        quotechar = details["quotechar"]
    else:
        quotechar = "\""
    log.info(f"Writing csv file \"{filename}\" with quote character {quotechar} and delimiter \"{delimiter}\"")

    with open(filename, "w") as stream:
        df.to_csv(
            stream,
            sep=delimiter,
            quotechar=quotechar,
            header=True,
            index=False,
        )

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
        "default_glob": "*.yml",
        "read_file": read_yaml_file,
        "name": "read_yaml_directory",
        "docstr": "Read a directory of yaml files.",
    },
    {
        "default_glob": "*.json",
        "read_file": read_json_file,
        "name": "read_json_directory",
        "docstr": "Read a directory of json files.",
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
        "docstr": "Read a directory of yaml meta files.",
    },
    {
        "default_glob": "*.docx",
        "read_file": read_docx_file,
        "name": "read_docx_directory",
        "docstr": "Read a directory of word files.",
    },
]

directory_writers =[
    {
        "write_file": write_json_file,
        "name": "write_json_directory",
        "docstr": "Write a directory of json files.",
    },
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
        "docstr": "Write a directory of yaml meta files.",
    },
]

def gdrf_(default_glob, read_file, name="", docstr=""):
    """Function generator for different directory readers."""
    def directory_reader(details):
        details = update_store_fields(details)
        globname = None
        if "glob" in details:
            globname = details["glob"]
        if globname is None or globname == "":
            globname = default_glob
        if "source" in details:
            source = details["source"]
        else:
            source = None
        return read_directory(
            details=details,
            read_file=read_file,
            default_glob=globname,
            source=source,
        )
            
    directory_reader.__name__ = name
    directory_reader.__docstr__ = docstr
    return directory_reader

def update_store_fields(details):
    """Add default store fields values"""
    # TK: Perhaps this should be set in config defaults somewhere.
    # Extracts info about where the directory read file data is to be written.
    if "store_fields" not in details:
        details["store_fields"] = {
            "root": "sourceRoot",
            "directory": "sourceDirectory",
            "filename": "sourceFilename",
        }
    else:
        if "root" not in details["store_fields"]:
            details["store_fields"]["root"] =  "sourceRoot"
        if "directory" not in details["store_fields"]:
            details["store_fields"]["directory"] =  "sourceDirectory"
        if "filename" not in details["store_fields"]:
            details["store_fields"]["filename"] =  "sourceFilename"
    return details
    
def gdwf_(write_file, name="", docstr=""):
    """Function generator for different directory writers."""
    def directory_writer(df, details):
        details = update_store_fields(details)
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

def finalize_data(df, details):
    """Finalize the data frame by augmenting with any columns. """
    """Eventually this should do any augmentation that isn't required by the series. The problem is at the moment the liquid rendering (and other renderings) are too integrated with assess. They need to be pulled out and not so dependent on the data structure."""
    
    return df, details
    

def read_data(details):
    """Read in the data from the details given in configuration."""
    if "type" in details:
        ftype = details["type"]
    else:
        raise ValueError("Field \"type\" missing in data source details for read_data.")
    
    if ftype == "excel":
        df = read_excel(details)
    elif ftype == "gsheet":
        df = read_gsheet(details)
    elif ftype == "yaml":
        df = read_yaml(details)
    elif ftype == "csv":
        df = read_csv(details)
    elif ftype == "json":
        df = read_json(details)
    elif ftype == "yaml_directory":
        df = read_yaml_directory(details)
    elif ftype == "markdown_directory":
        df = read_markdown_directory(details)
    elif ftype == "directory":
        df = read_plain_directory(details)
    elif ftype == "meta_directory":
        df = read_meta_directory(details)
    elif ftype == "docx_directory":
        df = read_docx_directory(details)
    else:
        raise ValueError("Unknown type \"{ftype}\" in read_data.")

    return finalize_data(df, details)

def data_exists(details):
    """Check if a particular data structure exists or needs to be created."""
    if "filename" in details:
        filename = extract_full_filename(details)
        if os.path.exists(filename):
            return True
        else:
            return False
    if details["type"] == "gsheet":
        raise NotImplementedError("Haven't yet implemented check for existence fo particular google sheets.")

    if "source" in details:
        sources = details["source"]
        available = True
        if type(sources) is not list:
            sources = [sources]
        for source in sources:
            directory = source["directory"]
            if not os.path.exists(os.path.expandvars(directory)):
                log.error(f"Missing directory \"{directory}\".")
                available = False
        return available

    else:
        log.error("Unhandled data source availability type.")
        return False

def load_or_create_df(details, index):
    """Load in a data frame or create it if it doesn't exist yet."""
    if data_exists(details):
        return read_data(details)
    elif index is not None:
        log.info(f"Creating new DataFrame from index as \"{details}\" is not found.")
        if "columns" in details:
            df = pd.DataFrame(index=index, columns=[index.name] + details["columns"])
            df[index.name] = index
        else:
            df = pd.DataFrame(index=index, data=index)
        return finalize_data(df, details)
    else:
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT), filename
            )


def globals(details, index=None):
    """Load in the globals data to a data frame."""
    # don't do it in the standard way as we don't want the index to be a column
    if "index" in details:
        index_column_name = details["index"]
    else:
        index_column_name = "index"
    if data_exists(details):
        df, details = read_data(details)
        df.set_index(index_column_name, inplace=True)
        return df, details
    elif index is not None:
        log.info(f"Creating new globals DataFrame from index as \"{details}\" is not found.")
        if "columns" in details:
            df = pd.DataFrame(index=pd.Index(data=index, name=index_column_name), columns=details["columns"])
        else:
            raise ValueError(f"Field \"columns\" must be provided in globals.")
        return finalize_data(df, details)
    else:
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT), filename
            )
        
    return load_or_create_df(details, index)

def cache(details, index=None):
    """Load in the cache data to a data frame."""
    return load_or_create_df(details, index)
    
def scores(details, index=None):
    """Load in the score data to data frames."""
    return load_or_create_df(details, index)


def series(details, index=None):
    """Load in a series to data frame"""
    if data_exists(details):
        return read_data(details)
    elif index is not None:
        log.info(f"Creating new DataFrame for write data from index as \"{details}\" is not found.")
        return finalize_data(pd.DataFrame(index=index, data=index), details)
    else:
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT), details
            )


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
    elif ftype == "csv":
        write_csv(df, details)
    elif ftype == "json":
        write_json(df, details)
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


def convert_datetime_to_str(df):
    """Convert datetime columns to strings in isoformat for ease of writing."""
    write_df = df.copy(deep=True)
    for col in df.select_dtypes(include=['datetime64']).columns.tolist():
        date_series = pd.Series(index=df.index, name=col,dtype="object")
        for ind, val in df[col].items():
            if pd.isnull(val):
                date_series.at[ind] = None
            else:
                date_series.at[ind] = val.strftime("%Y-%m-%d %H:%M:%S.%f")
                
        write_df[col] = date_series
    return write_df


def write_globals(df, config):
    """Write the globals to a file."""
    write_df = pd.concat([pd.Series(list(df.index), index=df.index, name=df.index.name), df], axis=1)    
    write_data(write_df, config["globals"])

def write_cache(df, config):
    """Write the cache to a file."""
    write_df = pd.concat([pd.Series(list(df.index), index=df.index, name=df.index.name), df], axis=1)    
    write_data(write_df, config["cache"])
    
def write_scores(df, config):
    """Write the scoring data frame to a file."""
    write_df = pd.concat([pd.Series(list(df.index), index=df.index, name=df.index.name), df], axis=1)    
    write_data(write_df, config["scores"])
    
def write_series(df, config):
    """Load in the series data to a file."""
    write_df = pd.concat([pd.Series(list(df.index), index=df.index, name=df.index.name), df], axis=1)    
    write_data(write_df, config["series"])

