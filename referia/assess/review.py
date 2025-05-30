"""
Interactive review interfaces for assessment and data annotation.

This module provides classes and functions for creating and managing interactive
review interfaces. The core class is :class:`Reviewer`, which extends the DisplaySystem
from lynguine to provide a rich, web-based interface for data review and annotation.

The module implements a widget-based approach to building review interfaces, with
support for:

* Various input types (text fields, checkboxes, sliders, etc.)
* Document generation
* Summary creation
* Integration with the compute engine
* Dynamic widget creation and management

Key Components:
--------------
* Reviewer: Main class for interactive review interfaces
* WidgetCluster classes: Organize widgets into logical groups
* Extract functions: Parse configuration to build widget hierarchies
* Utility functions: Support widget creation and management

The interfaces are typically defined in YAML configuration files and loaded through
the Interface class, then passed to a Reviewer instance for display and interaction.
"""

import string
import random

import re

import numpy as np
import pandas as pd
import json

import traceback

import markdown
import warnings

from IPython import display
import matplotlib.pyplot as plt

from ipywidgets import jslink, jsdlink, Layout

from lynguine import log
from lynguine.util.misc import to_valid_var
from lynguine.config.context import Context
from lynguine.assess.display import WidgetCluster, DisplaySystem


from ..util.widgets import (
    IntSlider, FloatSlider, Checkbox, RadioButtons, Text, Textarea, IntText,
    Combobox, Dropdown, Label, HTML, HTMLMath, DatePicker, Markdown, Flag,
    Select, SelectMultiple, IndexSelector, IndexSubIndexSelectorSelect,
    SaveButton, ReloadButton, CreateDocButton, CreateSummaryButton,
    CreateSummaryDocButton, BoundedFloatText, ScreenCapture, PopulateButton,
    ElementIntSlider, ElementFloatSlider, ElementCheckbox, ElementRadioButtons,
    ElementText, ElementTextarea, ElementIntText, ElementCombobox, ElementDropdown,
    ElementLabel, ElementHTML, ElementHTMLMath, ElementDatePicker, ElementMarkdown,
    ElementFlag, ElementSelect, ElementSelectMultiple, ElementBoundedFloatText
)

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

    # Default value initialization
    default_value = details.get("value",
                                details.get("args", {}).get("value",
                                widget_type(parent=reviewer, field_name=store_name).get_value()))

    # Handle 'default' key when it's a dictionary or a string
    default_details = details.get("default")
    if isinstance(default_details, dict):
        default_value = default_details.get("value", default_value)
        source = default_details.get("source")
    elif isinstance(default_details, str):
        source = default_details
    else:
        source = None

    # Set default value
    if isinstance(reviewer._default_field_vals, pd.Series):
        reviewer._default_field_vals[store_name] = default_value
    else:
        reviewer._default_field_vals[store_name] = default_value

    # Set default source
    if source:
        if source in getattr(reviewer._data, 'columns', []):
            if isinstance(reviewer._default_field_source, pd.Series):
                reviewer._default_field_source[store_name] = source
            else:
                reviewer._default_field_source[store_name] = source
        else:
            log.warning(f"Missing column source \"{source}\" in data.columns proposed for default value.")


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
        raise ValueError(f"Cannot find {details['type']} interaction type.")

    if "compute" in details:
        log.debug(f"Adding widget targeting \"{details.get('field')}\" with compute function.")
    # Generate widget key
    store_name = details.get("field") or details.get("cache")
    if details.get("name") is None:
        details["name"] = "".join(random.choices(string.ascii_letters, k=39))

    if store_name is None:
        widget_key = "_" + details.get("name")
    else:
        widget_key = store_name

    # Set default values
    if store_name:
        set_default_values(details, widget_type, reviewer)
        valid_name = to_valid_var(store_name)
        reviewer._column_names_dict[valid_name] = store_name
    else:
        valid_name = None

    # Deep copy of details to avoid global modification
    process_details = json.loads(json.dumps(details))

    # Ensure 'args' dictionary exists in process_details
    if "args" not in process_details:
        process_details["args"] = {}
        
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

    if valid_name is not None:       
        args["field_name"] = valid_name
        args["column_name"] = reviewer._column_names_dict[valid_name]
    else:
        args["field_name"] = to_valid_var(widget_key) # Use widget key to provide a unique field name
        args["column_name"] = "_" # There's no column associated with the widget.
        
    args["parent"] = reviewer

    # Add the widget
    if "compute" in args:
        log.debug(f"Adding widget \"{widget_key}\" with compute function of widget_type \"{widget_type}\".")
    widgets.add(**{widget_key: widget_type(**args)})


def extract_review(details, reviewer, widgets):
    """
    Interpret a review element from the yaml file and create the relevant widgets to be passed to the interact command. Widget is added to the widgets list.

    :param details: The details of the review element.
    :type details: dict
    :param reviewer: The reviewer object.
    :type reviewer: Reviewer
    :param widgets: The widgets to be displayed.
    :type widgets: WidgetCluster
    """

    log.debug(f"Extracting review element: {details}")
    if details["type"] == "precompute":
        # These are score items that can be precompute (i.e. not dependent on other rows). Once filled they are not changed.
        if isinstance(details["specifications"], list):
            reviewer._data._precompute.extend(details["specifications"])
        else:
            reviewer._data._precompute.append(details["specifications"])
            
    elif details["type"] == "postcompute":
        # These are score items that are computed every time the row is updated.
        if isinstance(details["specifications"], list):
            reviewer._data._postcompute.extend(details["specifications"])
        else:
            reviewer._data._postcompute.append(details["specifications"])
        
    elif details["type"] == "load":
        load_widgets = LoadWidgetCluster(name="load", parent=reviewer)
        widgets.add(load_widgets)
        for detail in details["entries"]:
            extract_review(detail, reviewer, load_widgets)

    elif details["type"] == "group":
        group_widgets = GroupWidgetCluster(name="group", parent=reviewer)
        widgets.add(group_widgets)
        for detail in details["entries"]:
            extract_review(detail, reviewer, group_widgets)

    
    elif details["type"] == "composite":
        composite_widget = CompositeWidgetCluster(name=details["type"], parent=reviewer)
        widgets.add(composite_widget)
        for sub_score in details["entries"]:
            extract_review(sub_score, reviewer, composite_widget)


    elif details["type"] == "loop":
        loop_widget = LoopWidgetCluster(name="loop", details=details, parent=reviewer, start=details["start"], stop=details["stop"], step=details["step"])
        widgets.add(loop_widget)
        for sub_score in details["entries"]:
            extract_review(sub_score, reviewer, loop_widget)
        
    else:
        # Widget is directly specified
        extract_widget(details, reviewer, widgets)

def view(data):
    """
    Provide a view of the data that allows the user to verify some aspect of its quality.
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    data.hist('Score', bins=np.linspace(-.5, 12.5, 14), width=0.8, ax=ax)
    ax.set_xticks(range(0,13))


def expand_loop_review(details, reviewer):
    """
    Extract details for a loop of widgets. The loop is defined by a
    start, stop and step value. The body of the loop is defined by
    body which is a list of widgets. The element value is passed to
    the body widgets so that the widgets can be updated for each
    element in the loop.

    :param details: The details of the scoring element.
    :type details: dict
    :param reviewer: The reviewer object.
    :type reviewer: Reviewer
    :param widgets: The widgets to be displayed.
    :type widgets: WidgetCluster

    """
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

    return_details = []
    for element in range(*loop):
        sub_scores = details["body"]
        if type(sub_scores) is not list:
            sub_scores = [sub_scores]
        for sub_score in sub_scores:
            if not "local" in sub_score:
                sub_score["local"] = {}
            sub_score["local"]["element"] = element
            sub_score["element"] = element
            return_details.append(sub_score)
    return return_details

    
    

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
                                
                
class LoadWidgetCluster(WidgetCluster):
    """A widget cluster for loading widgets."""
    pass

class GroupWidgetCluster(WidgetCluster):
    """A widget cluster for grouping widgets."""
    pass

class CompositeWidgetCluster(WidgetCluster):
    """A widget cluster for composite widgets."""
    pass

class DynamicWidgetCluster(WidgetCluster):
    """
    A widget cluster that dynamically rebuilds its contents as needed.
    
    This class extends the basic WidgetCluster with the ability to reconstruct
    its child widgets based on configuration details. It's particularly useful
    for widgets that need to change based on user interaction or data updates.
    
    DynamicWidgetCluster stores its configuration details and can refresh itself
    by recreating its child widgets from these details, allowing for adaptive
    user interfaces that respond to changing conditions.
    
    :param details: Configuration details for the widget cluster
    :type details: dict
    :param kwargs: Additional keyword arguments passed to the parent class
    
    .. seealso::
        :class:`LoopWidgetCluster`
            A specialized dynamic widget cluster for loop-based widget creation
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
        super().refresh()
        self.display()

    def from_details(self, details=None):
        """
        Reconstruct the widgets from the details.

        :param details: The details of the scoring element.
        :type details: dict
        """
        if details is None:
            details = self._details
        self.clear_children()
        extract_loop_review(details, self._parent, self)

class LoopWidgetCluster(DynamicWidgetCluster):
    """A widget cluster for loop widgets."""
    pass

class Reviewer(DisplaySystem):
    """
    Interactive review interface for assessment and data annotation.
    
    The Reviewer class provides a web-based interactive interface for reviewing, 
    annotating, and processing data. It extends the DisplaySystem from lynguine
    and adds functionality for document generation, summaries, and advanced 
    widget management.
    
    This class is the main entry point for creating interactive review interfaces
    in referia. It manages a collection of widgets organized into clusters and
    handles events, data updates, and view rendering.
    
    .. rubric:: Inheritance
    
    This class inherits from lynguine.assess.display.DisplaySystem and extends it with:
    
    * Document generation from templates
    * Summary creation and aggregation
    * Advanced widget management and dynamic UI creation
    * Integration with the referia compute engine
    
    .. rubric:: Key Features
    
    * Interactive widget-based UI for data review
    * Support for various input types (text, checkbox, sliders, etc.)
    * Document generation from templates
    * Summary creation and reporting
    * Integration with the Compute engine for data processing
    * Real-time reactivity to data changes
    
    :param index: The index of the data to display, defaults to None
    :type index: str or int, optional
    :param data: The data to be displayed and manipulated, defaults to None
    :type data: lynguine.assess.data.CustomDataFrame, optional
    :param interface: The interface configuration defining the review layout, defaults to None
    :type interface: referia.config.interface.Interface, optional
    :param system: The system configuration, defaults to None
    :type system: str, optional
    :param viewer_inherit: Whether the viewer inherits a parent viewer, defaults to True
    :type viewer_inherit: bool, optional
    
    .. rubric:: Example
    
    Basic usage:
    
    .. code-block:: python
    
        from referia.assess.review import Reviewer
        from referia.config.interface import Interface
        from lynguine.assess.data import CustomDataFrame
        
        # Create data
        data = CustomDataFrame({"text": ["Sample review text"], "score": [0]})
        
        # Load interface configuration
        interface = Interface(config_file="review_config.yml")
        
        # Create reviewer
        reviewer = Reviewer(data=data, interface=interface)
        
        # Display the review interface
        reviewer.run()
    
    .. seealso::
        :class:`lynguine.assess.display.DisplaySystem`
            Parent class providing base display functionality
        :class:`referia.assess.compute.Compute`
            Computation engine used with Reviewer
        :class:`lynguine.assess.data.CustomDataFrame`
            Data class used with Reviewer
    """
    def __init__(self, index=None, data=None, interface=None, system=None, viewer_inherit=True):
        """
        Create the display system.

        :param index: The index of the data.
        :type index: str
        :param data: The data to be displayed.
        :type data: pd.DataFrame
        :param interface: The interface to be used.
        :type interface: str
        :param system: The system to be used.
        :type system: str
        :param viewer_inherit: Whether the viewer inherits a parent viewer.
        :type viewer_inherit: bool
        """
        super().__init__(index, data, interface, system)        
        
        if viewer_inherit:
            append = ["viewer"]
            ignore = []
        else:
            append = []
            ignore = ["viewer"]

        # Store the map between valid python variable names and data column name
        self._column_names_dict = {"_": "_"} # This initialisation handles case where a function gives no output.
        self._view_list = []
        self._dynamic_list = []
        self._selector_widget = None
        self._default_field_vals = pd.Series(dtype=object)
        self._default_field_source = pd.Series(dtype=object)
            
        self._write_score = True
        self._select_subindex = False
        self._select_selector = False
        self._create_widgets()

              
    def set_default_field_value(self, field, value):
        """
        Set the default value for a specified field.
        
        This method establishes a default value for a data field that will be used
        when no explicit value is provided. Default values are stored in the 
        _default_field_vals series and are used to initialize widgets when they
        are created.
        
        :param field: The name of the field to set the default value for
        :type field: str
        :param value: The default value to assign to the field
        :type value: any
        :return: None
        :rtype: None
        
        .. code-block:: python
            
            # Set a default value for a field
            reviewer.set_default_field_value("comment", "No comment provided")
        """
        self._default_field_vals[field] = value

    def set_default_field_source(self, field, source):
        """
        Set the default source for the field.

        :param field: The field to set the default source for.
        :type field: str
        :param source: The source to set.
        :type source: str
        """
        self._default_field_source[field] = source
        
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
        widgets = WidgetCluster(name="viewer", parent=self._widgets, viewer=True)
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

    def _create_review(self, reviewers):
        """
        Create the reviewers from the config file.

        :param reviewers: The reviewers to be displayed.
        :type reviewers: dict
        """
        widgets = WidgetCluster(name="review_widgets", parent=self._widgets)
        for reviewer in reviewers:
            extract_review(reviewer, self, widgets)
        return widgets

    def _create_documents(self, documents):
        """
        Process the document creators from the config file.

        :param documents: The documents to be created.
        :type documents: dict
        """
        widgets = WidgetCluster(name="documents", parent=self._widgets)
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
        widgets = WidgetCluster(name="summaries", parent=self._widgets)
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
        widgets = WidgetCluster(name="documents", parent=self._widgets)
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

        # Process the review from the interface file.
        if "review" in self._interface:
            self._widgets.add(self._create_review(self._interface["review"]))
            
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
        
    def get_selectors(self) -> list:
        """
        Get the list of valid selectors of the display system.

        :return: The selectors of the display system.
        :rtype: list
        """
        return self._data.get_selectors()

    def get_selector(self):
        """
        Get the selector of the display system.

        :return: The selector of the display system.
        :rtype: valid selector (column of a series portion(s) of the dataframe)
        """
        return self._data.get_selector()

    def set_selector(self, value) -> None:
        """
        Set the selector of the display system.

        :param value: The selector of the display system.
        :type value: valid selector (column of the dataframe)
        """
        self._data.set_selector(value)

    def get_indices(self) -> pd.Index:
        """
        Get the list of valid indices of the display system.

        :return: The indices of the display system.
        :rtype: pd.Index
        """
        return self._data.index

    def get_subindices(self) -> pd.Index:
        """
        Get the list of valid subindices of the display system.

        :return: The subindices of the display system.
        :rtype: pd.Index
        """
        return self._data.get_subindices()

    def get_subindex(self):
        """
        Get the subindex of the display system.

        :return: The subindex of the display system.

        """
        return self._data.get_subindex()

    def set_subindex(self, value):
        """
        Set the subindex of the display system.

        :param value: The subindex of the display system.
        :type value: valid subindex
        """
        self._data.set_subindex(value)
        self.populate_display()

    def add_row(self, index, values=None):
        """
        Add a row with a given index to the series.
        """
        self._data.add_row(index, values)

    def add_series_row(self, values=None):
        """
        Add a row with a given index to the series.
        """
        self._data.add_series_row(index=self._data.get_index(), values=values)        
        
    def full_selector(self):
        """
        Select a selector and subindex from the data

        """
        self._selector_widget=IndexSubIndexSelectorSelect(parent=self)
        self._selector_widget.display()

    def select_index(self):
        """
        Select an index from the data
        """
        self._selector_widget=IndexSelector(parent=self)
        self._selector_widget.display()

    def select_selector(self):
        """
        Select a selector from the data

        :return: The selector selected.
        """
        self._selector_widget=IndexSubIndexSelectorSelect(parent=self)
        self._selector_widget.display()

    def select_subindex(self):
        """
        Select a subindex from the data

        :return: The subindex selected.
        """
        self._selector_widget=IndexSubIndexSelectorSelect(parent=self)
        self._selector_widget.display()

    def get_select_selector(self):
        """
        Get state of selector selection.

        :return: The state of the selector selection.
        """
        return self._select_selector

    def set_select_selector(self, value):
        """
        Set state of selector selection.

        :param value: The value of the selector selection.
        """
        self._select_selector = value

    def get_select_subindex(self):
        """
        Get state of subindex selection.

        :return: The state of the subindex selection.
        :rtype: valid index
        """
        return self._select_subindex

    def set_select_subindex(self, value) -> None:
        """
        Set state of subindex selection.

        :param value: The value of the subindex selection.
        :type value: valid index
        """
        self._select_subindex = value
        
    def get_most_recent_screen_capture(self):
        """
        This function copys the name of the most recent screen capture to a column.
        """
        raise NotImplementedError("Copying screen capture not yet implemented.")
        filename = self._system.get_screen_capture(filename)
        self.set_column(column_name)
        self.set_value(filename)

    def run(self):
        """
        Display the interactive review interface.
        
        This method is the main entry point for displaying and interacting with the
        review interface. It initializes the appropriate selectors based on configuration,
        displays the widget hierarchy, and populates the display with current data.
        
        When called:
        1. If an index is set, it displays either the selector or full selector based on configuration
        2. Renders all widgets in the interface
        3. Populates the display with current data values
        4. Initializes series view if configured
        
        This is typically the last method called after initializing a Reviewer instance.
        
        :return: None
        :rtype: None
        
        .. code-block:: python
            
            # Create and display a reviewer
            reviewer = Reviewer(data=data, interface=interface)
            reviewer.run()  # Displays the interactive interface
            
        .. note::
            This method must be called in a Jupyter notebook environment for the
            interactive widgets to display properly.
        """
        if self.index is not None:
            if "series" in self._interface:
                self.full_selector()
            else:
                self.select_index()
        self._widgets.display()
        self.populate_display()
        self.view_series()

    def template_to_value(self, template : dict) -> str:
        """
        Process a template configuration into its rendered text value.
        
        This method converts template definitions into actual content by applying
        the appropriate rendering strategy based on the template type. It handles
        special template types that reference UI components or data views.
        
        :param template: Template configuration dictionary
        :type template: dict
        :return: The rendered text content
        :rtype: str
        
        The template can use special keys:
        
        * **use**: Defines a template source type
          - "viewer": Uses content from the viewer configuration
          - "scorer"/"review": Uses content from review widgets
        
        If no "use" key is present, the template is processed as a standard
        data view template.
        
        .. code-block:: python
        
            # Example: Render content from viewer
            content = reviewer.template_to_value({"use": "viewer"})
            
            # Example: Render content from review widgets
            content = reviewer.template_to_value({"use": "review"})
            
            # Example: Render content from a custom view template
            content = reviewer.template_to_value({"display": {"field": "comments"}})
        """
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
            elif template["use"] == "scorer" or template["use"] == "review":
                return self._widgets.to_markdown()
        else:
            return self._data.view_to_value(template)
        
    # Seems redundant, schedule for remove.
    # def view_review(self):
    #     text = ""
    #     return 
    #     for key, widget in self.widgets().items():
    #         text += widget.to_markdown()
    #     return text


    def load_flows(self, reload : bool = False) -> None:
        """
        Load flows from data stores

        :param reload: Whether to reload the flows.
        :type reload: bool
        """
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
        
    def create_document(self, document : dict, summary : bool = False) -> None:
        """
        Generate a document from templates and data.
        
        This method creates documents (such as reports, reviews, or summaries) based on
        templates defined in the configuration. It processes template fields, renders content
        from data, and passes the result to the system's document creation mechanism.
        
        The document dictionary can contain various fields that define the document's content
        and structure. Special fields like "header", "body", "footer", and "content" receive
        special handling, with "body" being copied to "content" and headers/footers being
        concatenated with the content.
        
        :param document: Document configuration dictionary containing template definitions
                         and other document parameters
        :type document: dict
        :param summary: Whether to create a summary document that aggregates content
                        across multiple data indices
        :type summary: bool
        :return: None
        :rtype: None
        
        .. note::
            Template fields can contain special rendering instructions:
            
            * "tally": Aggregate values
            * "display": Format for display
            * "list": Process as list
            * "join": Join elements
            * "liquid": Process as liquid template
            * "use": Reference viewer or review content
            
        .. code-block:: python
        
            # Example document configuration
            doc_config = {
                "type": "markdown",
                "header": "# Review Summary",
                "body": {"use": "review"},
                "footer": "Generated on {{date}}",
                "filename": "review_{{index}}.md"
            }
            
            # Generate the document
            reviewer.create_document(doc_config)
            
        .. seealso::
            :meth:`template_to_value` for details on template processing
        """
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

    def create_summary(self, details : "lynguine.config.interface.Interface") -> None:
        """
        Create a summary file given the relevant information

        :param details: The details of the summary.
        :type details: lynguine.config.interface.Interface
        """
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

    def compute(self, compute : "lynguine.config.interface.Interface") -> None:
        """
        Perform a computation as specified in the associated details.

        :param compute: The computation to be performed.
        :type compute: lynguine.config.interface.Interface
        """
        self._data._compute.run(compute)

    def compute_onchange(self):
        """
        Process computation triggered by widget value changes.
        
        This method is called when a widget value changes and triggers the compute
        infrastructure to perform calculations that depend on the changed value.
        It retrieves the current index and column information and passes them to
        the compute engine's run_onchange method.
        
        This creates a reactive computation network where changes to input values
        automatically update dependent values based on compute definitions in the
        configuration.
        
        :return: None
        :rtype: None
        
        .. note::
            This method is typically called internally by widgets when their
            values change, not directly by users.
            
        .. seealso::
            :meth:`referia.assess.compute.Compute.run_onchange` for details on the
            computation process
        """
        if self.index is not None:
            # Get the data once
            data = self._data
            compute_index = data.get_compute_index(self.index)
            if "compute" in self._interface and data is not None:
                if compute_index is not None:
                    if self.column_name is not None:
                        self._system.compute.run_onchange(data, compute_index, self.column_name)


    def value_updated(self):
        """
        Process all updates triggered by a value change in the data.
        
        This method is called when a value in a data field is updated and handles
        all the necessary follow-up actions, including:
        
        1. Triggering compute functions that depend on the changed value
        2. Updating timestamp fields (modified and created dates)
        3. Updating combinator fields that aggregate multiple values
        
        The method follows these steps:
        - Calls compute_onchange() to trigger dependent computations
        - Updates the modification timestamp for the changed field
        - Creates a creation timestamp if one doesn't exist
        - Updates any combinator fields defined in the interface
        
        :return: None
        :rtype: None
        
        .. note::
            This method is automatically called by widgets when their values change,
            and typically should not be called directly by users.
            
        .. seealso::
            :meth:`compute_onchange` for the computation part of the update process
        """

        # TK Perform updates triggered by value changes.
        # If index has changed, run computes.
        column = self.get_column()
        log.debug(f"Value updated. Index is \"{self.get_index()}\" and column is \"{column}\".")
        self.compute_onchange()
        log.debug(f"On change computes complete.")

        # TK Create a new compute type "onchange" or similar and place these within.
        # Need to determine if these should update series or data.

        # Update timestamp field.
        log.debug(f"Updating timestamp field.")
        today_val = pd.to_datetime("today")

        # Set the modified field
        modified_suffix = self._interface["modified_suffix"]
        modified_field = column + "_" + modified_suffix
        self._data.set_dtype(modified_field, "datetime64[ns]")
        self.set_column(modified_field)
        self.set_value(today_val, trigger_update=False)

        # Set the created field
        log.debug(f"Setting created field.")
        created_suffix = self._interface["created_suffix"]
        created_field = column + "_" + created_suffix
        self._data.set_dtype(created_field, "datetime64[ns]")
        if data.empty(self._data.get_value_column(created_field)):
            self.set_column(created_field)
            self.set_value(today_val, trigger_update=False)

        
        # Combinator is a combined field based on others
        if "combinator" in self._interface:
            log.debug(f"Updating combinator field.")
            for view in self._interface["combinator"]:
                if "field" in view:
                    col = view["field"]
                    del view["field"] #Prevent data reviewer trying to return field
                    combinator = self._data.viewer_to_value(view)
                    self.set_column(col)
                    self.set_value(combinator, trigger_update=False)
                else:
                    log.error("Missing key 'field' in combinator view.")

        self.set_column(column)

        
    def populate_display(self) -> None:
        """
        Update the widgets with defaults or values from the data

        :return: None
        """
        log.debug("Populating display.")
        try:
            self._widgets.refresh()
        except Exception as e:
            log.error(f"Error refreshing widgets: {e}")
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e
        log.debug("Display populated.")

        if self._widgets.has("_progress_label"):
            log.debug("Updating progress label.")
            try:
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
            except Exception as e:
                log.error(f"Error updating progress label: {e}")
                log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
                raise e


    def view_series(self):
        """
        Display files, URLs and editable files for the current data.
        
        This method triggers the system to:
        1. Clear any temporary files
        2. Display files associated with the current data
        3. Display URLs referenced in the data
        4. Open editors for editable files
        
        This is typically called as part of the run method to initialize
        the full review interface.
        
        :return: None
        """
        self._system.clear_temp_files()
        self._system.view_files(self._data)
        self._system.view_urls(self._data)
        self._system.edit_files(self._data)
