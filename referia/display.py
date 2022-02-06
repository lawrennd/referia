
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

class Scorer:
    def __init__(self, index=None, data=None):
        self._interact_args = {}
        self._column_names = {}
        self._write_score = True
        if data is None:
            self._data = assess.Data()
        else:
            self._data = data

        if index is not None:
            self.set_index(index)
                        
        # Process the different scorers in from the _referia.yml file 
        if "scorer" in config:
            for score in config["scorer"]:
                self._interact_args = {**self._interact_args, **self.extract_scorer(score)}

    def get_index(self):
        return self._data.get_index()

    def set_index(self, value):
        self._data.set_index(value)
        
    def select_index(self):
        index_select=Dropdown(options=self._data.index, value=self._data.get_index())
        interact(self.update_score_row, index=index_select)

    def run(self):
        """Run the scorer to edit the data frame."""
        self.select_index()
        self.batch_entry_edit()


    def extract_scorer(self, orig_score):
        """Interpret a scoring element from the yaml file and create the relevant widgets to be passed to the interact command"""
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
                interact_args = {**interact_args, **self.extract_scorer(sub_score)}
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
                interact_args = {**interact_args, **self.extract_scorer(sub_score)}
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
                interact_args = {**interact_args, **self.extract_scorer(sub_score)}
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
                interact_args = {**interact_args, **self.extract_scorer(sub_score)}
            return interact_args

        global_variables = globals()
        if "field" in score:
            name = clean_string(score["field"])
            self._column_names[name] = score["field"]

            # Create an instance of the object to extract default value.
            DEFAULT_WRITEDF_VALS[score["field"]] = global_variables[score["type"]]().value
            if "value" in score:
                DEFAULT_WRITEDF_VALS[score["field"]] = score["value"]               
            if "args" in score and "value" in score["args"]:
                DEFAULT_WRITEDF_VALS[score["field"]] = score["args"]["value"]
            if "default" in score:
                if "source" in score["default"]:
                    source = score["default"]["source"]
                    if source in self._data.columns:
                        DEFAULT_WRITEDF_SOURCE[score["field"]] = source
                    else:
                        log.warning(f"Missing column \"{source}\" in _DATA and _WRITEDATA.")
                if "value" in score["default"]:
                    DEFAULT_WRITEDF_VALS[score["field"]] = score["default"]["value"]

        else:
            # Field name is missing, generate a random one.
            name = "_" + "".join(random.choice(string.ascii_letters) for _ in range(39))
            self._column_names[name] = name

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
                        score["args"][arg] = self._data.get_current_value(field)
            if "criterion" in score["source"]:
                criterion = score["source"]["criterion"]
                if "display" in criterion:
                    score["criterion"] = criterion["display"].format(**self._data.mapping())

        # Set arguments of widget from data fields if appropriate.                
        global_variables = globals()
        if "layout" in score:
            score["args"]["layout"] = Layout(**score["layout"])
        elif score["type"] in global_variables:
            interact_args[name] = global_variables[score["type"]](**score["args"])
        else:
            raise Exception("Have not loaded " + score["type"] + " interaction type.")
        return interact_args

    def batch_entry_edit(self):
        """Update the data frame with a batch entry (hit save score to save updates)"""
        interact_manual(
            self.update_entry, 
            **self._interact_args
        )

    
    def save_score(self):
        access.write_scores(self._data._writedata)

    def update_entry(self, **kwargs):

        for key, value in kwargs.items():
            # fields starting with "_" are not transferred
            # (typically HTML widgets for prompting input)
            if key[0] != "_":
                self._data.set_current_value(value, self._column_names[key])

        if "timestamp_field" in config:
            timestamp_field = config["timestamp_field"]
        else:
            timestamp_field = "Timestamp"
        self._data.set_current_value(
            pd.to_datetime("today"),
            timestamp_field
        )
        if "created_field" in config:
            created_field = config["created_field"]
        else:
            created_field = "Created"
        if created_field not in self._data._writedata.columns or assess.empty(self._data.get_current_value(created_field)):
            self._data.set_current_value(
                pd.to_datetime("today"),
                created_field
            )
        if "combinator" in config:
            for view in config["combinator"]:
                if "field" in view:
                    self._data.set_current_value(
                        view_to_text(view, self._data),
                        view["field"]
                    )                    
                else:
                    log.error("Missing key 'field' in combinator view.")
            
        if self._write_score:
            self.save_score()

        


    def update_score_row(self, index):
        
        self.set_index(index)
        system.view_series(self._data)
        display(Markdown(view_text(self._data)))
    


        # Now update the widget entries with values from the data
        for key, widget in self._interact_args.items():
            if self._column_names[key][0] != "_":
                if self._column_names[key] not in DEFAULT_WRITEDF_VALS:
                    DEFAULT_WRITEDF_VALS[self._column_names[key]] = None
                widget.value = DEFAULT_WRITEDF_VALS[self._column_names[key]]
                # Take default from existing column 
                if self._column_names[key] in DEFAULT_WRITEDF_SOURCE:
                    dval = self._data.get_current_value(DEFAULT_WRITEDF_SOURCE[self._column_names[key]])
                    if assess.notempty(dval):
                        widget.value = dval
                # Take default from existing column in _WRITEDATA
                if self._column_names[key] in self._data.columns:
                    dval = self._data.get_current_value(self._column_names[key])
                    if assess.notempty(dval):
                        widget.value = dval
                else:
                    self._data.add_column(self._column_names[key])

        # COmmenting because it feels out of place here, progress should be separtely handled.            
        # total = self._data.to_score()
        # remain = total
        # progress_label = fixed("None")
        # if "scored" in config:
        #     scored = self._data.scored()
        #     remain -= scored
        #     perc=scored/total*100
        #     progress_label = Label(f"{remain} to go. Scored {scored} from {total} which is {perc:.3g}%")

        # self._interact_args = {
        #     "progress_label": progress_label,
        #     **self._interact_args
        # }


            
    

