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
from ipywidgets import IntSlider, FloatSlider, Checkbox, Text, Textarea, Combobox, Dropdown, Label, Layout, HTML, HTMLMath
from ipywidgets import interact, interactive, fixed, interact_manual

from .widgets import MyCheckbox
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
        log.info("Sorting by {field}".format(field=config["sortby"]["field"]))
        DATA.sort_values(by=config["sortby"]["field"], ascending=ascending, inplace=True)
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
            log.info("Removing temporary file {filename}.".format(filename=destname))
            os.remove(destname)

    for key in delete_keys:
        del TMPPDFFILES[key]

def open_pdf(filename):
    """Use the system viewer to open a PDF."""
    log.info("Opening file {filename}.".format(filename=filename))
    os.system('open ' + '--background ' + '"' + filename + '"')

def open_url(urlname):
    """Use the browser to open URL."""
    if "browser" in config:
        browser=config["browser"]
    else:
        browser="Google Chrome.app" 
    
    log.info("Opening url {urlname}.".format(urlname=urlname))
    os.system('open ' + '-a "' + browser + '" --background ' + '"' + urlname + '"')

    
def edit_pdfs(ds):
    """Use the system viewer to show a PDF containing relevant information to the assessment."""

    if "editpdf" in config:
        for display in config["editpdf"]:
            if "field" in display and type(ds[display["field"]]) is str:
                storedirectory = os.path.expandvars(display["storedirectory"])
                origfile = os.path.join(os.path.expandvars(display["sourcedirectory"]),ds[display["field"]])
                editfilename = ds[config["allocation"]["index"]] + "_" + to_camel_case(display["field"]) + ".pdf"
                destfile = os.path.join(storedirectory,editfilename)
                if not os.path.exists(storedirectory):
                    os.makedirs(storedirectory)
                
                if not os.path.exists(destfile):
                    if os.path.exists(origfile):
                        log.debug("Copying {origfile} to {destfile}.".format(origfile=origfile, destfile=destfile))
                        copy2(origfile, destfile)
                    else:
                        log.warning("Warning editpdf {origfile} does not exist.".format(origfile=origfile))
                open_pdf(destfile)

def view_pdfs(ds):
    """Use the system viewer to show a PDF containing relevant information to the assessment."""

    if "localpdf" in config:
        for display in config["localpdf"]:
            filename = ""
            tmpname = ""
            if "field" in display and type(ds[display["field"]]) is str:
                filename = os.path.expandvars(os.path.join(display["directory"],ds[display["field"]]))
                tmpname = to_camel_case(display["field"])
            elif "file" in display:
                filename = os.path.expandvars(os.path.join(display["directory"], display["file"]))
            if os.path.exists(filename):
                if len(tmpname)>0:
                    tmpdirectory = tempfile.gettempdir()
                    destfile = ds[config["allocation"]["index"]] + "_" + tmpname + ".pdf"
                    destname = os.path.join(tmpdirectory, destfile)
                    if not os.path.exists(destname):
                        log.debug("Copying {origfile} to {destfile}.".format(origfile=filename, destfile=destname))
                        copy2(filename, destname)
                    TMPPDFFILES[destfile] = {
                        "origfile": filename,
                        "tmpdirectory": tmpdirectory,
                    }
                    open_pdf(destname)
                else:
                    open_pdf(filename)
            else:
                log.warning("localpdf {filename} does not exist.".format(filename=filename))

def view_urls(ds):
    if "urls" in config:
        for display in config["urls"]:
            if "url" in display:
                if "field" in display and type(ds[display["field"]]) is str:
                    urlterm = ds[display["field"]]
                elif "display" in display:
                    urlterm = view_to_text(display, ds)
                else:
                    urlterm = ""
                urlname = unidecode(display["url"] + urlterm.replace(" ", "%20"))
                open_url(urlname)


def view_series(ds):
    clear_temp_files()    
    view_pdfs(ds)
    edit_pdfs(ds)
    view_urls(ds)
    display(Markdown(view_text(ds)))


def view_to_text(view, ds):
    format = {}
    if "format" in view:
        for key, column in view["format"].items():
            format[key] = ds[column] 

    show_display = True
    if "conditions" in view:
        for condition in view["conditions"]:
            if "present" in condition:
                if not condition["present"]["field"] in ds:
                    show_display = False
                    break
            if "equal" in condition:
                if not ds[condition["equal"]["field"]] == condition["equal"]["value"]:
                    show_display = False
                    break
    if show_display:
        return view["display"].format(**format)
    else:
        return ""
    
def viewer_to_text(key, ds):
    """Create a formatted text output from a yaml entry with base text and format keys."""
    text = ""
    if key in config:
        for view in config[key]:
            text += view_to_text(view, ds)
    return text



def view_text(ds):
    """Text that views a a single record."""
    if "viewer" in config:
        return viewer_to_text("viewer", ds)
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
            "type": "Combobox",
            "args": {
                "placeholder": "Against expectations",
                "options": [
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
        if "args" in score and "value" in score["args"]:
            DEFAULT_WRITEDF_VALS[score["field"]] = score["args"]["value"]
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
        log.info("Index {index} selected.".format(index=index))
        
def get_index():
    global INDEX
    return INDEX

        
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
                if COLUMN_NAMES[key] in WRITEDATA.columns:
                    WRITEDATA.at[get_index(), COLUMN_NAMES[key]] = value
                else:
                    log.info("{field} not in write columns ... adding.".format(field=COLUMN_NAMES[key]))
                    WRITEDATA[COLUMN_NAMES[key]] = None
                    WRITEDATA.at[get_index(), COLUMN_NAMES[key]] = value

        if "timestamp_field" in config:
            timestamp_field = config["timestamp_field"]
        else:
            timestamp_field = "Timestamp"
        WRITEDATA.at[get_index(), timestamp_field] = pd.to_datetime("today")
        if "created_field" in config:
            created_field = config["created_field"]
        else:
            created_field = "Created"
        if created_field not in WRITEDATA.columns or WRITEDATA.at[get_index(), created_field] == "" or pd.isna(WRITEDATA.at[get_index(), created_field]):
            WRITEDATA.at[get_index(), created_field] = pd.to_datetime("today")
        if "combinator" in config:
            for view in config["combinator"]:
                if "field" in view:
                    WRITEDATA.at[get_index(), view["field"]] = view_to_text(view, WRITEDATA.loc[get_index()])
                else:
                    log.error("Missing key 'field' in combinator view.")
            
        access.write_scores(WRITEDATA)

        


    def update_score_row(index):
        global DATA
        global WRITEDATA
        global INTERACT_ARGS
        global COLUMN_NAMES
        
        set_index(index)
        view_series(DATA.loc[get_index()])


        # Now update the widget entries with values from the WRITEDATA if they exist otherwise set to default
        for key, widget in INTERACT_ARGS.items():
            if COLUMN_NAMES[key][0] != "_":
                if COLUMN_NAMES[key] not in DEFAULT_WRITEDF_VALS:
                    DEFAULT_WRITEDF_VALS[COLUMN_NAMES[key]] = None

                widget.value = DEFAULT_WRITEDF_VALS[COLUMN_NAMES[key]]
                if COLUMN_NAMES[key] in WRITEDATA.columns:
                    dval = WRITEDATA.at[get_index(), COLUMN_NAMES[key]]
                    if pd.notna(dval) and dval != "":
                        widget.value = WRITEDATA.at[get_index(), COLUMN_NAMES[key]]
                else:
                    log.warning("{field} not in WRITEDATA".format(field=COLUMN_NAMES[key]))
                    WRITEDATA[COLUMN_NAMES[key]] = None

                    
        total = len(WRITEDATA.index)
        remain = total
        progress_label = fixed("None")
        if config["scored"]["field"] in WRITEDATA:
            scored = WRITEDATA[config["scored"]["field"]].count()
            remain -= scored
            progress_label = Label("{remain} to go. Scored {scored} from {total} which is {perc:.3g}%".format(remain=remain, scored=scored, total=total, perc=scored/total*100))

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
    

