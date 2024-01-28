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

from ndlpy import log
from ndlpy import access
from ndlpy.util.misc import remove_nan, to_valid_var
from ndlpy.config.context import Context


from ..util.widgets import (IntSlider, FloatSlider, Checkbox, RadioButtons, Text, Textarea, IntText, Combobox, Dropdown, Label, HTML, HTMLMath, DatePicker, Markdown, Flag, Select, SelectMultiple, IndexSelector, IndexSubIndexSelectorSelect, SaveButton, ReloadButton, CreateDocButton, CreateSummaryButton, CreateSummaryDocButton, BoundedFloatText, ScreenCapture, PopulateButton, ElementIntSlider, ElementFloatSlider, ElementCheckbox, ElementRadioButtons, ElementText, ElementTextarea, ElementIntText, ElementCombobox, ElementDropdown, ElementLabel, ElementHTML, ElementHTMLMath, ElementDatePicker, ElementMarkdown, ElementFlag, ElementSelect, ElementSelectMultiple, ElementBoundedFloatText)

from ..config import interface
from . import data


cntxt = Context(name="referia")
log = log.Logger(
    name=__name__,
    level=cntxt["logging"]["level"],
    filename=cntxt["logging"]["filename"],
)


def set_default_values(details, widget_type, reviewer):
    """
    Set default values for the widget based on provided details.

    :param details: Widget configuration details from YAML.
    :type details: dict
    :param widget_type: The widget class type.
    :type widget_type: class
    :param reviewer: The reviewer object.
    :type reviewer: Reviewer
    """
    store_name = details.get("field") or details.get("cache")
    default_value = details.get("value", 
                                details.get("args", {}).get("value", 
                                details.get("default", {}).get("value", 
                                widget_type(parent=reviewer, field_name=store_name).get_value())))

    reviewer._default_field_vals[store_name] = default_value

    # Handle default value source
    source = details.get("default", {}).get("source")
    if source and source in reviewer._data.columns:
        reviewer._default_field_source[store_name] = source
    elif source:
        reviewer._log.warning(f"Missing column source \"{source}\" in data.columns proposed for default value.")

def process_layout_and_local_args(process_details):
    """
    Process layout and local arguments from the provided details.

    :param process_details: Processed widget configuration details.
    :type process_details: dict
    :return: Processed args including layout and local settings.
    :rtype: dict
    """
    args = process_details.get("args", {})
    if "layout" in process_details:
        args["layout"] = Layout(**process_details["layout"])
    elif "layout" in args:
        args["layout"] = Layout(**args["layout"])

    if "local" in process_details:
        args["local"] = process_details["local"]

    return args
        

def extract_widget(details, reviewer, widgets):
    """
    Extract widget information from provided details and add it to the widgets collection.

    :param details: Widget configuration details from YAML.
    :type details: dict
    :param reviewer: The reviewer object.
    :type reviewer: Reviewer
    :param widgets: The widgets collection to add the extracted widget.
    :type widgets: WidgetsCollection
    :raises Exception: If widget type is not found.
    """
    widget_type = globals().get(details["type"])
    if not widget_type:
        raise Exception(f"Cannot find {details['type']} interaction type.")

    # Generate widget key
    store_name = details.get("field") or details.get("cache")
    widget_key = store_name or "".join(random.choices(string.ascii_letters, k=39))
    # Set default values
    if store_name:
        set_default_values(details, widget_type, reviewer)
        valid_name = to_valid_var(store_name)
        reviewer._column_names_dict[valid_name] = store_name
    else:
        valid_name = widget_key

    # Deep copy of details to avoid global modification
    process_details = json.loads(json.dumps(details))
    
    # Handle special case for HTML widgets
    if process_details["type"] in ["HTML", "HTMLMath", "Markdown"] and "description" not in process_details.get("args", {}):
        process_details["args"]["description"] = " "

    # Process layout and local arguments
    args = process_layout_and_local_args(process_details)

    # Process source arguments if provided
    source_args = details.get("source", {}).get("args", {})
    for arg, field in source_args.items():
        if arg not in args:
            reviewer.set_column(field)
            args[arg] = reviewer.get_value()

    # Handle refresh display setting
    refresh_display = details.get("refresh_display")
    if refresh_display is not None:
        if not isinstance(refresh_display, bool):
            raise ValueError(f"\"refresh_display\" entry should be either True or False.")
        args["refresh_display"] = refresh_display

    # Process element if present
    element = details.get("element")
    if element is not None:
        args["element"] = element
        widget_key += str(element)

    # Additional processing for specific fields
    for field in ["display", "tally", "liquid", "compute"]:
        if field in details and field not in args:
            args[field] = details[field]

    args["field_name"] = valid_name
    args["column_name"] = reviewer._column_names_dict[valid_name]
    args["parent"] = reviewer

    # Add the widget
    widgets.add(**{widget_key: widget_type(**args)})

def view(data):
    """Provide a view of the data that allows the user to verify some aspect of its quality."""
    fig, ax = plt.subplots(figsize=(8, 5))
    data.hist('Score', bins=np.linspace(-.5, 12.5, 14), width=0.8, ax=ax)
    ax.set_xticks(range(0,13))

def extract_load_scorer(details, reviewer, widgets):
    """Extract details from a separate file where they're specified."""
    # This is a link to a widget specificaiton stored in a file
    if "details" not in details:
        raise ValueError("Load reviewer needs to provide load details as entry under \"details\"")
    df,  newdetails = access.io.read_data(details["details"])
    for ind, series in df.iterrows():
        extract_scorer(remove_nan(series.to_dict()), reviewer, widgets)

def extract_group_scorer(details, reviewer, widgets):
    """Extract details that are clustered together in a group."""
    if "children" not in details:
        raise ValueError("group reviewer needs to provide a list of children under \"children\"")
    for child in details["children"]:
        if "name" in child and "name" in details and details["name"] is not None:
            child["name"] = details["name"] + "-" + child["name"]
        if "prefix" in details and details["prefix"] is not None:
            if "prefix" in child:
                child["prefix"] = details["prefix"] + child["prefix"]
            if "field" in child:
                child["field"] = details["prefix"] + child["field"]
        extract_scorer(child, reviewer, widgets)

def extract_composite_scorer(details, reviewer, widgets):
    """Extract details for a predefined composition of widgets."""
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
                #"field": "_" + prefix + " Criterion",
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
        extract_scorer(criterion, reviewer, widgets)
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
            extract_scorer(sub_score, reviewer, widgets)
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
            extract_scorer(sub_score, reviewer, widgets)
        return


    if details["type"] == "CriterionCommentRedAmberGreen":
        criterioncomment = json.loads(json.dumps(details))
        criterioncomment["type"] = "CriterionComment"

        prefix = details["prefix"]
        expectation = {
            "field": prefix + " Traffic",
            "type": "Dropdown",
            "args": {
                "placeholder": "Traffic Signal",
                "options": [
                    "",
                    "Red",
                    "Amber",
                    "Green",
                ],
                "description": "Traffic Signal",
            }
        }
        for sub_score in [criterioncomment, expectation]:
            extract_scorer(sub_score, reviewer, widgets)
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
            extract_scorer(sub_score, reviewer, widgets)
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
            extract_scorer(sub_score, reviewer, widgets)
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
            extract_scorer(sub_score, reviewer, widgets)

def extract_loop_scorer(details, reviewer, widgets):
    """Extract details for a loop of widgets."""
    if "start" not in details:
        raise ValueError("Missing start entry in loop")
    if "stop" not in details:
        raise ValueError("Missing stop entry in loop")
    loop = []
    for ent in ["start", "stop", "step"]:
        if ent in details:
            if type(details[ent]) is dict:
                loop.append(int(reviewer._data.view_to_value(details[ent])))
            else:
                loop.append(int(details[ent]))

    for element in range(*loop):
        
        sub_scores = details["body"]
        if type(sub_scores) is not list:
            sub_scores = [sub_scores]
        for sub_score in sub_scores:
            if not "local" in sub_score:
                sub_score["local"] = {}
            sub_score["local"]["element"] = element
            sub_score["element"] = element
            extract_scorer(sub_score, reviewer, widgets)


    
def extract_scorer(details, reviewer, widgets):
    """
    Interpret a scoring element from the yaml file and create the relevant widgets to be passed to the interact command. Widget is added to the widgets list.

    :param details: The details of the scoring element.
    :type details: dict
    :param reviewer: The reviewer object.
    :type reviewer: Reviewer
    :param widgets: The widgets to be displayed.
    :type widgets: WidgetCluster
    """

        
    if details["type"] == "precompute":
        # These are score items that can be precompute (i.e. not dependent on other rows). Once filled they are not changed.
        reviewer._precompute.append(details)
        
    elif details["type"] == "postcompute":
        # These are score items that are computed every time the row is updated.
        reviewer._postcompute.append(details)
        
    elif details["type"] == "load":
        load_widgets = LoadWidgetCluster(name="load", parent=reviewer)
        widgets.add(load_widgets)
        extract_load_scorer(details, reviewer, load_widgets)

    elif details["type"] == "group":
        group_widgets = GroupWidgetCluster(name="group", parent=reviewer)
        widgets.add(group_widgets)
        extract_group_scorer(details, reviewer, group_widgets)

    
    elif details["type"] in ["Criterion", "CriterionComment", "CriterionCommentDate", "CriterionCommentRedAmberGreen", "CriterionCommentRaisesMeetsLowers", "CriterionCommentRaisesMeetsLowersFlag", "CriterionCommentScore"]:
        if isinstance(widgets, CompositeWidgetCluster):
            extract_composite_scorer(details, reviewer, widgets)
        else:
            composite_widget = CompositeWidgetCluster(name=details["type"], parent=reviewer)
            widgets.add(composite_widget)
            extract_composite_scorer(details, reviewer, composite_widget)


    elif details["type"] == "loop":
        loop_widget = LoopWidgetCluster(name="loop", details=details, parent=reviewer)
        widgets.add(loop_widget)
        extract_loop_scorer(details, reviewer, loop_widget)
        
    else:
        # Widget is directly specified
        extract_widget(details, reviewer, widgets)
    

def nodes(chain, index=None):
    """Display the series of nodes """
    data = {}
    reviewer = {}
    oldkey=None
    while len(chain)>0:
        key, directory=chain.pop()
        data[key] = data.Data(directory=directory)
        if index is None and data[key].index is not None:
            index = data[key].index[0]
        reviewer[key] = Reviewer(index, data[key], directory=directory, viewer_inherit=False)
        if oldkey is not None:
            reviewer[oldkey].add_downstream_display(reviewer[key])
        reviewer[key].run()
        oldkey = key
                                
class WidgetCluster():
    """
    A class to hold a cluster of widgets.
    """
    def __init__(self, name, parent, viewer=False, **kwargs):
        """
        Create a cluster of widgets.

        :param name: The name of the cluster.
        :type name: str
        :param parent: The parent of the cluster.
        :type parent: Reviewer or WidgetCluster
        :param viewer: Whether the cluster is a viewer.
        """
        self._widget_dict = {}
        self._widget_list = []
        self._name = name
        self._viewer = viewer
        self._parent = parent
        self.add(**kwargs)

    def clear_children(self):
        """
        Clear the children of the cluster.
        """
        self.close()
        self._widget_dict = {}
        self._widget_list = []

    def close(self):
        """
        Close the widgets.
        """
        for entry in self._widget_list:
            if isinstance(entry, WidgetCluster):
                entry.close()
            else:
                self._widget_dict[entry].close()
                
    def has(self, key):
        """
        Check if the cluster has a widget with the given key.

        :param key: The key of the widget.
        :type key: str
        :return: Whether the cluster has the widget.
        :rtype: bool
        """
        if key in self.to_dict():
            return True
        else:
            return False

    def get(self, key):
        """
        Get the widget with the given key.

        :param key: The key of the widget.
        :type key: str
        :return: The widget.
        """
        return self.to_dict()[key]

    def refresh(self):
        """
        Refresh the widgets.
        """
        for entry in self._widget_list:
            if isinstance(entry, WidgetCluster):
                entry.refresh()
            else:
                self._widget_dict[entry].refresh()
        
    def add(self, cluster=None, **kwargs):
        """
        Add a widget to the cluster.

        :param cluster: The cluster to be added.
        :type cluster: WidgetCluster
        :param kwargs: The widgets to be added.
        :type kwargs: dict
        """
        if cluster is not None:
            cluster.add(**kwargs)
            self._widget_list.append(cluster)
        else:
            if kwargs != {}:
                self._widget_list += list(kwargs.keys())
                self._widget_dict = {**self._widget_dict, **kwargs}
        
    def update(self, **kwargs):
        """
        Update the widgets.

        :param kwargs: The widgets to be updated.
        :type kwargs: dict
        """
        for key, item in kwargs.items():
            if key in self._widget_dict:
                self._widget_dict[key] = item
            else:
                raise ValueError(f"Attempt to update widget \"{key}\" when it doesn't exist.")

    def to_markdown(self,skip=[]):
        """
        Convert the widget outputs into text.

        :param skip: The widgets to be skipped.
        """
        text = ""
        for entry in self._widget_list:
            if isinstance(entry, WidgetCluster):
                text += entry.to_markdown(skip=skip)
            else:
                if type(entry) is str:
                    entry = [entry]
                for key in entry:
                    if key not in skip:
                        text += self._widget_dict[key].to_markdown()
                        if text != "":
                            text+= "\n\n"
        return text
            
    def to_dict(self):
        """
        Convert the widget outputs into a dictionary.

        :return: The widgets.
        :rtype: dict
        """
        widgets = {}
        for entry in self._widget_list:
            if isinstance(entry, WidgetCluster):
                widgets = {**widgets, **entry.to_dict()}
            else:
                if type(entry) is str:
                    widgets[entry] = self._widget_dict[entry]
                else:
                    for key in entry:
                        widgets[key] = self._widget_dict[key]
        return widgets

    def display(self):
        """
        Display the widgets
        """
        for entry in self._widget_list:
            if isinstance(entry, WidgetCluster):
                entry.display()
            else:
                self._widget_dict[entry].display()
                
class DynamicWidgetCluster(WidgetCluster):
    """
    A class to hold a cluster of widgets that are dynamically reconstructed.
    """
    def __init__(self, details, **kwargs):
        """
        Create a cluster of widgets.

        :param details: The details of the scoring element.
        :type details: dict
        """
        self._details = details
        super().__init__(**kwargs)

    def refresh(self):
        """
        Refresh the widgets.
        """
        self.from_details()
        for entry in self._widget_list:
            if isinstance(entry, WidgetCluster):
                entry.refresh()
            else:
                self._widget_dict[entry].refresh()
        self.display()
                

    def from_details(self, details=None):
        """
        Reconstruct the widgets from the details.

        :param details: The details of the scoring element.
        :type details: dict
        """
        if details is None:
            details=self._details
        self.clear_children()
        extract_loop_scorer(details, self._parent, self)

class LoadWidgetCluster(WidgetCluster):
    """
    """
    def __init__(self, **kwargs):
        """
        Create a cluster of widgets.
        """
        super().__init__(**kwargs)

class GroupWidgetCluster(WidgetCluster):
    """
    """
    def __init__(self, **kwargs):
        """
        Create a cluster of widgets.
        """
        super().__init__(**kwargs)

class CompositeWidgetCluster(WidgetCluster):
    """
    """
    def __init__(self, **kwargs):
        """
        Create a cluster of widgets.
        """
        super().__init__(**kwargs)
    
class LoopWidgetCluster(DynamicWidgetCluster):
    """
    
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Reviewer:
    """
    A class to hold the display system.
    """
    def __init__(self, index=None, data=None, interface=None, system=None, viewer_inherit=True):
        """
        Create the display system.
        """
        if viewer_inherit:
            append = ["viewer"]
            ignore = []
        else:
            append = []
            ignore = ["viewer"]

        # Store the map between valid python variable names and data column name
        self._column_names_dict = {"_": "_"} # This initialisation handles case where a function gives no output.
        # Store the map between valid python variable names and data column names
        self._widgets = WidgetCluster(name="parent", parent=self)
        self._view_list = []
        self._dynamic_list = []
        self._selector_widget = None
        self._downstream_displays = []
        self._default_field_vals = pd.Series(dtype=object)
        self._default_field_source = pd.Series(dtype=object)

        if interface is None:
            raise TypeError("The interface argument is missing in Reviewer.")
        else:
            self._interface = interface

        if system is None:
            raise TypeError("The system argument is missing in Reviewer.")
        else:
            self._system = system

        if data is None:
            raise TypeError("The data argument is missing in Reviewer.")
        else:
            self._data = data

        if index is not None:
            # Widget isn't created yet so set index in data only.
            self._data.set_index(index)
            
        self._write_score = True
        self._select_subindex = False
        self._select_selector = False
        self._create_widgets()

    def _create_reload_button(self, config):
        """
        Create the reload button.

        :param config: The configuration file.
        :type config: dict
        """
        _reload_button = ReloadButton(parent=self)
        return WidgetCluster(name="reload_button", parent=self,  _reload_button=_reload_button)

    def _create_progress_bar(self, label):
        """
        Create the progress bar.

        :param label: The label for the progress bar.
        :type label: str
        """
        _progress_label = Markdown(description=" ", field_name=label)
        return WidgetCluster(name="progress_bar", parent=self,  viewer=True, _progress_label=_progress_label)

    def _create_viewer(self, views):
        """
        Create the viewer.

        :param views: The views to be displayed.
        :type views: dict
        """
        widgets = WidgetCluster(name="viewer", parent=self, viewer=True)
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
            widgets.add(**{label: Markdown(**args)})
        return widgets

    def _create_scorer(self, reviewers):
        """
        Create the reviewers from the config file.

        :param reviewers: The reviewers to be displayed.
        :type reviewers: dict
        """
        for reviewer in reviewers:
            extract_scorer(reviewer, self, self._widgets)

    def _create_documents(self, documents):
        """
        Process the document creators from the config file.

        :param documents: The documents to be created.
        :type documents: dict
        """
        widgets = WidgetCluster(name="documents", parent=self)
        for count, document in enumerate(documents):
            label = "_doc_button" + str(count)
            args = {
                "document": document,
                "type": document["type"],
                "parent": self,
            }
            widgets.add(**{label: CreateDocButton(**args)})
        return widgets

    def _create_summary(self, summaries):
        """
        Process the summary creators from the config file.

        :param summaries: The summaries to be created.
        :type summaries: dict
        """
        widgets = WidgetCluster(name="summaries", parent=self)
        for count, summary in enumerate(summaries):
            label = "_summary_button" + str(count)
            args = {
                "details": summary,
                "type": summary["type"],
                "parent": self,
            }
            widgets.add(**{label: CreateSummaryButton(**args)})
        return widgets
    
    def _create_summary_documents(self, documents):
        """
        Process the summary document creators from the config file.

        :param documents: The documents to be created.
        :type documents: dict
        """
        widgets = WidgetCluster(name="documents", parent=self)
        for count, document in enumerate(documents):
            label = "_summary_doc_button" + str(count)
            args = {
                "document": document,
                "type": document["type"],
                "parent": self,
            }
            widgets.add(**{label: CreateSummaryDocButton(**args)})
        return widgets

        
    def _create_widgets(self):
        """
        Create the widgets to be used for display.
        """
        if "scored" in self._interface:
            self._widgets.add(cluster=self._create_progress_bar(label="_progress_label"))

        # Process the viewer from the interface file.
        if "viewer" in self._interface:
            self._widgets.add(cluster=self._create_viewer(self._interface["viewer"]))

        self._widgets.add(self._create_reload_button(self._interface))
        # Process the reviewer from the interface file.
        if "scorer" in self._interface:
            self._widgets.add(self._create_scorer(self._interface["scorer"]))

        # Process the document creators from the interface file.
        if "documents" in self._interface:
            documents = self._interface["documents"]
            self._widgets.add(cluster=self._create_documents(documents))

        # Process the summaries from the interface file.
        if "summary" in self._interface:
            summaries = self._interface["summary"]
            self._widgets.add(cluster=self._create_summary(summaries))

        # Process the summary document creators from the interface file.
        if "summary_documents" in self._interface:
            documents = self._interface["summary_documents"]
            self._widgets.add(cluster=self._create_summary_documents(documents))

        _save_button = SaveButton(parent=self)
        self._widgets.add(cluster=WidgetCluster(name="save_button", parent=self, _save_button=_save_button))

    def add_views(self, label):
        """
        Maintain a list of widgets that stem from views

        :param label: The label for the view.
        """
        self._view_list.append(label)

    def add_dynamic(self, label):
        """
        Maintain a list of widgets that are dynamically reconstructed.

        :param label: The label for the dynamic widget.
        :type label: str
        """
        self._dynamic_list.append(label)
        
    def add_downstream_display(self, display):
        """
        Add a display that is downstream of this one to be updated.

        :param display: The display to be updated.
        :type display: Reviewer
        """
        self._downstream_displays.append(display)
        
    @property
    def index(self):
        """
        Get the index of the display system.

        :return: The index of the display system.
        :rtype: int
        """
        return self._data.index

    def get_index(self):
        """
        Get the index of the display system.

        :return: The index of the display system.
        :rtype: int
        """
        return self._data.get_index()

    def set_index(self, value):
        """
        Set the index of the display system.

        :param value: The index of the display system.
        :type value: int
        """
        oldval = self.get_index()
        if oldval != value:
            self._data.set_index(value)
            if self._selector_widget is not None:
                self._selector_widget.set_index(value)
            self.populate_display()
            for ds in self._downstream_displays:
                ds.set_index(value)
            
    def get_value(self):
        """
        Get the value of the focus element in the data of display system.

        :return: The value of the focus element in the data of the display system.
        :rtype: object
        """
        return self._data.get_value()

    def get_value_by_element(self, element):
        """
        Get an element of the value."""
        return self._data.get_value_by_element(element)
    
    def set_value_by_element(self, value, element, trigger_update=True):
        """Set an element of the value."""
        old_value = self.get_value_by_element(element)
        column = self.get_column()
        if value != old_value:
            log.debug(f"Column is \"{column}\" and element is \"{element}\". Old value is  \"{old_value}\" and new value is \"{value}\".")
            self._data.set_value_by_element(value, element)
            if trigger_update:
                self.value_updated()                            
        
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
        self.populate_display()

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
        
    def get_most_recent_screen_capture(self):
        """This function copys the name of the most recent screen capture to a column."""
        raise NotImplementedError("Copying screen capture not yet implemented.")
        filename = self._system.get_screen_capture(filename)
        self.set_column(column_name)
        self.set_value(filename)

    def run(self):
        """Run the reviewer to edit the data frame."""
        if self.index is not None:
            if "series" in self._interface:
                self.full_selector()
            else:
                self.select_index()
        self._widgets.display()
        self.populate_display()
        self.view_series()

    def template_to_value(self, template):
        """Convert a template to values."""
        if "use" in template:
            if template["use"] == "viewer":
                viewer = self._interface["viewer"] 
                if type(viewer) is not list:
                    viewer = [viewer]
                string = ""
                for view in viewer:
                    string += self._data.view_to_value(view)
                    string += "\n\n"
                return string
            elif template["use"] == "scorer":
                return self._widgets.to_markdown()
        else:
            return self._data.view_to_value(template)
        
    # Seems redundant, schedule for remove.
    # def view_scorer(self):
    #     text = ""
    #     return 
    #     for key, widget in self.widgets().items():
    #         text += widget.to_markdown()
    #     return text


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
        self.populate_display()

    def save(self):
        """Save output flows and reload inputs for any downstream displays."""
        self._data.save()
        for ds in self._downstream_displays:
            ds.load()
            ds.set_index(self.get_index())
            ds.populate_display()

        
    def load_input_flows(self):
        self._data.load_input_flows()

    def load_output_flows(self):
        self._data.load_output_flows()
        
            
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
            
            
        self._system.create_document(document, **args)

    

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
        self._system.create_summary(details, **args)

    def compute(self, compute):
        """Perform a computation as specified in the associated details."""
        self._data._compute.run(compute)
        
    def value_updated(self):
        """If a value in a row has been updated, modify other values"""

        # If index has changed, run computes.
        self._data._compute.run_all(post=True)

        # Need to determine if these should update series or data.
        # Update timestamp fields.
        today_val = pd.to_datetime("today")
        if "timestamp_field" in self._interface:
            timestamp_field = self._interface["timestamp_field"]
        else:
            timestamp_field = "Timestamp"
        if timestamp_field not in self._data.columns:
            self._data.add_column(timestamp_field)
        self._data.set_dtype(timestamp_field, "datetime64[ns]")

        self.set_column(timestamp_field)
        self.set_value(today_val,
                       trigger_update=False)
        if "created_field" in self._interface:
            created_field = self._interface["created_field"]
        else:
            created_field = "Created"

        if created_field not in self._data.columns:
            self._data.add_column(created_field)
        self._data.set_dtype(created_field, "datetime64[ns]")

        if created_field not in self._data.columns or data.empty(self._data.get_value_column(created_field)):
            self.set_column(created_field)
            self.set_value(today_val,
                           trigger_update=False)

        # Combinator is a combined field based on others
        if "combinator" in self._interface:
            for view in self._interface["combinator"]:
                if "field" in view:
                    col = view["field"]
                    del view["field"] #Prevent data reviewer trying to return field
                    combinator = self._data.viewer_to_value(view)
                    self.set_column(col)
                    self.set_value(combinator,
                                   trigger_update=False)
                else:
                    log.error("Missing key 'field' in combinator view.")



    
    def populate_display(self):
        """Update the widgets with defaults or values from the data"""
        self._widgets.refresh()
        if self._widgets.has("_progress_label"):
            total = self._data.to_score()
            if total > 0:
                scored = self._data.scored()
                remain = total - scored
                perc=scored/total*100

            else:
                scored = 0
                remain = total
                perc=0
            message = f"{remain} to go. Scored {scored} from {total} which is {perc:.3g}%"
            self._widgets.to_dict()["_progress_label"].set_value(message)


    def view_series(self):
        self._system.clear_temp_files()
        self._system.view_files(self._data)
        self._system.view_urls(self._data)
        self._system.edit_files(self._data)
