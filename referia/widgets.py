import os
import sys
import glob

import ipywidgets as ipyw
import markdown

from .config import *
from .log import Logger
from . import display

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



class MyWidget:
    def __init__(self, function, conversion, **args):
        self.ipywidget = function(**args)
        self.ipywidget.observe(self.on_value_change)

    def on_value_change(self, change):
        self.set_value(change.new)
        
    def get_value(self):
        return self.ipywidget.value
    
    def set_value(self, v):
        self.ipywidget.value = v
    
def gwf_(name, function, conversion=None, default_args={}, docstr=None):
    """This function wraps the widget function and calls it with any additional default arguments as specified."""
    def widget_function(**args):
        all_args = default_args.copy()
        all_args.update(args)
        return MyWidget(
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


populate_widgets(list_widgets)

