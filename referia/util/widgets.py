import os
import sys
import glob
import traceback

import IPython
import ipywidgets as ipyw

from pandas.api.types import is_string_dtype, is_numeric_dtype, is_bool_dtype

from lynguine.util.misc import markdown2html, html2markdown

from .misc import notempty, yyyymmddToDatetime, datetimeToYyyymmdd, filename_to_binary

from lynguine import log
from lynguine.config.context import Context


cntxt = Context(name="referia")
log = log.Logger(
    name=__name__,
    level=cntxt["logging"]["level"],
    filename=cntxt["logging"]["filename"],
)


#other = [jslink, jsdlink, MyCheckbox, MyFileChooser]

list_stateful_widgets = [
    {
        "name" : "IntSlider",
        "function" : ipyw.IntSlider,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },
    {
        "name" : "FloatSlider",
        "function" : ipyw.FloatSlider,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },
    {
        "name" : "Checkbox",
        "function" : ipyw.Checkbox,
        "default_args" : {},
        "docstr" : None,
        "conversion" : bool,
        "reversion" : None,
    },
    {
        "name" : "Flag",
        "function" : ipyw.Checkbox,
        "default_args" : {},
        "docstr" : None,
        "conversion" : bool,
        "reversion" : None,
    },
    {
        "name" : "PngImageFile",
        "function": ipyw.Image,
        "default_args" : {
            "format" : "png",
        },
        "docstr": None,
        "conversion" : filename_to_binary,
        "reversion" : None,
    },
    {
        "name" : "Text",
        "function" : ipyw.Text,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },
    {
        "name" : "Textarea",
        "function" : ipyw.Textarea,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },
    {
        "name" : "IntText",
        "function" : ipyw.IntText,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },
    {
        "name" : "BoundedFloatText",
        "function" : ipyw.BoundedFloatText,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },
    {
        "name" : "Combobox",
        "function" : ipyw.Combobox,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },
    {
        "name" : "Dropdown",
        "function" : ipyw.Dropdown,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Label",
        "function" : ipyw.Label,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },
    {
        "name" : "Layout",
        "function" : ipyw.Layout,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },
    {
        "name" : "HTML",
        "function" : ipyw.HTML,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },
    {
        "name" : "RadioButtons",
        "function" : ipyw.RadioButtons,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },            
    {
        "name" : "Select",
        "function" : ipyw.Select,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },            
    {
        "name" : "SelectMultiple",
        "function" : ipyw.SelectMultiple,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },            
    {
        "name" : "HTMLMath",
        "function" : ipyw.HTMLMath,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
        "reversion" : None,
    },
    {
        "name" : "Markdown",
        "function" : ipyw.HTMLMath,
        "default_args" : {},
        "docstr" : None,
        "conversion" : markdown2html,
        "reversion" : html2markdown,
    },
    {
        "name" : "DatePicker",
        "function" : ipyw.DatePicker,
        "default_args" : {},
        "docstr" : None,
        "conversion" : yyyymmddToDatetime,
        "reversion" : None, #datetimeToYyyymmdd not used as conversion is only to tidy up
    },
]

class ReferiaWidget():
    """
    Base class for Referia widgets. ReferiaWidgets are wrappers around ipywidgets in an effort to avoid dependency injection.

    """
    def __init__(self, **args):
        """
        Initialise the widget.

        :param args: The arguments for the widget.
        :type args: dict
        """
        
        self._parent = None
        self.private = True

        # Set the widget function. Should be a valid ipywidget function.
        if "function" in args:
            log.debug(f"Setting widget function to \"{args['function']}\".")
            self._ipywidget_function = args["function"]
            del args["function"]
        else:
            widget_function = self._default_widget()
            log.warning(f"No function specified for widget. Setting to default \"{widget_function}\".")
            self._ipywidget_function = widget_function


        # Set the description for the widget.
        if "description" in args:
            self._description = args["description"]
        else:
            self._description = None
            
        if "parent" in args:
            self._parent = args["parent"]
            del args["parent"]

        # Delete other arguments not used by widget
        for key in ["type", "document", "target", "details", "compute"]:
            if key in args:
                del args[key]
        self._create_widget(args)

    @property
    def name(self):
        """
        Return the name of the widget.
        """
        raise NotImplementedError("Name must be implemented in subclass.")
    
    @classmethod    
    def _default_widget(cls):
        """
        Return the default widget function.

        :return: The default widget function.
        :rtype: function
        """
        raise NotImplementedError("Default widget function must be implemented in subclass.")

    @property
    def description(self):
        """
        Return the description of the widget.
        """
        self._description
        
    def _create_widget(self, args):
        """
        Create the widget.

        :param args: The arguments for the widget.
        :type args: dict
        """

        log.debug(f"Creating widget with arguments \"{args}\".")
        self.widget = self._ipywidget_function(**args)
        self._widget_events()

    def _widget_events(self):
        """
        Create any relevant widget event handlers.
        """

        log.debug(f"Creating widget events for widget \"{self._ipywidget}.\".")
        pass

    def close(self):
        """
        Close the widget.
        """
        self.widget.close()
        
    def on_click(self, b):
        """
        Handle the click event.

        :param b: The widget.
        """
        raise NotImplementedError("on_click method must be implemented in subclass.")

    def refresh(self):
        """
        Refresh the widget.
        """
        raise NotImplementedError("refresh method must be implemented in subclass.")

    @property
    def widget(self):
        """
        Return the ipywidget.
        """
        return self._ipywidget

    @widget.setter
    def widget(self, value):
        """
        Set the ipywidget.

        :param value: The value to set.
        """
        self._ipywidget = value
    
    @property
    def private(self):
        """
        Return whether the widget is private. A private widget does not update the parent data.
        """
        return self._private

    @private.setter
    def private(self, value):
        #if not is_bool_dtype(value):
        #    raise ValueError("Private must be set as bool (True/False)")
        """
        Set whether the widget is private. A private widget does not update the parent data.

        :param value: The value to set.
        :type value: bool
        """
        self._private = value

    def display(self):
        """
        Display the widget.
        """
        IPython.display.display(self.widget)

    def null(self, void):
        pass

    def to_markdown(self):
        return ""
        
class ReferiaStatefulWidget(ReferiaWidget):
    """
    Base class for Referia stateful widgets.
    """
    def __init__(self, **args):
        """
        Initialise the widget.

        :param conversion: The conversion function for setting the widget value.
        :type conversion: function
        :param reversion: The reversion function for getting the widget value.
        :type reversion: function
        :param display: The display for the widget.
        :type display: function
        :param column_name: The column name for the widget.
        :type column_name: str
        :param field_name: The field name for the widget.
        :type field_name: str
        :param refresh_display: Whether to refresh the display when the widget value changes.
        :type refresh_display: bool
        :param value: The default value for the widget.
        :type value: any
        :param description: The description for the widget.
        :type description: str
        """
        self._conversion = None
        self._reversion = None
        self._viewer = {}
        self._column_name = None
        self._field_name = None

        # Conversion and reversion functions for setting and getting the widget value. They ensure that the widget value is translated to the right format.
        if "conversion" in args:
            self._conversion = args["conversion"]
            del args["conversion"]            
        if "reversion" in args:
            self._reversion = args["reversion"]
            del args["reversion"]

        # Display, tally, list, join, liquid are used for the _viewer structure to generate the widget value. For example liquid allows the use of liquid lanaguage when generating the widget value.    
        if "display" in args:
            self._viewer["display"] = args["display"]
            del args["display"]
        if "tally" in args:
            self._viewer["tally"] = args["tally"]
            del args["tally"]
        if "list" in args:
            self._viewer["list"] = args["list"]
            del args["list"]
        if "join" in args:
            self._viewer["join"] = args["join"]
            del args["join"]
        if "liquid" in args:
            self._viewer["liquid"] = args["liquid"]
            del args["liquid"]
        if "local" in args:
            self._viewer["local"] = args["local"]
            del args["local"]
        if "conditions" in args:
            self._viewer["conditions"] = args["conditions"]
            del args["conditions"]

            
        if "column_name" in args:
            self._column_name = args["column_name"]
            del args["column_name"]
        if "field_name" in args:
            self._field_name = args["field_name"]
            del args["field_name"]
        else:
            self._field_name = "_No Field Name"
            

        if "refresh_display" in args:
            self._refresh_display = args["refresh_display"]
            del args["refresh_display"]
        else:
            self._refresh_display = False
        
        super().__init__(**args)

        # If there's a value provided in args set the widget value to that value.
        if "value" in args:
            self._default_value = args["value"]
            self.set_value(args["value"]) # TK should this be set silently?
        else:
            self._default_value = self._ipywidget_function().value

            
        # If the widget's field name starts with a "_" then it is assumed to be private
        # A private field is one that doesn't update parent data when it's changed.
        if self._field_name is not None and self._field_name[0] == "_": 
            self.private = True
        else:
            self.private = False

        if self.private and "description" not in args: 
            args["descripton"] = " "


    @property
    def name(self):
        """
        Return the name of the widget.
        """
        return self._field_name
    
          
    @classmethod      
    def _default_widget(cls):
        """
        Return the default widget function.
        """
        return ipyw.Textarea

    def _widget_events(self):
        """
        Create any relevant wiget event handlers.
        """
        super()._widget_events()
        log.debug(f"Binding on_value_change event for widget {self._ipywidget}.")
        self._ipywidget.observe(self.on_value_change, names="value")

    def on_value_change(self, value):
        """
        Observer for when value changes.
        """
        pass
    
    def get_value(self):
        """
        Get the value of the widget.

        :return: The value of the widget.
        :rtype: any
        """
        if self._reversion is None:
            return self._ipywidget.value
        else:
            return self._reversion(self._ipywidget.value)

    def get_layout(self):
        """
        Returns the layout of the internal ipywidget.
        
        :return: The layout of the widget.
        :rtype: ipywidgets.Layout
        """
        return self._ipywidget.layout
        
    def get_description(self):
        """
        Get the description of the widget.
        
        :return: The description of the widget.
        :rtype: str
        """
        return self._ipywidget.description
    
    def set_value(self, value):
        """
        Set the value of the widget.
        
        :param value: The value to set.
        :type value: any
        """
        
        if notempty(value):
            if self._conversion is not None:
                log.debug(f"Converting value {value} for widget \"{self.name}\".")             
                value = self._conversion(value)

            log.debug(f"Setting widget \"{self.name}\" to value {value}.")
            self._ipywidget.value = value
        else:
            log.debug(f"Widget \"{self.name}\" has been set to an empty value. Setting to widget's default value.")
            # TK Should it be set to a default value or left as empty?
            self.reset_value()
    
    def set_value_silently(self, value) -> None:
        """
        Set the value of the widget without triggering the observer.

        :param value: The value to set.
        :type value: any
        """
        log.debug(f"Silently setting widget \"\"{self.name}\"\" to value: {value}.")
        # Remove value change observers
        # Formerly self._ipywidget.observe(self.null, names='value')
        observers = self._get_observers().copy()
        log.debug(f"Length of observers is {len(observers)}.")
        removed_observers = []
        for observer in observers:
            # Only remove observers that are of the form self.on_value_change
            log.debug(f"Observer is {observer}.")
            if hasattr(observer, "__name__") and observer.__name__ == "on_value_change":
                log.debug(f"Removing observer {observer} from widget \"{self.name}\".")
                self._ipywidget.unobserve(observer, names='value')
                # Add observer to list of removed observers
                removed_observers.append(observer)

        # Silently change value
        if self._conversion is not None:
            log.debug(f"Converting value {value} for widget \"{self.name}\".")
            value = self._conversion(value)
            
        log.debug(f"Setting widget \"{self.name}\" to value {value}.")
        self._ipywidget.value = value

        # Re-add value change observers
        # Formerly self._ipywidget.observe(self.on_value_change, names="value")
        log.debug(f"Length of obsrervers is {len(observers)}.")
        for observer in removed_observers:
            log.debug(f"Re-adding observer {observer} to widget \"{self.name}\".")
            self._ipywidget.observe(observer, names='value')        

    def _get_observers(self) -> list:
        """
        Return the observers for value change for the widget.

        :return: The observers for value change for the widget.
        :rtype: list
        """
        try:
            return self._ipywidget._trait_notifiers['value']['change']
        except (AttributeError, KeyError, TypeError):
            log.debug(f"Widget \"{self.name}\" has no observers")
            return []
        
    def reset_value(self):
        """
        Reset value to default for widget.
        """
        value = self._default_value
        log.debug(f"Setting widget {self.widget} named \"{self.name}\" to default value {value}.")
        self.set_value_silently(value)
        
    def get_column(self):
        """
        Get the column name for the widget.

        :return: The column name for the widget.
        :rtype: str
        """
        return self._column_name
    
    def to_markdown(self):
        """
        Return the widget value and description as markdown.

        :return: The widget value and description as markdown.
        :rtype: str
        """
        description = self.get_description()
        value = self.get_value()
        if description is None or description.strip() == "":
            return f"{value}"
        else:
            return f"#### {description}\n\n{value}"
    
class FieldWidget(ReferiaStatefulWidget):
    """
    Widget for editing field values in parent data.
    """
    def __init__(self, function=None, conversion=None, reversion=None, **args):
        """
        Initialise the widget.

        :param function: The function for creating the widget.
        :type function: function
        :param conversion: The conversion function for setting the widget value.
        :type conversion: function
        :param reversion: The reversion function for getting the widget value.
        :type reversion: function
        :param args: The arguments for the widget.
        :type args: dict
        """
        # This argument includes the ipywidgets function for creating the widget
        args["function"] = function

        # These arguments are for any conversions for setting and retrieving the widget value.
        args["conversion"] = conversion
        args["reversion"] = reversion
        super().__init__(**args)
        
    def on_value_change(self, change):
        """
        When value of the widget changes update the relevant parent data structure.

        :param change: The change event containing keys 'old' and 'new'.
        :type change: dict
        """
        # Jupyter catches exceptions to prevent notebook crashes.
        # If there are errors in the code they occur silently. This try catch ensures they are logged.
        try: 
            log.debug(f"Widget \"{self.name}\" value changed from {change.old} to {change.new}")
            # If the widget is not private and has a parent, update the parent data structure.
            if not self.private and self._parent is not None:
                if self.get_column() is not None:
                    self._parent.set_column(self.get_column())
                    self._parent.set_value(change.new)

            if self._refresh_display:
                if self._parent is not None:
                    self._parent._widgets.refresh()
        except Exception as e:
            errmsg = f"An error occurred in FieldWidget.on_value_change: {str(e)}"
            log.error(errmsg)
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e
        
    def has_viewer(self):
        """
        Does the widget have a viewer structure for generating its values.

        :return: True if the widget has a viewer structure, False otherwise.
        :rtype: bool
        """
        return len(self._viewer)>0
    
    def refresh(self):
        """
        Update the widget value from the data.
        """
        log.debug(f"Refreshing widget \"{self.name}\".")
        column = self.get_column()
        if column is not None and self._parent is not None:
            if self.has_viewer():
                log.debug(f"Widget \"{self.name}\" has a viewer structure")
                log.debug(f"Viewer structure is {self._viewer}")
                # Convert the result using viewer before setting value.
                value = self._parent._data.viewer_to_value(self._viewer)
                log.debug(f"Setting widget \"{self.name}\" to value {value}")
            else:
                log.debug(f"Widget \"{self.name}\" does not have a viewer structure")
                self._parent.set_column(column)
                value = self._parent.get_value()

            if notempty(value):
                log.debug(f"Setting widget \"{self.name}\" to value {value}")
                self.set_value_silently(value)
            else:
                self.reset_value()
        else:
            self.reset_value()

class ElementWidget(FieldWidget):
    """
    Widget for editing element of a given field value in parent data.
    """
    def __init__(self, **args):
        """
        Initialise the widget.

        :param element: The element to edit.
        :type element: int
        """
        if "element" in args:
            self.set_element(args["element"])
            del args["element"]
        else:
            self.set_element(None)

        super().__init__(**args)

    def get_element(self):
        """
        Get the element of the widget.

        :return: The element of the widget.
        """
        return self._element

    def set_element(self, value):
        """
        Set the element of the widget.

        :param value: The value to set.
        """
        self._element = value
        
    def on_value_change(self, change):
        """
        When value of the widget changes update the relevant parent data structure.
        :param change: The change event.
        """
        try:
            if not self.private and self._parent is not None:
                self._parent.set_column(self.get_column())
                self._parent.set_value_by_element(change.new, self.get_element())
            if self._refresh_display:
                if self._parent is not None:
                    self._parent.refresh()
        except Exception as e:
            errmsg = f"An error occurred in ElementWidget.on_value_change: {str(e)}"
            log.error(errmsg)
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e

    def has_viewer(self):
        """
        Does the widget have a viewer structure for generating its values

        :return: True if the widget has a viewer structure, False otherwise.
        :rtype: bool
        """
        return len(self._viewer)>0
    
    def refresh(self):
        """
        Update the widget value from the data.
        """
        log.debug(f"Refreshing widget {self.name}")
        try:
            column = self.get_column()
            if column is not None and self._parent is not None:
                if self.has_viewer():
                    # Convert the result using viewer before setting value.
                    value = self._parent._data.viewer_to_value(self._viewer)
                    self.set_value_silently(value)
                else:
                    self._parent.set_column(column)
                    self.set_value_silently(self._parent.get_value_by_element(self.get_element()))
            else:
                self.reset_value()
        except Exception as e:
            errmsg = f"An error occurred in refresh: {str(e)}"
            log.error(errmsg)
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e

        
class IndexSelector(ReferiaStatefulWidget):
    """
    Widget for selecting an index from a list of indices.

    This widget is a stateful widget that allows the user to select an index from the index list, typically for pulling up that entry's data.
    """
    def __init__(self, parent):
        """
        Initialise the widget.

        :param parent: The parent widget.
        :type parent: ReferiaWidget
        """
        args = {
            "options": parent.index,
            "value": parent.get_index(),
            "parent" : parent,
            "function" : ipyw.Dropdown,
        }
        super().__init__(**args)
        self.private = False
        
    def on_value_change(self, change):
        """
        When value of the widget changes update the relevant parent data structure.
        :param change: The change event.
        """
        try:
            if not self.private and self._parent is not None:
                if change.new != self._parent.get_index():
                    self._parent.set_index(change.new)
                    self._parent.view_series()
        except Exception as e:
            errmsg = f"An error occurred in IndexSelector.on_value_change: {str(e)}"
            log.error(errmsg)
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e

    def set_index(self, value):
        """
        Set the index of the widget.

        :param value: The value to set.
        """
        self.set_value(value)
        
    def refresh(self):
        pass

class ReferiaMultiWidget(ReferiaStatefulWidget):
    """Class for forming a collection of widgets that interact."""
    def __init__(self, parent, stateful_args, stateless_args):
        """
        Initialise the widget.

        :param parent: The parent widget.
        :type parent: ReferiaWidget
        :param stateful_args: The stateful arguments for the widget.
        :type stateful_args: dict
        :param stateless_args: The stateless arguments for the widget.
        :type stateless_args: dict
        """
        self._parent = parent
        self._ipywidgets = {}

        # Create the widgets that have state.
        for key, item in stateful_args.items():
            self.add_stateful(key, item)

        # Create the widgets that have state.
        for key, item in stateful_args.items():
            self.update_side_effects(key, item)
            
        # Create the widgets that are stateless (such as buttons)
        for key, item in stateless_args.items():
            self.add_stateless(key, item)

    def add_stateful(self, key, item):
        """
        Add a stateful widget to the multiwidget display.

        :param key: The key for the widget.
        :type key: str
        :param item: The item for the widget.
        :type item: dict
        """
        self._ipywidgets[key] = {
            "function": item["function"],
            "result_function": item["result_function"],
            "conversion": item["conversion"],
            "reversion": item["reversion"],
            "stateful": True,
        }
        kwargs = item.copy()
        del kwargs["function"]
        del kwargs["result_function"]
        self._ipywidgets[key]["set_value"] = gsv_(key, kwargs, self)
        
        self._ipywidgets[key]["widget"] = self._ipywidgets[key]["function"](**kwargs)
        self._ipywidgets[key]["update"] = gwu_(key, kwargs, self)

    def update_side_effects(self, key, item):
        """
        Create the generator functions for when widgets change.

        :param key: The key for the widget.
        :type key: str
        :param item: The item for the widget.
        :type item: dict
        """
        self._ipywidgets[key]["on_change"] = gwc_(key, item, self)            
        self._ipywidgets[key]["widget"].observe(self._ipywidgets[key]["on_change"], names="value")
        
    def add_stateless(self, key, item):
        """
        Add a stateless widget to the multiwidget display.

        :param key: The key for the widget.
        :type key: str
        """
        self._ipywidgets[key] = {
            "function": item["function"],
            "on_click_function": item["on_click_function"],
            "stateful": False,
        }
        kwargs = item.copy()
        del kwargs["function"]
        del kwargs["on_click_function"]
        self._ipywidgets[key]['widget'] = self._ipywidgets[key]["function"](**kwargs)
        self._ipywidgets[key]["widget"].on_click(gocf_(key, kwargs, self))

    def display(self):
        """
        Display the widget.
        """
        objects = []
        for key, item in self._ipywidgets.items():
            objects.append(item["widget"])
        IPython.display.display(ipyw.VBox(objects))

# class WidgetList(ReferiaMultiWidget):
#     """This multi widget holds a list of widgets to provide a list entry in the data."""
#     def __init__(self, parent):
#         stateful_args = {
#             "text_select1":  {
#                     "value_function": parent.get_value,
#                     "function": ipyw.Textarea,
#                     "result_function" : parent.set_value,
#                 "conversion": None,
#                 "reversion": None,
#             },
#             "selector_select":  {
#                 "function": ipyw.Dropdown,
#                 "options_function": parent.get_selectors,
#                 "value_function": parent.get_selector,
#                 "result_function": parent.set_selector,
#                 "display_when_function": parent.get_select_selector,
#                 "conversion": None,
#                 "reversion": None,
#             },
#             "subindex_select": {
#                 "function" : ipyw.Dropdown,
#                 "options_function": parent.get_subindices,
#                 "value_function": parent.get_subindex,
#                 "result_function" : parent.set_subindex,
#                 "display_when_function": parent.get_select_subindex,
#                 "conversion": None,
#                 "reversion": None,
#             },
#             "select_subindex_checkbox": {
#                 "function" : ipyw.Checkbox,
#                 "value_function": parent.get_select_subindex,
#                 "result_function": parent.set_select_subindex,
#                 "conversion": bool,
#                 "description": "Select Subindex",
#                 "reversion": None,
#             },
#             "select_selector_checkbox": {
#                 "function" : ipyw.Checkbox,
#                 "value_function": parent.get_select_selector,
#                 "result_function": parent.set_select_selector,
#                 "conversion": bool,
#                 "description": "Select Selector",
#                 "reversion": None,
#             }
#         }
#         stateless_args = {
#             "generate_button" : {
#                 "function": ipyw.Button,
#                 "on_click_function": parent.add_series_row,
#                 "description": "Add Row",
#             }
#         }
#         super().__init__(parent, stateful_args, stateless_args)
    
#     def get_value(self):
#         return [val for widget in self._ipywidgets if widget["stateful"]]

#     def set_value(self, values):
#         if type(values) is not list:
#             raise ValueError(f"Attempt to set value of a WidgetList with a non-list value.")
#         else:
#             for i, val in enumerate(values):
#                 if self._ipywidgets[i]
#         val = []
#         return [val for widget in self._ipywidgets if widget["stateful"]]
    
        
# class ActionExtractor(ReferiaMultiWidget):
#     """
#     This multi widget allows a box to be filled from an action taken by a button.
#     """
#     def __init__(self, parent, action_function, action_args):
#         """
#         Initialise the widget.

#         :param parent: The parent widget.
#         :type parent: ReferiaWidget
#         :param action_function: The function to call when the button is clicked.
#         :type action_function: function
#         :param action_args: The arguments for the action function.
#         :type action_args: dict
#         """
#         stateful_args = {
#             "extract_information" : {
#                 "function" : ipyw.Textarea,
#                 "defaultargs" : {},
#             }
#         }
#         stateless_args = {
#             "extract_button" : {
#                 "function": ipyw.Button,
#                 "on_click_function": action_function,
#                 "on_click_args": action_args,
#             }
#         }
#         super().__init__(parent, stateful_args, stateless_args)
        
class ScreenCapture(ReferiaMultiWidget):
    """
    Take the most recent screen capture and display it
    """
    def __init__(self, parent):
        """
        Initialise the widget.

        :param parent: The parent widget.
        :type parent: ReferiaWidget
        """
        stateful_args = {
            "image" : {
                "function" : ipyw.Image,
                "defaultargs" : {
                    "format": "png",
                },
                "result_function": None, 
                "conversion": None,      
                "reversion": None,       
            }
        }
        stateless_args = {
            "capture_button" : {
                "function" : ipyw.Button,
                "on_click_function": parent.copy_screen_capture,
            }
        }
            
        super().__init__(parent, stateful_args, stateless_args)
            
class FullSelector(ReferiaMultiWidget):
    """
    This multi widget allows a range of interacting selectors.
    """
    def __init__(self, parent, stateful_args, stateless_args):
        """
        Initialise the widget.

        :param parent: The parent widget.
        :type parent: ReferiaWidget
        :param stateful_args: The stateful arguments for the widget.
        :type stateful_args: dict
        :param stateless_args: The stateless arguments for the widget.
        :type stateless_args: dict
        """
        
        # Set the item values and option values from the functions.
        for key, item in stateful_args.items():
            item["value"] = item["value_function"]()
            if "options_function" in item:
                item["options"] = item["options_function"]()
            if "display_when_function" in item:
                if "layout" not in item:
                    item["layout"] = {}
                if item["display_when_function"]():
                    item["layout"]["display"] = "block"
                else:
                    item["layout"]["display"] = "none"
        super().__init__(parent, stateful_args, stateless_args)

class IndexSubIndexSelectorSelect(FullSelector):
    """
    This multi widget allows a range of interacting index selectors.

    The index selector is a dropdown list of indices.
    The subindex selector is a dropdown list of subindices.
    The selector selector is a dropdown list of selectors.
    """
    def __init__(self, parent):
        """
        Initialise the widget.

        :param parent: The parent widget.
        :type parent: ReferiaWidget
        """
        # Define the widgets to create
        self._private = False
        stateful_args = {
            "index_select":  {
                "options_function": parent.get_indices,
                "value_function": parent.get_index,
                "function": ipyw.Dropdown,
                "result_function" : parent.set_index,
                "conversion": None,
                "reversion": None,
            },
            "selector_select":  {
                "function": ipyw.Dropdown,
                "options_function": parent.get_selectors,
                "value_function": parent.get_selector,
                "result_function": parent.set_selector,
                "display_when_function": parent.get_select_selector,
                "conversion": None,
                "reversion": None,
            },
            "subindex_select": {
                "function" : ipyw.Dropdown,
                "options_function": parent.get_subindices,
                "value_function": parent.get_subindex,
                "result_function" : parent.set_subindex,
                "display_when_function": parent.get_select_subindex,
                "conversion": None,
                "reversion": None,
            },
            "select_subindex_checkbox": {
                "function" : ipyw.Checkbox,
                "value_function": parent.get_select_subindex,
                "result_function": parent.set_select_subindex,
                "conversion": bool,
                "description": "Select Subindex",
                "reversion": None,
            },
            "select_selector_checkbox": {
                "function" : ipyw.Checkbox,
                "value_function": parent.get_select_selector,
                "result_function": parent.set_select_selector,
                "conversion": bool,
                "description": "Select Selector",
                "reversion": None,
            }
        }
        stateless_args = {
            "generate_button" : {
                "function": ipyw.Button,
                "on_click_function": parent.add_series_row,
                "description": "Add Row",
            }
        }
        super().__init__(parent, stateful_args, stateless_args)

    def on_value_change(self, change):
        """
        When value of the widget changes update the relevant parent data structure.
        :param change: The change event.
        """
        try:
            if not self.private and self._parent is not None:
                self._parent.set_index(change.new)
                self._parent.view_series()
        except Exception as e:
            errmsg = f"An error occurred in IndexSubIndexSelectorSelect.on_value_change: {str(e)}"
            log.error(errmsg)
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e

    def set_index(self, value):
        """
        Set the index of the widget.

        :param value: The value to set.
        """
        self._ipywidgets["index_select"]["set_value"](value)

class ReferiaButtonWidget(ReferiaWidget):
    """
    A widget for a button.
    """
    def __init__(self, **args):
        """
        Initialise the widget.

        :param description: The description of the widget.
        :type description: str
        """
        super().__init__(**args)

    @property
    def name(self):
        """
        Return the name of the widget.
        """
        return self.description
        
    @classmethod
    def _default_widget(cls):
        """
        Return the default widget function.
        """
        return ipyw.Button


    def _widget_events(self):
        """
        Create any relevant wiget event handlers.
        """
        super()._widget_events()
        log.debug(f"Binding widget on_click event for widget {self._ipywidget}.")
        self._ipywidget.on_click(self.on_click)
        
    def on_click(self, b):
        """
        When the button is clicked do nothing.
        """
        raise NotImplementedError("The on_click method must be implemented in the subclass.")

    def refresh(self):
        """
        Refresh the widget.
        """
        # Button's do nothing when they are refreshed.
        pass
    
class CreateDocButton(ReferiaButtonWidget):
    """
    Create a document for editing based on the information we have.
    """
    def __init__(self, **args):
        """
        Initialise the widget.

        :param type: The type of document to create.
        :type type: str
        :param document: The document to create.
        :type document: str
        """
        args["description"] = "Create " + args["type"]
        super().__init__(**args)
        self.type = args["type"]
        self.document = args["document"]
        
    def on_click(self, b):
        """
        When the button is clicked create the document.
        """
        # Place in try except block to catch errors and log them due to Jupyter's silent error handling.
        try:
            self._parent.create_document(self.document, summary=False)
        except Exception as e:
            errmsg = f"An error occurred in CreateDocButton.on_click: {str(e)}"
            log.error(errmsg)
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e
        
class CreateSummaryDocButton(ReferiaButtonWidget):
    """
    Create a summary document based on all the entries.
    """
    def __init__(self, **args):
        """
        Initialise the widget.

        :param type: The type of document to create.
        :type type: str
        :param document: The document to create.
        :type document: str
        """
        args["description"] = "Create Summary " + args["type"]
        super().__init__(**args)
        self.type = args["type"]
        self.document = args["document"]
        
    def on_click(self, b):
        """
        When the button is clicked create the document.
        """
        # Place in try except block to catch errors and log them due to Jupyter's silent error handling.
        try:
            self._parent.create_document(self.document, summary=True)
        except Exception as e:
            errmsg = f"An error occurred in CreateSummaryDocButton.on_click: {str(e)}"
            log.error(errmsg)
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e
        
class CreateSummaryButton(ReferiaButtonWidget):
    """
    Create a summary based on all the entries.
    """
    def __init__(self, **args):
        """
        Initialise the widget.

        :param type: The type of summary to create.
        :type type: str
        :param details: The details of the summary to create.
        :type details: dict
        """
        
        args["description"] = "Create " + args["type"] + " Summary"
        super().__init__(**args)
        self.type = args["type"]
        self.details = args["details"]
        
    def on_click(self, b):
        """
        When the button is clicked create the summary.
        """
        # Place in try except block to catch errors and log them due to Jupyter's silent error handling.
        try:
            self._parent.create_summary(self.details)
        except Exception as e:
            errmsg = f"An error occurred in CreateSummaryButton.on_click: {str(e)}"
            log.error(errmsg)
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e
        
class SaveButton(ReferiaButtonWidget):
    """
    Write the data to the appropriate storage files.
    """
    def __init__(self, **args):
        """
        Initialise the SaveButton widget.
        """
        if "description" not in args:
            args["description"] = "Save Flows"
        super().__init__(**args)

    def on_click(self, b):
        """
        When the button is clicked save the flows.
        """
        # Place in try except block to catch errors and log them due to Jupyter's silent error handling.
        try:
            self._parent.save_flows()
        except Exception as e:
            errmsg = f"An error occurred in SaveButton.on_click: {str(e)}"
            log.error(errmsg)
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e
            
class ReloadButton(ReferiaButtonWidget):
    """Reload the data from the appropriate storage files."""
    def __init__(self, **args):
        """
        Initialise the ReloadButton widget.
        """
        if "description" not in args:
            args["description"] = "Reload Flows"
        super().__init__(**args)

    def on_click(self, b):
        """
        When the button is clicked reload the flows.
        """
        # Place in try except block to catch errors and log them due to Jupyter's silent error handling.
        try:
            self._parent.load_flows(reload=True)
        except Exception as e:
            errmsg = f"An error occurred in ReloadButton.on_click: {str(e)}"
            log.error(errmsg)
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e

class PopulateButton(ReferiaButtonWidget):
    """Populate the data from a compute."""
    def __init__(self, **args):
        """
        Initialise the PopulateButton widget.

        :param target: The target to populate.
        :type target: str
        :param compute: The compute to run.
        :type compute: dict
        :param description: The description of the widget.
        :type description: str
        """
        if "description" not in args:
            if "target" in args:
                args["description"] = "Populate " + args["target"]
            else:
                args["description"] = "Populate"

        log.debug(f"Creating PopulateButton with description \"{args['description']}\".")

        if "compute" not in args:
            errmsg = f"Compute not found in args for PopulateButton \"{args['description']}\"."
            log.error(errmsg)
            raise ValueError(errmsg)

        self._compute_interface = {"compute" : args["compute"]}
        #if isinstance(args["compute"], list):
        #    self._compute_interface = {"compute" : args["compute"]}
        #else:
        #    self._compute_interface = {[args["compute"]]
            
        super().__init__(**args)

    def on_click(self, b : ipyw.Button) -> None:
        """
        When the button is clicked populate the data.

        :param b: The button that was clicked.
        :type b: ipyw.Button
        :return: None
        """
        try:
            log.debug(f"Populating data for \"{self.name}\" and \"{self._compute_interface}\".")
            self._parent._data._compute.run(self._parent._data, self._compute_interface)            
            #for compute in self._compute_interface:
            #    compute["refresh"] = True
            #    self._parent._data._compute.run(self._parent._data._compute.prep(settings=compute, data=self._parent._data))
            self._parent.populate_display()
        except Exception as e:
            errmsg = f"An error occurred in PopulateButton.on_click: {str(e)}"
            log.error(errmsg)
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e


        #for compute in self._compute:
        #    compute["refresh"] = True
        #    self._parent._data._compute.run(self._parent._data._compute.prep(compute))
        #self._parent.populate_display()
        
            
def gocf_(key, item, obj, docstr=None):
    """
    Generator function for on_click function for the button class.

    :param key: The key for the widget.
    :type key: str
    :param item: The item for the widget.
    :type item: dict
    :param obj: The object for the widget.
    :type obj: ReferiaMultiWidget
    :param docstr: The docstring for the function.
    :type docstr: str
    :return: The on_click function.
    :rtype: function
    """
    def on_click(b):
        try:
            obj._ipywidgets[key]["on_click_function"]()
            for other_key, widget in obj._ipywidgets.items():
                if other_key == key:
                    pass
                elif "update" in widget:
                    widget["update"]()
        except Exception as e:
            errmsg = f"An error occurred in on_click: {str(e)}"
            log.error(errmsg)
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e
    on_click.__doc__ = docstr
    return on_click
            
def gsv_(key, item, obj, docstr=None):
    """
    Generator function for a set value function for the multiwidget class.

    :param key: The key for the widget.
    :type key: str
    :param item: The item for the widget.
    :type item: dict
    :param obj: The object for the widget.
    :type obj: ReferiaMultiWidget
    :param docstr: The docstring for the function.
    :type docstr: str
    :return: The set value function.
    :rtype: function
    """
    def set_value(value):
        if notempty(value):
            if obj._ipywidgets[key]["conversion"] is None:
                obj._ipywidgets[key]["widget"].value = value
            else:
                obj._ipywidgets[key]["widget"].value = obj._ipywidgets[key]["conversion"](value)
        else:
            obj._ipywidgets[key]["widget"].value = obj._ipywidgets[key]["function"]().value
        # Perform callback to set the result.
        obj._ipywidgets[key]["result_function"](obj._ipywidgets[key]["widget"].value)
    set_value.__doc__ = docstr
    return set_value

def gwc_(key, item, obj, docstr=None):
    """
    Generator functions for propagating changes to other widgets on this change.

    :param key: The key for the widget.
    :type key: str
    :param item: The item for the widget.
    :type item: dict
    :param obj: The object for the widget.
    :type obj: ReferiaMultiWidget
    :param docstr: The docstring for the function.
    :type docstr: str
    :return: The on change function.
    :rtype: function
    """
    name = "on_" + key + "_change"
    def on_change(change):
        try:
            obj._ipywidgets[key]["set_value"](change.new)
            for other_key, widget in obj._ipywidgets.items():
                if other_key == key:
                    pass
                elif "update" in widget:
                    widget["update"]()
        except Exception as e:
            errmsg = f"An error occurred in on_change: {str(e)}"
            log.error(errmsg)
            log.error(f"Full traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise e

    on_change.__name__ = name
    on_change.__doc__ = docstr
    return on_change
                    
def gwu_(key, item, obj, docstr=None):
    """
    Generator function for making update calls for a given widget.

    :param key: The key for the widget.
    :type key: str
    :param item: The item for the widget.
    :type item: dict
    :param obj: The object for the widget.
    :type obj: ReferiaMultiWidget
    :param docstr: The docstring for the function.
    :type docstr: str
    :return: The update function.
    :rtype: function
    """
    def on_other_widgets_change():
        widg = obj._ipywidgets[key]["widget"]
        if "options_function" in item:
            widg.options = item["options_function"]()
        if "value_function" in item:
            widg.value = item["value_function"]()
        if "display_when_function" in item:
            if item["display_when_function"]():
                widg.layout.display = "block"
            else:
                widg.layout.display = "none"
        on_other_widgets_change.__name__ = key
        on_other_widgets_change.__doc__ = docstr
    return on_other_widgets_change

def gwf_(name, function, conversion=None, reversion=None, default_args={}, docstr=None):
    """
    This function wraps the widget function and calls it with any additional default arguments as specified.

    :param name: The name of the widget.
    :type name: str
    :param function: The function to call.
    :type function: function
    :param conversion: The conversion function to use.
    :type conversion: function
    :param reversion: The reversion function to use.
    :type reversion: function
    :param default_args: The default arguments to use.
    :type default_args: dict
    :param docstr: The docstring for the function.
    :type docstr: str
    :return: The widget function.
    :rtype: function
    """
    def widget_function(**args):
        all_args = default_args.copy()
        all_args.update(args)
        return FieldWidget(
            function=function,
            conversion=conversion,
            reversion=reversion,
            **all_args,
        )
    widget_function.__name__ = name
    widget_function.__doc__ = docstr
    return widget_function

def gwef_(name, function, conversion=None, reversion=None, default_args={}, docstr=None):
    """
    This function wraps the widget function and calls it with any additional default arguments as specified.

    :param name: The name of the widget.
    :type name: str
    :param function: The function to call.
    :type function: function
    :param conversion: The conversion function to use.
    :type conversion: function
    :param reversion: The reversion function to use.
    :type reversion: function
    :param default_args: The default arguments to use.
    :type default_args: dict
    :param docstr: The docstring for the function.
    :type docstr: str
    :return: The widget function.
    :rtype: function
    """
    def widget_function(**args):
        all_args = default_args.copy()
        all_args.update(args)
        return ElementWidget(
            function=function,
            conversion=conversion,
            reversion=reversion,
            **all_args,
        )
    widget_function.__name__ = name
    widget_function.__doc__ = docstr
    return widget_function
                

        
def populate_widgets(widget_list):
    """
    Automatically creates widget wrapper objects and adds them to the module.

    :param widget_list: The list of widgets to create.
    :type widget_list: list
    """
    this_module = sys.modules[__name__]
    for widget in widget_list:
        setattr(
            this_module,
            widget["name"],
            gwf_(**widget),
        )

def populate_element_widgets(widget_list):
    """
    Automatically creates element widget wrapper objects and adds them to the module.

    :param widget_list: The list of widgets to create.
    :type widget_list: list
    """
    this_module = sys.modules[__name__]
    for widget in widget_list:
        setattr(
            this_module,
            "Element" + widget["name"],
            gwef_(**widget),
        )
                
def MyFileChooser(**args):
    """
    Create a simple Dropdown box to allow file selection from a given path.

    :param directory: The directory to search for files.
    :type directory: str
    :param glob: The glob to use for file selection.
    :type glob: str
    :param path: The path to use for file selection.
    :type path: str
    :return: The widget.
    :rtype: ipywidgets.Dropdown
    """
    if "directory" not in args:
        directory = "."
    else:
        directory = args["directory"]
        del args["directory"]

    if "path" in args:
        directory = os.path.join(path, directory)
        
    if "glob" not in args:
        globname = "*"
    else:
        globname = args["glob"]
        del args["glob"]
    files = glob.glob(os.path.join(os.path.expandvars(directory), globname))
    dirs = []
    options = []
    for option in [''] + dirs + files:
        options.append(os.path.basename(option))
    args["options"] = options
    
    return ipyw.Dropdown(**args)

def interact(function, **kwargs):
    """
    Create an interactive widget for a given function.

    :param function: The function to create the widget for.
    :type function: function
    :param **kwargs: The arguments for the function.
    """
    newargs = {}
    for key, widget in kwargs.items():
        newargs[key] = widget.widget
    ipyw.interact(function, **newargs)

def interact_manual(function, **kwargs):
    """
    Create an interactive widget for a given function.

    :param function: The function to create the widget for.
    :type function: function
    :param **kwargs: The arguments for the function.
    """
    newargs = {}
    for key, widget in kwargs.items():
        newargs[key] = widget.widget
    ipyw.interact_manual(function, **newargs)

def interactive(function, **kwargs):
    """
    Create an interactive widget for a given function.

    :param function: The function to create the widget for.
    :type function: function
    :param **kwargs: The arguments for the function.
    """
    newargs = {}
    for key, widget in kwargs.items():
        newargs[key] = widget.widget
    ipyw.interactive(function, **newargs)

    
populate_widgets(list_stateful_widgets)
populate_element_widgets(list_stateful_widgets)

