import os
import sys
import glob

import IPython
import ipywidgets as ipyw
import markdown

from pandas.api.types import is_string_dtype, is_numeric_dtype, is_bool_dtype


ipyw.interact_manual.opts["manual_name"] = "Save Score"

from .config import *
from .util import notempty
from .log import Logger
from . import display
from . import system

def markdown2html(text):
    return markdown.markdown(text)

log = Logger(
    name=__name__,
    level=config["logging"]["level"],
    filename=config["logging"]["filename"]
)

#other = [jslink, jsdlink, MyCheckbox, MyFileChooser]

list_stateful_widgets = [
    {
        "name" : "IntSlider",
        "function" : ipyw.IntSlider,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "FloatSlider",
        "function" : ipyw.FloatSlider,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Checkbox",
        "function" : ipyw.Checkbox,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Flag",
        "function" : ipyw.Checkbox,
        "default_args" : {},
        "docstr" : None,
        "conversion" : bool,
    },
    {
        "name" : "Text",
        "function" : ipyw.Text,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Textarea",
        "function" : ipyw.Textarea,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Combobox",
        "function" : ipyw.Combobox,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
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
    },
    {
        "name" : "Layout",
        "function" : ipyw.Layout,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "HTML",
        "function" : ipyw.HTML,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "HTMLMath",
        "function" : ipyw.HTMLMath,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Markdown",
        "function" : ipyw.HTMLMath,
        "default_args" : {},
        "docstr" : None,
        "conversion" : markdown2html,
    },
    {
        "name" : "DatePicker",
        "function" : ipyw.DatePicker,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
]

class ReferiaWidget():
    def __init__(self, **args):
        self._parent = None
        self.private = True
        if "function" in args:
            self._ipywidget_function = args["function"]
        else:
            self._ipywidget_function = self._default_widget()

        if "parent" in args:
            self._parent = args["parent"]
        self._create_widget(args)

    def _default_widget(self):
        return ipyw.Button

    def _create_widget(self, args):
        self._ipywidget = self._ipywidget_function(**args)
        self._widget_events()

    def _widget_events(self):
        self._ipywidget.on_click(self.on_click)

    def on_click(self, b):
        pass

    def refresh(self):
        pass

    @property
    def widget(self):
        return self._ipywidget
    
    @property
    def private(self):
        return self._private

    @private.setter
    def private(self, value):
        #if not is_bool_dtype(value):
        #    raise ValueError("Private must be set as bool (True/False)")
        self._private = value

    def display(self):
        IPython.display.display(self._ipywidget)

    def null(self, void):
        pass

        
class ReferiaStatefulWidget(ReferiaWidget):
    def __init__(self, **args):
        super().__init__(**args)
        self._conversion = None
        self._display = None
        self._column_name = None
        self._field_name = None
        if "conversion" in args:
            self._conversion = args["conversion"]
        if self._conversion is not None and "value" in args:
            args["value"] = self._conversion(args["value"])
        if "display" in args:
            self._display = args["display"]
        if "column_name" in args:
            self._column_name = args["column_name"]
        if "field_name" in args:
            self._field_name = args["field_name"]
            
        # Is this a private field (one that doesn't update the parent data)
        if self._field_name is not None and self._field_name[0] == "_": 
            self.private = True
        else:
            self.private = False

        if self.private and "description" not in args: 
            args["descripton"] = " "

    def _default_widget(self):
        return ipyw.Textarea

    def _widget_events(self):
        self._ipywidget.observe(self.on_value_change, names="value")

    def on_value_change(self, value):
        pass

    
    def get_value(self):
        return self._ipywidget.value
    
    def set_value(self, value):
        if notempty(value):
            if self._conversion is None:
                self._ipywidget.value = value
            else:
                self._ipywidget.value = self._conversion(value)
        else:
            self._ipywidget.value = self._ipywidget_function().value
            
    def get_column(self):
        return self._column_name
                           

class FieldWidget(ReferiaStatefulWidget):
    """Widget for editing field values in parent data."""
    def __init__(self, function=None, conversion=None, **args):
        args["function"] = function
        args["conversion"] = conversion
        super().__init__(**args)
        
    def on_value_change(self, change):
        self.set_value(change.new)
        if not self.private and self._parent is not None:
            self._parent.set_column(self.get_column())
            self._parent.set_value(self.get_value())

    def refresh(self):
        self._ipywidget.observe(self.null, names='value')
        if self._display is not None:
            self.set_value(self._display.format(**self._parent._data.mapping()))
        else:
            column = self.get_column()
            if not self.private and column is not None and self._parent is not None:
                self._parent.set_column(column)
                self.set_value(self._parent.get_value())

        self._ipywidget.observe(self.on_value_change, names="value")
            

class IndexSelector(ReferiaStatefulWidget):
    def __init__(self, parent):
        args = {
            "options": parent.index,
            "value": parent.get_index(),
            "parent" : parent,
            "function" : ipyw.Dropdown,
        }
        super().__init__(**args)

    def on_value_change(self, change):
        self.set_value(change.new)
        if not self.private and self._parent is not None:
            self._parent.set_index(self.get_value())
            system.view_series(self._parent._data)

    def refresh(self):
        pass

class ReferiaMultiWidget(ReferiaStatefulWidget):
    """Class for forming a collection of widgets that interact."""
    def __init__(self, **args):
        pass
    
class FullSelector(ReferiaMultiWidget):
    def __init__(self, parent, args):
        self._parent = parent
        self._ipywidgets = {}
        for key, item in args.items():
            item["value"] = item["value_function"]()
            if "options_function" in item:
                item["options"] = item["options_function"]()
        for key, item in args.items():
            self._ipywidgets[key] = {
                "function": item["function"],
                "result": item["result"],
                "conversion": item["conversion"],
                }
            del item["function"]
            del item["result"]
            self._ipywidgets[key]["set_value"] = gsv_(key, item, self)
            
            self._ipywidgets[key]["widget"] = self._ipywidgets[key]["function"](**item)
            self._ipywidgets[key]["update"] = gwu_(key, item, self)

        for key, item in self._ipywidgets.items():
            self._ipywidgets[key]["on_change"] = gwc_(key, item, self)            
            self._ipywidgets[key]["widget"].observe(self._ipywidgets[key]["on_change"], names="value")


    def display(self):
        objects = []
        for key, item in self._ipywidgets.items():
            objects.append(item["widget"])
        IPython.display.display(ipyw.VBox(objects))

class IndexSubIndexSelectorSelect(FullSelector):
    def __init__(self, parent):
        # Define the widgets to create
        args = {}
        args["subindex_select"] = {
            "options_function": parent.get_subindices,
            "value_function": parent.get_subindex,
            "function" : ipyw.Dropdown,
            "result" : parent.set_subindex,
            "conversion": None,
        }
        args["index_select"] = {
            "options_function": parent.get_indices,
            "value_function": parent.get_index,
            "function": ipyw.Dropdown,
            "result" : parent.set_index,
            "conversion": None,
        }
        args["selector_select"] =  {
            "options_function": parent.get_selectors,
            "value_function": parent.get_selector,
            "function": ipyw.Dropdown,
            "result": parent.set_selector,
            "conversion": None,
        }
        super().__init__(parent, args)

            
def gsv_(key, item, obj, docstr=None):
    """Generator function for a set value function for the multiwidget class"""
    def set_value(value):
        if notempty(value):
            if obj._ipywidgets[key]["conversion"] is None:
                obj._ipywidgets[key]["widget"].value = value
            else:
                obj._ipywidgets[key]["widget"].value = obj._ipywidgets[key]["conversion"](value)
        else:
            obj._ipywidgets[key]["widget"].value = self._ipywidgets[key]["function"]().value
        # Perform callback to set the result.
        obj._ipywidgets[key]["result"](obj._ipywidgets[key]["widget"].value)
    set_value.__docstr__ = docstr
    return set_value

def gwc_(key, item, obj, docstr=None):
    """Generator functions for propagating changes to other widgets on this change."""
    name = "on_" + key + "_change"
    def on_change(change):
        obj._ipywidgets[key]["set_value"](change.new)
        for other_key, item in obj._ipywidgets.items():
            if other_key == key:
                pass
            else:
                item["update"]()
    on_change.__name__ = name
    on_change.__docstr__ = docstr
    return on_change
                    
def gwu_(key, item, obj, docstr=None):
    """Generator function for making update calls for a given widget."""
    def on_other_widgets_change():
        if "value_function" in obj._ipywidgets[key]:
            obj._ipywidgets[key]["widget"].value = obj._ipywidgets[key]["value_function"]()
        if "option_function" in obj._ipywidgets[key]:
            obj._ipywidgets[key]["widget"].options = obj._ipywidgets[key]["options_funtion"]()
        on_other_widgets_change.__name__ = key
        on_other_widgets_change.__docstr__ = docstr
    return on_other_widgets_change

def gwf_(name, function, conversion=None, default_args={}, docstr=None):
    """This function wraps the widget function and calls it with any additional default arguments as specified."""
    def widget_function(**args):
        all_args = default_args.copy()
        all_args.update(args)
        return FieldWidget(
            function=function,
            conversion=conversion,
            **all_args,
        )
    widget_function.__name__ = name
    widget_function.__docstr__ = docstr
    return widget_function

def populate_widgets(list_stateful_widgets):
    """populate_widgets: Automatically creates widget wrapper objects and adds them to the module."""
    this_module = sys.modules[__name__]
    for widget in list_stateful_widgets:
        setattr(
            this_module,
            widget["name"],
            gwf_(**widget),
        )

def MyFileChooser(**args):
    """Create a simple Dropdown box to allow file selection from a given path."""
    if "directory" not in args:
        directory = "."
    else:
        directory = args["directory"]

    if "path" in args:
        directory = os.path.join(path, directory)
        
    if "glob" not in args:
        globname = "*"
    else:
        globname = args["glob"]
    files = glob.glob(os.path.join(os.path.expandvars(directory), globname))
    dirs = []
    options = []
    for option in [''] + dirs + files:
        options.append(os.path.basename(option))
    args["options"] = options
    
    return ipyw.Dropdown(**args)



def interact(function, **args):
    newargs = {}
    for key, widget in args.items():
        newargs[key] = widget.widget
    ipyw.interact(function, **newargs)

def interact_manual(function, **args):
    newargs = {}
    for key, widget in args.items():
        newargs[key] = widget.widget
    ipyw.interact_manual(function, **newargs)

def interactive(function, **args):
    newargs = {}
    for key, widget in args.items():
        newargs[key] = widget.widget
    ipyw.interactive(function, **newargs)


fixed = ipyw.fixed

class SaveButton(ReferiaWidget):
    def __init__(self, **args):
        args["description"] = "Save Flows"
        super().__init__(**args)

    def on_click(self, b):
        self._parent.save_flows()

class ReloadButton(ReferiaWidget):
    def __init__(self, **args):
        args["description"] = "Reload Flows"
        super().__init__(**args)

    def on_click(self, b):
        self._parent.load_flows()

    
populate_widgets(list_stateful_widgets)

