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

from ipywidgets import jslink, jsdlink, Layout

from .config import *
from .log import Logger
from .util import remove_nan
from .widgets import IntSlider, FloatSlider, Checkbox, RadioButtons, Text, Textarea, Combobox, Dropdown, Label, HTML, HTMLMath, DatePicker, Markdown, Flag, Select, SelectMultiple, IndexSelector, IndexSubIndexSelectorSelect, SaveButton, ReloadButton, CreateDocButton, CreateSummaryButton, CreateSummaryDocButton, BoundedFloatText
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

        self._default_field_vals = pd.Series(dtype=object)
        self._default_field_source = pd.Series(dtype=object)

        self._write_score = True
        self._select_subindex = False
        self._select_selector = False

        self._precompute = []
        self._postcompute = []

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

        if "summary" in config:
            summaries = config["summary"]
            for count, summary in enumerate(summaries):
                label = "_summary_button" + str(count)
                args = {
                    "details": summary,
                    "type": summary["type"],
                    "parent": self,
                }
                self.add_widgets(**{label: CreateSummaryButton(**args)})

        if "summary_documents" in config:
            documents = config["summary_documents"]
            for count, document in enumerate(documents):
                label = "_summary_doc_button" + str(count)
                args = {
                    "document": document,
                    "type": document["type"],
                    "parent": self,
                }
                self.add_widgets(**{label: CreateSummaryDocButton(**args)})



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

    def add_series_row(self):
        """Add a row with a generated subindex to the series."""
        self._data.add_series_row()

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


    def extract_scorer(self, details):
        """Interpret a scoring element from the yaml file and create the relevant widgets to be passed to the interact command"""

        if details["type"] == "load":
            # This is a link to a widget specificaiton stored in a file
            if "details" not in details:
                raise ValueError("Load scorer needs to provide load details as entry under \"details\"")
            df,  newdetails = access.read_data(details["details"])
            for ind, series in df.iterrows():
                self.extract_scorer(remove_nan(series.to_dict()))
            return

        if details["type"] == "group":
            if "children" not in details:
                raise ValueError("group scorer needs to provide a list of children under \"children\"")
            for child in details["children"]:
                if "name" in child and "name" in details and details["name"] is not None:
                    child["name"] = details["name"] + "-" + child["name"]
                if "prefix" in details and details["prefix"] is not None:
                    if "prefix" in child:
                        child["prefix"] = details["prefix"] + child["prefix"]
                    if "field" in child:
                        child["field"] = details["prefix"] + child["field"]
                self.extract_scorer(child)
            return
            
        if details["type"] == "precompute":
            # These are score items that can be precompute (i.e. not dependent on other rows). Once filled they are not changed.
            self._precompute.append(details)
            return

        if details["type"] == "postcompute":
            # These are score items that are computed every time the row is updated.
            self._postcompute.append(details)
            return

        if details["type"] == "Criterion":
            value = None
            display = None
            tally = None
            liquid = None
            lis = None
            join = None
            prefix = details["prefix"]
            if "criterion" in details:
                value = details["criterion"]
            if "display" in details:
                display = details["display"]
            if "liquid" in details:
                liquid = details["liquid"]
            if "tally" in details:
                tally = details["tally"]
            if "list" in details:
                lis = details["list"]
            if "join" in details:
                liquid = details["join"]
            if "width" in details:
                width = details["width"]
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
            if display is not None:
                criterion["args"]["display"] = display
            if liquid is not None:
                criterion["args"]["liquid"] = liquid
            if tally is not None:
                criterion["args"]["tally"] = tally
            if join is not None:
                criterion["args"]["join"] = join
            if lis is not None:
                criterion["args"]["list"] = lis
            self.extract_scorer(criterion)
            return

        if details["type"] == "CriterionComment":
            criterion = json.loads(json.dumps(details))
            criterion["type"] = "Criterion"
            prefix = details["prefix"]
            if "width" in details:
                width = details["width"]
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

        if details["type"] == "CriterionCommentDate":
            criterion = json.loads(json.dumps(details))
            criterion["type"] = "CriterionComment"
            prefix = details["prefix"]
            date = {
                "field": prefix + " Date",
                "type": "DatePicker",
                "args": {
                    "description": "Date",
                }
            }
            for sub_score in [criterion, date]:
                self.extract_scorer(sub_score)
            return


        if details["type"] == "CriterionCommentRaisesMeetsLowers":
            criterioncomment = json.loads(json.dumps(details))
            criterioncomment["type"] = "CriterionComment"

            prefix = details["prefix"]
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

        if details["type"] == "CriterionCommentRaisesMeetsLowersFlag":
            criterioncommentraisesmeetslowers = json.loads(json.dumps(details))
            criterioncommentraisesmeetslowers["type"] = "CriterionCommentRaisesMeetsLowers"

            prefix = details["prefix"]
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

        if details["type"] == "CriterionCommentScore":
            criterioncomment = json.loads(json.dumps(details))
            criterioncomment["type"] = "CriterionComment"
            if "width" in details:
                width = details["width"]
            else:
                width = "800px"

            prefix = details["prefix"]
            if "min" in details:
                minval = details["min"]
            else:
                minval = 0
            if "max" in details:
                maxval = details["max"]
            else:
                maxval = 10
            if "step" in details:
                step = details["step"]
            else:
                step = 1
            if "value" in details:
                value = details["value"]
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
        if details["type"] in global_variables:
            widget_type = global_variables[details["type"]]

            if "field" in details:
                field_name = clean_string(details["field"])
                self._column_names_dict[field_name] = details["field"]

                # Create an instance of the object to extract default value.
                self._default_field_vals[details["field"]] = widget_type(parent=self, field_name=details["field"]).get_value()
                if "value" in details:
                    self._default_field_vals[details["field"]] = details["value"]
                if "args" in details and "value" in details["args"]:
                    self._default_field_vals[details["field"]] = details["args"]["value"]
                if "default" in details:
                    if "source" in details["default"]:
                        source = details["default"]["source"]
                        if source in self._data.columns:
                            self._default_field_source[details["field"]] = source
                        else:
                            log.warning(f"Missing column \"{source}\" in data.columns")
                    if "value" in details["default"]:
                        self._default_field_vals[details["field"]] = details["default"]["value"]

            else:
                # Field field_name is missing, generate a random one.
                field_name = "_" + "".join(random.choice(string.ascii_letters) for _ in range(39))
                self._column_names_dict[field_name] = field_name

            # Deep copy of details so we don't change it globally.
            process_details = json.loads(json.dumps(details))

            # Deal with HTML descriptions (setting them to blank if not set)
            if process_details["type"] in ["HTML", "HTMLMath", "Markdown"]:
                if "args" not in process_details:
                    process_details["args"] = {"description": " "}
                else:
                    if "description" not in process_details:
                        process_details["args"]["description"] = " "

            if "source" in process_details:
                # Set arguments of widget from data fields if source is given
                if "args" in process_details["source"]:
                    for arg, field in process_details["source"]["args"]:
                        if arg not in process_details["args"]:
                            self.set_column(field)
                            process_details["args"][arg] = self.get_value()

            # Set up arguments for the widget
            args = process_details["args"]
            try:
                args["field_name"] = field_name
            except TypeError as err:
                raise TypeError("The argument \"args\" in _referia.yml should be in the form of a mapping.") from err
            args["column_name"] = self._column_names_dict[field_name]

            for field in ["display", "tally", "liquid"]:
                if field in process_details and field not in args:
                    args[field] = process_details[field]
            # Layout descriptor can be in main structure, or in args.
            if "layout" in process_details and "layout" not in args:
                args["layout"] =  Layout(**process_details["layout"])
            elif "layout" in args:
                args["layout"] = Layout(**args["layout"])
            args["parent"] = self
            # Add the widget
            self.add_widgets(**{field_name: widget_type(**args)})
        else:
            raise Exception("Cannot find " + details["type"] + " interaction type.")


    def display_widgets(self):
        """Display the field entry widgets"""
        for key, widget in self.widgets().items():
            widget.display()

    def template_to_value(self, template):
        """Convert a template to values."""
        if "use" in template:
            if template["use"] == "viewer":
                viewer = config["viewer"] 
                if type(viewer) is not list:
                    viewer = [viewer]
                string = ""
                for view in viewer:
                    string += self._data.view_to_value(view)
                    string += "\n\n"
                return string
            elif template["use"] == "scorer":
                return self.widgets_to_value()
        else:
            return self._data.view_to_value(template)
        
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


    def load_flows(self, reload=False):
        """Reload flows from data stores."""
        log.info(f"Reload of flows requested.")
        if reload:
            index = self.get_index()
            selector = self.get_selector()
            subindex = self.get_subindex()
            log.debug(f"Storing index: \"{index}\" selector: \"{selector}\" subindex: \"{subindex}\"")
        self._data.load_flows()
        if reload:
            log.debug(f"Resetting index.")
            if index is not None:
                self.set_index(index)
            if selector is not None:
                self.set_selector(selector)
            if subindex is not None:
                self.set_subindex(subindex)
        self.populate_widgets()

    def save_flows(self):
        if self._data._writedata is not None:
            log.info(f"Writing _writedata.")
            access.write_scores(self._data._writedata)
        if self._data._writeseries is not None:
            access.write_series(self._data._writeseries)
            log.info(f"Writing _writeseries.")

    def create_document(self, document, summary=False):
        """Create a document from the data we've provided."""
        args = {}
        for field in document:
            if field not in ["type"]:
                args[field] = document[field]
                if document[field] is not None:
                    if type(document[field]) is dict:
                        if "tally" in document[field] or "display" in document[field] or "list" in document[field] or "join" in document[field] or "liquid" in document[field] or "use" in document[field]:
                            if summary and field in ["content", "body"]:
                                ind = self.get_index()
                                txt = ""
                                for ind2 in self.get_indices():
                                    self.set_index(ind2)
                                    txt += self.template_to_value(document[field])
                                    txt += "\n\n"
                                args[field] = txt
                                self.set_index(ind)
                            else:
                                args[field] = self.template_to_value(document[field])
        if "body" in args:
            if "content" in args:
                log.warning(f"Contents field being overwritten by body in create_document")       
            args["content"] = args["body"]
        if "header" in args:
            args["content"] = args["header"] + "\n\n" + args["content"]
            del args["header"]
        if "footer" in args:
            args["content"] = args["content"] + "\n\n" + args["footer"]
            del args["footer"]
            
            
        system.create_document(document, **args)

    

    def create_summary(self, details):
        """Create a summary file given the relevant information"""
        args = {}
        args["entries"] = []
        if "columns" in details:
            columns = details["columns"]
            if type(columns) is not list:
                columns = [columns]

            for column in columns:
                for index in self.index:
                    print(f"Set index {index}")
                    self.set_index(index)
                    val = self._data.get_value_column(column)
                    print(f"Value is {val}")
                    args["entries"].append(val)
        system.create_summary(details, **args)

    def value_updated(self):
        """If a value in a row has been updated, modify other values"""

        # If index has changed, run computes.
        for compute in self._postcompute:
            assess.run_compute(compute)

        # Need to determine if these should update series or data.
        # Update timestamp fields.
        today_val = pd.to_datetime("today")
        if "timestamp_field" in config:
            timestamp_field = config["timestamp_field"]
        else:
            timestamp_field = "Timestamp"
        if timestamp_field not in self._data.columns:
            self._data.add_column(timestamp_field)
        self._data.set_dtype(timestamp_field, "datetime64[ns]")

        self.set_column(timestamp_field)
        self.set_value(today_val,
                       trigger_update=False)
        if "created_field" in config:
            created_field = config["created_field"]
        else:
            created_field = "Created"

        if created_field not in self._data.columns:
            self._data.add_column(created_field)
        self._data.set_dtype(created_field, "datetime64[ns]")

        if created_field not in self._data.columns or assess.empty(self._data.get_value_column(created_field)):
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

    def last_widget(self):
        """Return the most recently added widget"""
        key = self._widget_dict.keys[-1] # Relying on ordered dictionaries here
        widget = self._widget_dict[key]
        return key, widget
    
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
