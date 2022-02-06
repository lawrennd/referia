
import string
import random

import re

import numpy as np
import pandas as pd
import json

from IPython.display import display, HTML
import matplotlib.pyplot as plt
from IPython.display import Markdown, display
from ipywidgets import IntSlider, FloatSlider, Checkbox, Text, Textarea, Combobox, Dropdown, Label, Layout, HTML, HTMLMath, DatePicker
from ipywidgets import interact, interactive, fixed, interact_manual

import pypdftk as tk

from .widgets import MyCheckbox, MyFileChooser

from .config import *
from .log import Logger
from . import access
from . import assess
from . import system

interact_manual.opts["manual_name"] = "Save Score"

INTERACT_ARGS = {}
COLUMN_NAMES = {}
DEFAULT_WRITEDF_VALS = pd.Series()
DEFAULT_WRITEDF_SOURCE = pd.Series()

log = Logger(
    name=__name__,
    level=config["logging"]["level"],
    filename=config["logging"]["filename"]
)

"""This file creates displays that help visualize the data."""

def expand_cell():

    display(HTML(data="""
<style>
.container {
    width: 100% !important;
}   

div.notebook-container {
    width: 100% !important;
    height: fit-content;
}  

div.menubar-container {
    width: 100% !important;
    height: fit-content;
}  

div.maintoolbar-container {
    width: 100% !important;
    height: fit-content;
}  

div.cell.selected {
    border-left-width: 1px !important;  
}

div.output_scroll {
    resize: vertical !important;
}

.output_wrapper .output { 
    overflow-y: visible; 
    height: fit-content; 
}


.output_scroll {
    box-shadow:none !important;
    webkit-box-shadow:none !important;
}
</style>
"""))


def view(data):
    """Provide a view of the data that allows the user to verify some aspect of its quality."""
    fig, ax = plt.subplots(figsize=(8, 5))
    data.hist('Score', bins=np.linspace(-.5, 12.5, 14), width=0.8, ax=ax)
    ax.set_xticks(range(0,13))


def extract_scorer(orig_score, data):
    """Interpret a scoring element from the yaml file and create the relevant widgets to be passed to the interact command"""
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
            interact_args = {**interact_args, **extract_scorer(sub_score, data)}
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
            interact_args = {**interact_args, **extract_scorer(sub_score, data)}
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
            interact_args = {**interact_args, **extract_scorer(sub_score, data)}
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
            interact_args = {**interact_args, **extract_scorer(sub_score, data)}
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
                if source in data.columns:
                    DEFAULT_WRITEDF_SOURCE[score["field"]] = source
                else:
                    log.warning(f"Missing column \"{source}\" in _DATA and _WRITEDATA.")
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
                    score["args"][arg] = data.get_current_value(field)
        if "criterion" in score["source"]:
            criterion = score["source"]["criterion"]
            if "display" in criterion:
                score["criterion"] = criterion["display"].format(**data.mapping())
                                 
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


def viewer_to_text(key, data):
    """Create a formatted text output from a yaml entry with base text and format keys."""
    text = ""
    if key in config:
        for view in config[key]:
            text += view_to_text(view, data)
    return text



def view_to_text(view, data):
    """Create the text of the view."""
    if "format" in view:
        format = data.mapping(view["format"])
    else:
        format = data.mapping()

    if data.conditions(view):
        return view["display"].format(**format)
    else:
        return ""


def view_text(data):
    """Text that views a a single record."""
    if "viewer" in config:
        return viewer_to_text("viewer", data)
    else:
        return ""

def score(index=None, data=None):
    global INTERACT_ARGS

    if data is None:
        data = assess.Data()
        
    if index is not None:
        data.set_index(index)

    INTERACT_ARGS = {}
    # Process the different scorers in from the _referia.yml file 
    if "scorer" in config:
        for score in config["scorer"]:
            INTERACT_ARGS = {**INTERACT_ARGS, **extract_scorer(score, data)}

    
    def update_df(progress_label, **kwargs):

        for key, value in kwargs.items():
            # fields starting with "_" are not transferred
            # (typically HTML widgets for prompting input)
            if key[0] != "_":
                data.set_current_value(value, COLUMN_NAMES[key])

        if "timestamp_field" in config:
            timestamp_field = config["timestamp_field"]
        else:
            timestamp_field = "Timestamp"
        data.set_current_value(
            pd.to_datetime("today"),
            timestamp_field
        )
        if "created_field" in config:
            created_field = config["created_field"]
        else:
            created_field = "Created"
        if created_field not in data._writedata.columns or assess.empty(data.get_current_value(created_field)):
            data.set_current_value(
                pd.to_datetime("today"),
                created_field
            )
        if "combinator" in config:
            for view in config["combinator"]:
                if "field" in view:
                    data.set_current_value(
                        view_to_text(view, data),
                        view["field"]
                    )                    
                else:
                    log.error("Missing key 'field' in combinator view.")
            
        access.write_scores(data._writedata)

        


    def update_score_row(data, index):
        global INTERACT_ARGS
        global COLUMN_NAMES
        
        data.set_index(index)
        system.view_series(data)
        display(Markdown(view_text(data)))
    


        # Now update the widget entries with values from the data
        for key, widget in INTERACT_ARGS.items():
            if COLUMN_NAMES[key][0] != "_":
                if COLUMN_NAMES[key] not in DEFAULT_WRITEDF_VALS:
                    DEFAULT_WRITEDF_VALS[COLUMN_NAMES[key]] = None
                widget.value = DEFAULT_WRITEDF_VALS[COLUMN_NAMES[key]]
                # Take default from existing column 
                if COLUMN_NAMES[key] in DEFAULT_WRITEDF_SOURCE:
                    dval = data.get_current_value(DEFAULT_WRITEDF_SOURCE[COLUMN_NAMES[key]])
                    if assess.notempty(dval):
                        widget.value = dval
                # Take default from existing column in _WRITEDATA
                if COLUMN_NAMES[key] in data.columns:
                    dval = data.get_current_value(COLUMN_NAMES[key])
                    if assess.notempty(dval):
                        widget.value = dval
                else:
                    data.add_column(COLUMN_NAMES[key])

                    
        total = data.to_score()
        remain = total
        progress_label = fixed("None")
        if "scored" in config:
            scored = data.scored()
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

            
    index_select=Dropdown(options=data.index, value=data.get_index())
    interact(update_score_row, index=index_select, data=fixed(data))
    

