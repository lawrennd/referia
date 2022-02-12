"""This file creates displays that help visualize the data."""

import string
import random

import re

import numpy as np
import pandas as pd
import json

import markdown

from IPython import display
import matplotlib.pyplot as plt


from ipywidgets import jslink, jsdlink

import pypdftk as tk

from .config import *
from .log import Logger
from .widgets import IntSlider, FloatSlider, Checkbox, Text, Textarea, Combobox, Dropdown, Label, Layout, HTML, HTMLMath, DatePicker, Markdown, interact, interactive, interact_manual, fixed# MyCheckbox, MyFileChooser,
from . import access
from . import assess
from . import system



log = Logger(
    name=__name__,
    level=config["logging"]["level"],
    filename=config["logging"]["filename"]
)


def expand_cell():

    display.display(display.HTML(data="""
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
            text += "\n\n"
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


class Scorer:
    def __init__(self, index=None, data=None):
        self._interact_args = {}
        self._column_names = {}
        self._default_field_vals = pd.Series()
        self._default_field_source = pd.Series()

        self._write_score = True
        self._select_subindex = False
        self._select_selector = False
        if data is None:
            self._data = assess.Data()
        else:
            self._data = data

        if index is not None:
            self.set_index(index)
                        
        # Process the different scorers in from the _referia.yml file
        if "scored" in config:
            _progress_label = Label()
            self.add_widgets(_progress_label=_progress_label)

        if "viewer" in config:
            _viewer_label = Markdown()
            _viewer_label.description = " "
            self.add_widgets(_viewer_label=_viewer_label)
            
        if "scorer" in config:
            for score in config["scorer"]:
                self.extract_scorer(score)

    def add_widgets(self, **kwargs):
        self._interact_args = {**self._interact_args, **kwargs}
        
    @property
    def index(self):
        return self._data.index

    def get_index(self):
        return self._data.get_index()

    def set_index(self, value):
        self._data.set_index(value)
        self.view_entity()

    def get_selectors(self):
        return self._data.get_selectors()

    def get_selector(self):
        return self._data.get_selector()

    def set_selector(self, value):
        self._data.set_selector(value)
        self.view_entity()

    def get_subindices(self):
        return self._data.get_subindices()
    
    def get_subindex(self):
        return self._data.get_subindex()
    
    def set_subindex(self, value):
        self._data.set_subindex(value)
        self.view_entity()

    def select_index(self):
        select=Dropdown(
            options=self.index,
            value=self.get_index(),
        )
        interact(self.set_index, value=select)

    def select_subindex(self):
        """Select a subindex from the data"""
        select=Dropdown(
            options=self.get_subindices(),
            value=self.get_subindex(),
        )
        interact(self.set_subindex, value=select)

    def select_selector(self):
        """Select a selector from the data"""
        select=Dropdown(
            options=self.get_selectors(),
            value=self.get_selector(),
        )
        interact(self.set_selector, value=select)

    def view_entity(self):
        self.populate_widgets()


    def run(self):
        """Run the scorer to edit the data frame."""
        self.select_index()
        if self._select_selector:
            self.select_selector()
        if self._select_subindex:
            self.select_subindex()
        system.view_series(self._data)
        self.batch_entry_edit()


    def extract_scorer(self, score):
        """Interpret a scoring element from the yaml file and create the relevant widgets to be passed to the interact command"""
        if score['type'] == 'Criterion':
            value = None
            display = None
            prefix = score["prefix"]
            if "display" in score:
                display = score["display"]
            elif "criterion" in score:
                value = score["criterion"]
            if "width" in score:
                width = score["width"]
            else:
                width = "800px"
                criterion = {
                    "field": "_" + prefix + " Criterion",
                    "type": "HTMLMath",
                    "args": {
                        "layout": {"width": width},
                    }
                }
            if value is not None:
                criterion["args"]["value"] = value
            elif display is not None:
                criterion["display"] = display
                self.extract_scorer(criterion)
            return

        if score["type"] == "CriterionComment":
            criterion = json.loads(json.dumps(score))
            criterion["type"] = "Criterion"
            prefix = score["prefix"]
            if "width" in score:
                width = score["width"]
            else:
                width = "800px"
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
                self.extract_scorer(sub_score)
            return


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
                self.extract_scorer(sub_score)
            return

        if score["type"] == "CriterionCommentRaisesMeetsLowersFlag":
            criterioncommentraisesmeetslowers = json.loads(json.dumps(score))
            criterioncommentraisesmeetslowers["type"] = "CriterionCommentRaisesMeetsLowers"

            prefix = score["prefix"]
            flag = {
                "field": prefix + " Flag",
                "type": "MyCheckbox",
                "args": {
                    "value": False,
                    "description": "Flag",
                }
            }
            for sub_score in [criterioncommentraisesmeetslowers, flag]:
                self.extract_scorer(sub_score)
            return

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

            slider = {
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
            for sub_score in [criterioncomment, slider]:
                self.extract_scorer(sub_score)
            return

        global_variables = globals()
        if "field" in score:
            name = clean_string(score["field"])
            self._column_names[name] = score["field"]

            # Create an instance of the object to extract default value.
            self._default_field_vals[score["field"]] = global_variables[score["type"]]().get_value()
            if "value" in score:
                self._default_field_vals[score["field"]] = score["value"]               
            if "args" in score and "value" in score["args"]:
                self._default_field_vals[score["field"]] = score["args"]["value"]
            if "default" in score:
                if "source" in score["default"]:
                    source = score["default"]["source"]
                    if source in self._data.columns:
                        self._default_field_source[score["field"]] = source
                    else:
                        log.warning(f"Missing column \"{source}\" in data.columns")
                if "value" in score["default"]:
                    self._default_field_vals[score["field"]] = score["default"]["value"]

        else:
            # Field name is missing, generate a random one.
            name = "_" + "".join(random.choice(string.ascii_letters) for _ in range(39))
            self._column_names[name] = name

        # Deep copy of score so we don't change it globally.
        process_score = json.loads(json.dumps(score))

        # Deal with HTML descriptions (setting them to blank if not set)
        if process_score["type"] in ["HTML", "HTMLMath", "Markdown"]:
            if "args" not in process_score:
                process_score["args"] = {"description": " "}
            else:
                if "description" not in process_score:
                    process_score["args"]["description"] = " "
            if "display" in process_score:
                process_score["args"]["value"] = process_score["display"].format(**self._data.mapping())

        if "source" in process_score:
            # Set arguments of widget from data fields if source is given
            if "args" in process_score["source"]:
                for arg, field in process_score["source"]["args"]:
                    if arg not in process_score["args"]:
                        process_score["args"][arg] = self._data.get_current_value(field)
            if "criterion" in process_score["source"]:
                criterion = process_score["source"]["criterion"]
                if "display" in criterion:
                    process_score["criterion"] = criterion["display"].format(**self._data.mapping())

        # Set arguments of widget from data fields if appropriate.                
        if "layout" in process_score:
            process_score["args"]["layout"] = Layout(**process_score["layout"])

        if process_score["type"] in global_variables:
            self.add_widgets(**{name: global_variables[process_score["type"]](**process_score["args"])})
        else:
            raise Exception("Have not loaded " + process_score["type"] + " interaction type.")
        
    def batch_entry_edit(self):
        """Update the data frame with a batch entry (hit save score to save updates)"""
        interact_manual(
            self.update_entry, 
            **self.widgets()
        )

    
    def save_score(self):
        access.write_scores(self._data._writedata)
        if self._data._writeseries is not None:
            access.write_series(self._data._writeseries)

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

    def widgets(self):
        """Return the widgets associated with the display"""
        return self._interact_args

    def populate_widgets(self):
        """Update the widgets with defaults or values from the data"""
        for key, widget in self.widgets().items():
            if key == "_viewer_label":
                widget.value = viewer_to_text("viewer", self._data)
                continue

            if key == "_progress_label":
                total = self._data.to_score()
                scored = self._data.scored()
                remain = total - scored
                perc=scored/total*100
                if "_progress_label" in self.widgets():
                    widget.value = f"{remain} to go. Scored {scored} from {total} which is {perc:.3g}%"
                continue
            
            if self._column_names[key][0] != "_": # Ignore columns starting with _
                if self._column_names[key] not in self._default_field_vals:
                    self._default_field_vals[self._column_names[key]] = None
                widget.value = self._default_field_vals[self._column_names[key]]

                # Take a default value from default source specified in _referia.yml
                if self._column_names[key] in self._default_field_source:
                    dval = self._data.get_current_value(self._default_field_source[self._column_names[key]])
                    if assess.notempty(dval):
                        widget.value = dval

                # Take value from the current value in _data
                if self._column_names[key] in self._data.columns:
                    dval = self._data.get_current_value(self._column_names[key])
                    if assess.notempty(dval):
                        widget.value = dval
                else:
                    self._data.add_column(self._column_names[key])



            
    

