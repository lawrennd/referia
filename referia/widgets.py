import os
import sys
import glob

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

list_widgets = [
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
        self._conversion = None
        self._parent = None
        self._ipywidget_function = ipyw.Textarea
        self._display = None
        self._column_name = None
        self._field_name = None
        self.private = False
        if "conversion" in args:
            self._conversion = args["conversion"]
        if self._conversion is not None and "value" in args:
            args["value"] = self._conversion(args["value"])
        if "function" in args:
            self._ipywidget_function = args["function"]
        if "parent" in args:
            self._parent = args["parent"]
        if "display" in args:
            self._display = args["display"]
        if "column_name" in args:
            self._column_name = args["column_name"]
        if "field_name" in args:
            self._field_name = args["field_name"]
            
        # Is this a private field (one that doesn't update the parent data)
        if self._field_name is not None and self._field_name[0] == "_": 
            self.private = True
            
        if self.private and "description" not in args: 
            args["descripton"] = " "

        self._ipywidget = self._ipywidget_function(**args)
        self._ipywidget.observe(self.on_value_change, names='value')


    def on_value_change(self, value):
        pass

    def null(self, void):
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
    
class FieldWidget(ReferiaWidget):
    """Widget for editing field values in parent data."""
    def __init__(self, function=None, conversion=None, **args):
        args["function"] = function
        args["conversion"] = conversion
        super().__init__(**args)
        
    def on_value_change(self, change):
        self.set_value(change.new)
        if not self.private and self._parent is not None:
            self._parent._data.set_column(self.get_column())
            self._parent._data.set_value(self.get_value())

    def refresh(self):
        self._ipywidget.observe(self.null, names='value')
        if self._display is not None:
            self.set_value(self._display.format(**self._parent._data.mapping()))
        else:
            column = self.get_column()
            if not self.private and column is not None and self._parent is not None:
                self._parent._data.set_column(column)
                self.set_value(self._parent._data.get_value())

        self._ipywidget.observe(self.on_value_change, names="value")
            

class IndexSelector(ReferiaWidget):
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
            self._parent._data.set_index(self.get_value())
            system.view_series(self._parent._data)

    def refresh(self):
        pass
    
class FullSelector(ReferiaWidget):
    def __init__(self):
        args = {
            "options": parent.subindex,
            "value": parent.get_subindex(),
            "parent" : parent,
            "function" : ipyw.Dropdown,
        }
        super().__init__(**args)

        index_args = {
            "options": parent.index,
            "value": parent.get_index(),
            "parent" : parent,
            "function": ipyw.Dropdown,
        }
        self._ipywidget_index_selector_function = index_args["function"]
        self._ipywidget_index_selector = self._ipywidget_index_selector_function(**index_args)

    
#        select=Dropdown(
#            options=self.get_subindices(),
#            value=self.get_subindex(),
#        )
#        select=Dropdown(
#            options=self.get_selectors(),
#            value=self.get_selector(),
#        )
#        function = ipyw.Dropdown
#         args = {
#             "options": self._parent.index,
#             "value": self._parent.get_index(),
#         }
#         if self._parent._select_selector:
#             self._select_selector=ipyw.Dropdown(
#                 options=self._parent.get_selectors(),
#                 value=self._parent.get_selector(),
#             )
#         else:
#             self._select_selector = None
            
#         if self._parent._select_subindex:
#             self._select_subindex=ipyw.Dropdown(
#                 options=self._parent.get_subindices(),
#                 value=self._parent.get_subindex(),
#             )
#         else:
#             self._select_subindex = None

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

def populate_widgets(list_widgets):
    """populate_widgets: Automatically creates widget wrapper objects and adds them to the module."""
    this_module = sys.modules[__name__]
    for widget in list_widgets:
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

populate_widgets(list_widgets)

