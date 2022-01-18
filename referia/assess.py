import os
import re

import json
import tempfile
from shutil import copy2
import filecmp

from unidecode import unidecode
import random
import string
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import Markdown, display
from ipywidgets import IntSlider, FloatSlider, Checkbox, Text, Textarea, Combobox, Dropdown, Label, Layout, HTML, HTMLMath, DatePicker
from ipywidgets import interact, interactive, fixed, interact_manual

from pandas.api.types import is_string_dtype, is_numeric_dtype

import pypdftk as tk

from .widgets import MyCheckbox, MyFileChooser
from .config import *
from .log import Logger
from .util import to_camel_case
from . import access

TMPPDFFILES={}
DATA = None
WRITEDATA = None
INDEX = None
INTERACT_ARGS = {}
COLUMN_NAMES = {}
DEFAULT_WRITEDF_VALS = pd.Series()
DEFAULT_WRITEDF_SOURCE = pd.Series()

interact_manual.opts["manual_name"] = "Save Score"

log = Logger(
    name=__name__,
    level=config["logging"]["level"],
    filename=config["logging"]["filename"]
)


def load_data():
    """Joint the two data together, the allocation and additional information."""
    global DATA
    global WRITEDATA
    DATA = access.allocation()
    if "additional" in config:
        additional = access.additional()
        log.info("Joining allocation and additional information.")
        DATA = DATA.join(additional, rsuffix="additional")

    # If sorting is requested do it here.
    if "sortby" in config and "field" in config["sortby"] and config["sortby"]["field"] in DATA:
        if "ascending" in config["sortby"]:
            ascending = config["sortby"]["ascending"]
        else:
            ascending=True
        field = field=config["sortby"]["field"]
        log.info(f"Sorting by \"{field}\"")
        DATA.sort_values(by=field, ascending=ascending, inplace=True)
    WRITEDATA = access.scores(DATA.index)

def data():
    global DATA
    load_data()
    return DATA

    
def clear_temp_files():
    delete_keys = []
    for filename, values in TMPPDFFILES.items():
        destname = os.path.join(values["tmpdirectory"], filename)
        delete_keys.append(filename)
        if os.path.exists(destname):
            log.info(f"Removing temporary file \"{filename}\".")
            os.remove(destname)

    for key in delete_keys:
        del TMPPDFFILES[key]

def open_localfile(filename):
    """Open a local file."""
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext == ".pdf":
        open_pdf(filename)
    elif ext == ".mp4":
        open_video(filename)
    elif ext == ".py":
        open_python(filename)
    elif ext == ".md" or ext == ".markdown":
        open_markdown(filename)
    else:
        log.info(f"Opening file \"{filename}\".")
        os.system(f"open --background \"{filename}\"")


def open_markdown(filename):
    """Use the system viewer to open a markdown file."""
    log.info(f"Opening file \"{filename}\".")
    os.system(f"open --background \"{filename}\"")

def open_python(filename):
    """Use the system viewer to open a python file."""
    log.info(f"Opening file \"{filename}\".")
    os.system(f"open --background \"{filename}\"")
    
def open_pdf(filename):
    """Use the system viewer to open a PDF."""
    log.info(f"Opening file \"{filename}\".")
    os.system(f"open --background \"{filename}\"")

def open_video(filename):
    """Use the system viewer to open a video."""
    log.info(f"Opening file \"{filename}\".")
    os.system(f"open --background \"{filename}\"")
    
def open_url(urlname):
    """Use the browser to open URL."""
    if "browser" in config:
        browser=config["browser"]
    else:
        browser="Google Chrome.app" 
    
    log.info(f"Opening url \"{urlname}\".")
    os.system(f"open -a \"{browser}\" --background \"{urlname}\"")

def notempty(val):
    return pd.notna(val) and val!=""

def empty(val):
    return pd.isna(val) or val==""

def copy_file(origfile, destfile, display):
    """Copy a file, or pages from it, for separate editing or viewing."""
    _, ext = os.path.splitext(origfile)
    ext = ext.lower()

    if os.path.exists(origfile):
        if ext == ".pdf" and "pages" in display and "first" in display["pages"] and "last" in display["pages"]:
            # Extract pages from a PDF
            firstpage = get_value(get_index(), display["pages"]["first"])
            lastpage = get_value(get_index(), display["pages"]["last"])
            if notempty(firstpage) and notempty(lastpage) and notempty(display["field"]):
                firstpage = int(firstpage)
                lastpage = int(lastpage)
                log.info(f"Extracting \"{destfile}\" from \"{origfile}\" pages {firstpage}-{lastpage}")
                tk.get_pages(
                    pdf_path=origfile,
                    ranges=[[firstpage,
                             lastpage]],
                    out_file=destfile,
                )
        else:
            log.info(f"Copying \"{origfile}\" to \"{destfile}\".")
            copy2(origfile, destfile)
    else:
        log.warning(f"Warning edit file \"{origfile}\" does not exist.")


def edit_files():
    """Use the system viewer to show a PDF containing relevant information to the assessment."""

    displays = []
    if "editpdf" in config:
        displays += config["editpdf"]
        
    for display in displays:
        if "field" in display:
            val = get_value(get_index(), display["field"])
        if type(val) is str:
            storedirectory = os.path.expandvars(display["storedirectory"])
            origfile = os.path.join(os.path.expandvars(display["sourcedirectory"]),val)
            editfilename = str(get_value(get_index(), config["allocation"]["index"])) + "_" + to_camel_case(display["field"]) + ".pdf"
            destfile = os.path.join(storedirectory,editfilename)
            if not os.path.exists(storedirectory):
                os.makedirs(storedirectory)
            if not os.path.exists(destfile):
                copy_file(origfile, destfile, display)
            open_localfile(destfile)


def view_directory(display):
    """View a directory containing relevant information to the assessment."""
    pass

def view_file(display):
    """View a file containing relevant information to the assessment."""
    filename = ""
    tmpname = ""
    val = get_value(get_index(), display["field"])
    if type(val) is str:
        filename = os.path.expandvars(os.path.join(display["directory"],val))
        tmpname = to_camel_case(display["field"])
    elif "file" in display:
        filename = os.path.expandvars(os.path.join(display["directory"], display["file"]))
    if os.path.exists(filename):
        _, ext = os.path.splitext(filename)
        if len(tmpname)>0:
            tmpdirectory = tempfile.gettempdir()
            destfile = str(get_value(get_index(), config["allocation"]["index"])) + "_" + tmpname + ext
            destname = os.path.join(tmpdirectory, destfile)
            if not os.path.exists(destname):
                log.debug(f"Copying \"{filename}\" to \"{destname}\".")
                copy2(filename, destname)
            TMPPDFFILES[destfile] = {
                "origfile": filename,
                "tmpdirectory": tmpdirectory,
            }
            open_localfile(destname)
        else:
            open_localfile(filename)
    else:
        log.warning(f"view_file \"{filename}\" does not exist.")
    
    
def view_files():
    """Use the system viewer to show a PDF containing relevant information to the assessment."""
    displays = []
    if "localpdf" in config:
        displays += config["localpdf"]
    if "localvideo" in config:
        displays += config["localvideo"]

    for display in displays:
        view_file(display)
            
                
def view_urls():
    """View any urls that are provided."""
    displays = []
    if "urls" in config:
        displays += config["urls"]
        
    for display in displays:
        if "url" in display:
            if "field" in display:
                val = get_value(get_index(), display["field"])
            else:
                val = None
            if "field" in display and type(val) is str:
                urlterm = val
            elif "display" in display:
                urlterm = view_to_text(display)
            else:
                urlterm = ""
            urlname = unidecode(display["url"] + urlterm.replace(" ", "%20"))
            open_url(urlname)


def view_series():
    clear_temp_files()
    view_files()
    view_urls()
    edit_files()
    display(Markdown(view_text()))

def automapping():
    """Generate dictionary of mapping between variable names and column names."""
    mapping = {}
    for column in columns:
        field = to_camel_case(column)
        mapping[field] = column

def mapping(mapping=None):
    """Generate dictionary of mapping between variable names and column values."""
    if mapping is None:
        if "mapping" in config:
            mapping = config["mapping"]
        else:
            mapping = automapping()
            
    format = {}
    for key, column in mapping.items():
        format[key] = get_value(get_index(), column)

    return format
    

def conditions(entry):
    
    show_display = True
    if "conditions" in entry:
        for condition in entry["conditions"]:
            if "present" in condition:
                if not condition["present"]["field"] in columns():
                    return False
                    
            if "equal" in condition:
                if not get_value(get_index(), condition["equal"]["field"]) == condition["equal"]["value"]:
                    return False
                    
    return True

def view_to_text(view):
    """Create the text of the view."""
    if "format" in view:
        format = mapping(view["format"])
    else:
        format = mapping()

    if conditions(view):
        return view["display"].format(**format)
    else:
        return ""
    
def viewer_to_text(key):
    """Create a formatted text output from a yaml entry with base text and format keys."""
    text = ""
    if key in config:
        for view in config[key]:
            text += view_to_text(view)
    return text



def view_text():
    """Text that views a a single record."""
    if "viewer" in config:
        return viewer_to_text("viewer")
    else:
        return ""

def view(data):
    """Provide a view of the data that allows the user to verify some aspect of its quality."""
    fig, ax = plt.subplots(figsize=(8, 5))
    data.hist('Score', bins=np.linspace(-.5, 12.5, 14), width=0.8, ax=ax)
    ax.set_xticks(range(0,13))


def extract_scorer(orig_score):
    """Interpret a scoring element from the yaml file and create the relevant widgets to be past to the interact command"""
    global WRITEDATA
    global COLUMN_NAMES
    interact_args = {}
    score = json.loads(json.dumps(orig_score))

    if score["type"] == "CriterionComment":
        prefix = score["prefix"]
        criterion = score["criterion"]
        if "width" in score:
            width = score["width"]
        else:
            width = "800px"
        criterion = {
            "field": "_" + prefix + " Criterion",
            "type": "HTML",
            "args": {
                "value": criterion,
                "layout": {"width": width},
            }
        }
        comment = {
            "field": prefix + " Comment",
            "type": "Textarea",
            "args": {
                "value": "",
                "description": "Comment",
                "layout": {"width": width},
            }
        }
        for sub_score in [criterion, comment]:
            interact_args = {**interact_args, **extract_scorer(sub_score)}
        return interact_args
        

    if score["type"] == "CriterionCommentRaisesMeetsLowers":
        criterioncomment = json.loads(json.dumps(score))
        criterioncomment["type"] = "CriterionComment"

        prefix = score["prefix"]
        expectation = {
            "field": prefix + " Expectation",
            "type": "Dropdown",
            "args": {
                "placeholder": "Against expectations",
                "options": [
                    "",
                    "Raises",
                    "Meets",
                    "Lowers",
                    ],
                "description": "Expectation",
            }
        }
        for sub_score in [criterioncomment, expectation]:
            interact_args = {**interact_args, **extract_scorer(sub_score)}
        return interact_args

    if score["type"] == "CriterionCommentRaisesMeetsLowersFlag":
        criterioncomment = json.loads(json.dumps(score))
        criterioncomment["type"] = "CriterionComment"

        prefix = score["prefix"]
        expectation = {
            "field": prefix + " Expectation",
            "type": "Dropdown",
            "args": {
                "placeholder": "Against expectations",
                "options": [
                    "",
                    "Raises",
                    "Meets",
                    "Lowers",
                    "Flag",
                    ],
                "value": "",
                "description": "Expectation",
            }
        }
        for sub_score in [criterioncomment, expectation]:
            interact_args = {**interact_args, **extract_scorer(sub_score)}
        return interact_args
    
    if score["type"] == "CriterionCommentScore":
        criterioncomment = json.loads(json.dumps(score))
        criterioncomment["type"] = "CriterionComment"
        if "width" in score:
            width = score["width"]
        else:
            width = "800px"

        prefix = score["prefix"]
        if "min" in score:
            minval = score["min"]
        else:
            minval = 0
        if "max" in score:
            maxval = score["max"]
        else:
            maxval = 10
        if "step" in score:
            step = score["step"]
        else:
            step = 1
        if "value" in score:
            value = score["value"]
        else:
            value = int(((maxval-minval)/2)/step)*step + minval

        score = {
            "field": prefix + " Score",
            "type": "FloatSlider",
            "args": {
                "min": minval,
                "max": maxval,
                "step": step,
                "value": value,
                "description": "Score",
                "layout": {"width": width},
            }
        }
        for sub_score in [criterioncomment, score]:
            interact_args = {**interact_args, **extract_scorer(sub_score)}
        return interact_args
    
    global_variables = globals()
    if "field" in score:
        name = clean_string(score["field"])
        COLUMN_NAMES[name] = score["field"]

        # Create an instance of the object to extract default value.
        DEFAULT_WRITEDF_VALS[score["field"]] = global_variables[score["type"]]().value
        if "value" in score:
            DEFAULT_WRITEDF_VALS[score["field"]] = score["value"]               
        if "args" in score and "value" in score["args"]:
            DEFAULT_WRITEDF_VALS[score["field"]] = score["args"]["value"]
        if "default" in score:
            if "source" in score["default"]:
                source = score["default"]["source"]
                if source in DATA.columns or source in WRITEDATA.columns:
                    DEFAULT_WRITEDF_SOURCE[score["field"]] = source
                else:
                    log.warning(f"Missing column \"{source}\" in DATA and WRITEDATA.")
            if "value" in score["default"]:
                DEFAULT_WRITEDF_VALS[score["field"]] = score["default"]["value"]
                
    else:
        # Field name is missing, generate a random one.
        name = "_" + "".join(random.choice(string.ascii_letters) for _ in range(39))
        COLUMN_NAMES[name] = name

    # Deal with HTML descriptions (setting them to blank if not set)
    if score["type"] in ["HTML", "HTMLMath"]:
        if "args" not in score:
            score["args"] = {"description": " "}
        else:
            if "description" not in score:
                score["args"]["description"] = " "

    if "source" in score:
        # Set arguments of widget from data fields if source is given
        if "args" in score["source"]:
            for arg, field in score["source"]["args"]:
                if arg not in score["args"]:
                    score["args"][arg] = get_value(get_index(), field)
        if "criterion" in score["source"]:
            criterion = score["source"]["criterion"]
            if "display" in criterion:
                score["criterion"] = criterion["display"].format(**mapping())
                                 
    # Set arguments of widget from data fields if appropriate.                
    global_variables = globals()
    if "layout" in score:
        score["args"]["layout"] = Layout(**score["layout"])
    elif score["type"] in global_variables:
        interact_args[name] = global_variables[score["type"]](**score["args"])
    else:
        raise Exception("Have not loaded " + score["type"] + " interaction type.")
    return interact_args

def clean_string(instring):
    return re.sub("\W+|^(?=\d)","_", instring)

def set_index(index):
    """Index setter"""
    global INDEX
    if index not in DATA.index:
        raise ValueError("Invalid index")
    else:
        INDEX = index
        log.info(f"Index {index} selected.")
        
def get_index():
    global INDEX
    return INDEX


def set_value(value, index, column):
    """Set a value to the write data frame"""    
    # If trying to set a numeric valued column's entry to a string, set the type of column to object.
    if column in DATA.columns:
        log.warning(f"Warning attempting to write to DATA.")
    
    if column not in WRITEDATA.columns:
        add_column(column)

    coltype = WRITEDATA.dtypes[column]
    if is_numeric_dtype(coltype) and is_string_dtype(type(value)):
        log.info(f"Changing column \"{column}\" type to 'object' due to string input.")
        WRITEDATA[column] = WRITEDATA[column].astype('object')

    WRITEDATA.at[get_index(), column] = value

def get_value(index, column):
    """Get a value from the data frame(s)"""
    if column in WRITEDATA.columns:
        return WRITEDATA.at[index, column]
    elif column in DATA.columns:
        return DATA.at[index, column]
    else:
        log.warning(f"\"{column}\" not in WRITEDATA or DATA returning \"None\"")
        return None
    
def add_column(column):
    if column not in WRITEDATA.columns:
        log.info(f"\"{column}\" not in write columns ... adding.")
        WRITEDATA[column] = None
    else:
        log.warning(f"\"{column}\" requested to be added to write data but already exists.")
        
        
def score(index=None, df=None, write_df=None):
    global DATA
    global INTERACT_ARGS
    if df is not None or write_df is not None:
        log.warning("Passing of data frames to score is deprecated. These values are not used.")
        
    if index is not None:
        set_index(index)

    INTERACT_ARGS = {}
    # Process the different scorers in from the _referia.yml file 
    if "scorer" in config:
        for score in config["scorer"]:
            INTERACT_ARGS = {**INTERACT_ARGS, **extract_scorer(score)}

    
    def update_df(progress_label, **kwargs):
        global WRITEDATA

        for key, value in kwargs.items():
            # fields starting with "_" are not transferred
            # (typically HTML widgets for prompting input)
            if key[0] != "_":
                set_value(value, get_index(), COLUMN_NAMES[key])

        if "timestamp_field" in config:
            timestamp_field = config["timestamp_field"]
        else:
            timestamp_field = "Timestamp"
        set_value(
            pd.to_datetime("today"),
            get_index(),
            timestamp_field
        )
        if "created_field" in config:
            created_field = config["created_field"]
        else:
            created_field = "Created"
        if created_field not in WRITEDATA.columns or empty(get_value(get_index(), created_field)):
            set_value(
                pd.to_datetime("today"),
                get_index(),
                created_field
            )
        if "combinator" in config:
            for view in config["combinator"]:
                if "field" in view:
                    set_value(
                        view_to_text(view),
                        get_index(),
                        view["field"]
                    )                    
                else:
                    log.error("Missing key 'field' in combinator view.")
            
        access.write_scores(WRITEDATA)

        


    def update_score_row(index):
        global DATA
        global WRITEDATA
        global INTERACT_ARGS
        global COLUMN_NAMES
        
        set_index(index)
        view_series()


        # Now update the widget entries with values from the WRITEDATA if they exist otherwise relevant column from DATA or otherwise set to default
        for key, widget in INTERACT_ARGS.items():
            if COLUMN_NAMES[key][0] != "_":
                if COLUMN_NAMES[key] not in DEFAULT_WRITEDF_VALS:
                    DEFAULT_WRITEDF_VALS[COLUMN_NAMES[key]] = None
                widget.value = DEFAULT_WRITEDF_VALS[COLUMN_NAMES[key]]
                # Take default from existing column in DATA
                if COLUMN_NAMES[key] in DEFAULT_WRITEDF_SOURCE:
                    dval = get_value(get_index(), DEFAULT_WRITEDF_SOURCE[COLUMN_NAMES[key]])
                    if notempty(dval):
                        widget.value = dval
                # Take default from existing column in WRITEDATA
                if COLUMN_NAMES[key] in WRITEDATA.columns:
                    dval = get_value(get_index(), COLUMN_NAMES[key])
                    if notempty(dval):
                        widget.value = dval
                else:
                    add_column(COLUMN_NAMES[key])

                    
        total = len(WRITEDATA.index)
        remain = total
        progress_label = fixed("None")
        if "scored" in config:
            if config["scored"]["field"] in WRITEDATA:
                scored = WRITEDATA[config["scored"]["field"]].count()
                remain -= scored
                perc=scored/total*100
                progress_label = Label(f"{remain} to go. Scored {scored} from {total} which is {perc:.3g}%")

        interact_args = {
            "progress_label": progress_label,
            **INTERACT_ARGS
        }

        interact_manual(
            update_df, 
            **interact_args
        )

            
    index_select=Dropdown(options=DATA.index, value=get_index())
    interact(update_score_row, index=index_select)
    

