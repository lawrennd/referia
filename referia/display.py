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

from .config import *
from .log import Logger
from .widgets import IntSlider, FloatSlider, Checkbox, Text, Textarea, Combobox, Dropdown, Label, Layout, HTML, HTMLMath, DatePicker, Markdown, Flag, IndexSelector, IndexSubIndexSelectorSelect, SaveButton, ReloadButton, CreateDocButton
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



class Scorer:
    def __init__(self, index=None, data=None):
        
        # Store the map between valid python variable names and data column names
        self._column_names_dict = {}
        # Store the map between valid python varliable names and their boxed widgets.
        self._widget_dict = {}
                
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

        self._create_widgets()

    def _create_widgets(self):
        """Create the widgets to be used for display."""
        _reload_button = ReloadButton(parent=self)
        self.add_widgets(_reload_button=_reload_button)
                        
        # Process the different scorers in from the _referia.yml file
        if "scored" in config:
            _progress_label = Markdown(description=" ", field_name="_progress_label")
            self.add_widgets(_progress_label=_progress_label)

        if "viewer" in config:
            # TK need to add in viewer arguments for display etc here.
            views = config["viewer"]
            if type(views) is not list:
                views = [views]
            
            for count, view in enumerate(views):
                label = "_viewer_label" + str(count)
                args = {
                    "description": " ",
                    "field_name": label,
                    "column_name": label,
                    **view,
                    "parent": self,
                }
                self.add_widgets(**{label: Markdown(**args)})
            
        if "scorer" in config:
            for score in config["scorer"]:
                self.extract_scorer(score)

        if "documents" in config:
            documents = config["documents"]
            for count, document in enumerate(documents):
                label = "_doc_button" + str(count)
                args = {
                    "document": document,
                    "type": document["type"],
                    "parent": self,
                }
                self.add_widgets(**{label: CreateDocButton(**args)})


            
        _save_button = SaveButton(parent=self)
        self.add_widgets(_save_button=_save_button)
                    
    def add_widgets(self, **kwargs):
        self._widget_dict = {**self._widget_dict, **kwargs}

    @property
    def index(self):
        return self._data.index

    def get_index(self):
        return self._data.get_index()

    def set_index(self, value):
        self._data.set_index(value)
        self.populate_widgets()

    def get_value(self):
        return self._data.get_value()
    
    def set_value(self, value, trigger_update=True):
        """Update a value in one of the output flows."""
        old_value = self.get_value()
        column = self.get_column()
        if value != old_value:
            log.debug(f"Column is \"{column}\". Old value is \"{old_value}\" and new value is \"{value}\".")
            self._data.set_value(value)
            if trigger_update:
                self.value_updated()

    def get_column(self):
        return self._data.get_column()
    
    def set_column(self, column):
        self._data.set_column(column)
        
    def get_selectors(self):
        return self._data.get_selectors()

    def get_selector(self):
        return self._data.get_selector()

    def set_selector(self, value):
        self._data.set_selector(value)

    def get_indices(self):
        return self._data.index

    
    
    def get_subindices(self):
        return self._data.get_subindices()
    
    def get_subindex(self):
        return self._data.get_subindex()
    
    def set_subindex(self, value):
        self._data.set_subindex(value)
        self.populate_widgets()

    def add_new_row_to_series(self):
        """Add a row with a generated subindex to the series."""
        self._data.add_new_row_to_series()
        
    def full_selector(self):
        """Select a selector and subindex from the data"""
        self._selector_widget=IndexSubIndexSelectorSelect(parent=self)
        self._selector_widget.display()

    def select_index(self):
        self._selector_widget=IndexSelector(parent=self)
        self._selector_widget.display()

    def select_selector(self):
        """Select a selector from the data"""
        self._selector_widget=IndexSubIndexSelectorSelect(parent=self)
        self._selector_widget.display()

        
    def select_subindex(self):
        """Select a subindex from the data"""
        self._selector_widget=IndexSubIndexSelectorSelect(parent=self)
        self._selector_widget.display()

    def get_select_selector(self):
        """Get state of selector selection."""
        return self._select_selector

    def set_select_selector(self, value):
        """Set state of selector selection."""
        self._select_selector = value

    def get_select_subindex(self):
        """Get state of subindex selection."""
        return self._select_subindex

    def set_select_subindex(self, value):
        """Set state of subindex selection."""
        self._select_subindex = value
        
    def run(self):
        """Run the scorer to edit the data frame."""
        if "series" in config:
            self.full_selector()
        else:
            self.select_index()
        self.display_widgets()
        self.populate_widgets()
        system.view_series(self._data)

    def extract_scorer(self, score):
        """Interpret a scoring element from the yaml file and create the relevant widgets to be passed to the interact command"""
        if score['type'] == 'Criterion':
            value = None
            display = None
            tally = None
            prefix = score["prefix"]
            if "display" in score:
                display = score["display"]
            elif "criterion" in score:
                value = score["criterion"]
            if "tally" in score:
                tally = score["tally"]
            if "width" in score:
                width = score["width"]
            else:
                width = "800px"
                criterion = {
                    "field": "_" + prefix + " Criterion",
                    "type": "Markdown",
                    "args": {
                        "layout": {"width": width},
                    }
                }
            if value is not None:
                criterion["args"]["value"] = value
            elif display is not None:
                criterion["args"]["display"] = display
            if tally is not None:
                criterion["args"]["tally"] = tally
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
                "type": "Flag",
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

        # Get the widget type from the global variables list
        global_variables = globals()
        if score["type"] in global_variables:
            widget_type = global_variables[score["type"]]

            if "field" in score:
                field_name = clean_string(score["field"])
                self._column_names_dict[field_name] = score["field"]

                # Create an instance of the object to extract default value.
                self._default_field_vals[score["field"]] = widget_type(parent=self, field_name=score["field"]).get_value()
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
                # Field field_name is missing, generate a random one.
                field_name = "_" + "".join(random.choice(string.ascii_letters) for _ in range(39))
                self._column_names_dict[field_name] = field_name

            # Deep copy of score so we don't change it globally.
            process_score = json.loads(json.dumps(score))

            # Deal with HTML descriptions (setting them to blank if not set)
            if process_score["type"] in ["HTML", "HTMLMath", "Markdown"]:
                if "args" not in process_score:
                    process_score["args"] = {"description": " "}
                else:
                    if "description" not in process_score:
                        process_score["args"]["description"] = " "

            if "source" in process_score:
                # Set arguments of widget from data fields if source is given
                if "args" in process_score["source"]:
                    for arg, field in process_score["source"]["args"]:
                        if arg not in process_score["args"]:
                            self.set_column(field)
                            process_score["args"][arg] = self.get_value()

            # Set up arguments for the widget
            args = process_score["args"]
            args["field_name"] = field_name
            args["column_name"] = self._column_names_dict[field_name]
            if "display" in process_score and "display" not in args:
                args["display"] = process_score["display"]
            if "tally" in process_score and "tally" not in args:
                args["tally"] = process_score["tally"]
            if "layout" in process_score and "layout" not in args:
                args["layout"] =  Layout(**process_score["layout"])
            args["parent"] = self

            # Add the widget
            self.add_widgets(**{field_name: widget_type(**args)})
        else:
            raise Exception("Cannot find " + score["type"] + " interaction type.")

        
    def display_widgets(self):
        """Display the field entry widgets"""
        for key, widget in self.widgets().items():
            widget.display()
            
    def template_to_value(self, template):
        """Convert a template to values."""
        if "use" in template:
            if template["use"] == "viewer":
                return self._data.viewer_to_value(config["viewer"])
            elif template["use"] == "scorer":
                return self.widgets_to_value()
        else:
            return self._data.viewer_to_value(template)

    def widgets_to_value(self):
        """Convert the widget outputs into text."""
        value = ""
        for key, widget in self.widgets().items():
            value += widget.to_markdown()
            if value != "":
                value+= "\n\n"
        return value
    
    def view_scorer(self):
        text = ""
        for key, widget in self.widgets().items():
            text += widget.to_markdown()
        return text

    
    def load_flows(self):
        """Reload flows from data stores."""
        log.info(f"Reload of flows requested.")
        index = self.get_index()
        selector = self.get_selector()
        subindex = self.get_subindex()
        log.debug(f"Storing index: \"{index}\" selector: \"{selector}\" subindex: \"{subindex}\"")
        self._data.load_flows()
        log.debug(f"Resetting index.")
        self.set_index(index)
        self.set_selector(selector)
        self.set_subindex(subindex)
        self.populate_widgets()
        
    def save_flows(self):
        access.write_scores(self._data._writedata)
        if self._data._writeseries is not None:
            access.write_series(self._data._writeseries)

    def create_document(self, document):
        """Create a document from the data we've provided."""
        args = {}
        content = ""
        if "header" in document:
            content += self.template_to_value(document["header"])
        if "body" in document:
            content += self.template_to_value(document["body"])
        if "footer" in document:
            content += self.template_to_value(document["footer"])
        args["content"] = content
        
        for field in document:
            if field not in ["header", "body", "footer", "type"]:
                args[field] = self._data.view_to_value(document[field])
        system.create_document(document, **args)
        
    def value_updated(self):
        """If a value in a row has been updated, modify other values"""
        # Need to determine if these should update series or data.
        # Update timestamp fields.
        today_val = pd.to_datetime("today")
        if "timestamp_field" in config:
            timestamp_field = config["timestamp_field"]
        else:
            timestamp_field = "Timestamp"
        self.set_column(timestamp_field)
        self.set_value(today_val,
                       trigger_update=False)
        if "created_field" in config:
            created_field = config["created_field"]
        else:
            created_field = "Created"
        if created_field not in self._data._writedata.columns or assess.empty(self._data.get_value_column(created_field)):
            self.set_column(created_field)
            self.set_value(today_val,
                           trigger_update=False)

        # Combinator is a combined field based on others
        if "combinator" in config:
            for view in config["combinator"]:
                if "field" in view:
                    combinator = self._data.viewer_to_value(view)
                    self.set_column(view["field"])
                    self.set_value(combinator,
                                   trigger_update=False)
                else:
                    log.error("Missing key 'field' in combinator view.")
            

    def widgets(self):
        """Return the widgets associated with the display"""
        return self._widget_dict

    def populate_widgets(self):
        """Update the widgets with defaults or values from the data"""
        for key, widget in self.widgets().items():

            if key == "_progress_label":
                total = self._data.to_score()
                scored = self._data.scored()
                remain = total - scored
                perc=scored/total*100
                if "_progress_label" in self.widgets():
                    widget.set_value(f"{remain} to go. Scored {scored} from {total} which is {perc:.3g}%")
                continue
            
            widget.refresh()
            



            
    

