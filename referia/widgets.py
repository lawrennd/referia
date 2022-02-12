import ipywidgets
from ipyfilechooser import FileChooser
import os
import glob

from .config import *
from .log import Logger
from . import display

log = Logger(
    name=__name__,
    level=config["logging"]["level"],
    filename=config["logging"]["filename"]
)


list_widgets = [
    {
        "name" : "IntSlider",
        "func" : ipywidgets.IntSlider,
        "arg" : None,
        "docstr" : None,
    },
    {
        "name" : "FloatSlider",
        "func" : ipywidgets.FloatSlider,
        "arg" : None,
        "docstr" : None,
    },
    {
        "name" : "Checkbox",
        "func" : ipywidgets.Checkbox,
        "arg" : None,
        "docstr" : None,
    },
    {
        "name" : "Text",
        "func" : ipywidgets.Text,
        "arg" : None,
        "docstr" : None,
    },
    {
        "name" : "Textarea",
        "func" : ipywidgets.Textarea,
        "arg" : None,
        "docstr" : None,
    },
    {
        "name" : "Combobox",
        "func" : ipywidgets.Combobox,
        "arg" : None,
        "docstr" : None,
    },
    {
        "name" : "Dropdown",
        "func" : ipywidgets.Dropdown,
        "arg" : None,
        "docstr" : None,
    },
    {
        "name" : "Label",
        "func" : ipywidgets.Label,
        "arg" : None,
        "docstr" : None,
    },
    {
        "name" : "Layout",
        "func" : ipywidgets.Layout,
        "arg" : None,
        "docstr" : None,
    },
    {
        "name" : "HTML",
        "func" : ipywidgets.HTML,
        "arg" : None,
        "docstr" : None,
    },
    {
        "name" : "HTMLMath",
        "func" : ipywidgets.HTMLMath,
        "arg" : None,
        "docstr" : None,
    },
    {
        "name" : "DatePicker",
        "func" : ipywidgets.DatePicker,
        "arg" : None,
        "docstr" : None,
    },
]

for name, func in widgets_dict.items():
    dataset_test.append(
        {
            "dataset_name": name,
            "dataset_function": func,
            "arg": None,
            "docstr": func.__doc__,
        }
    )


other = [jslink, jsdlink, MyCheckbox, MyFileChooser, Markdown]

def gwf_(name, function, args=None, docstr=None):
    """Generate widget function"""
    def widget_function(self, **args):
        return MyWidget(function)
    return widget_function

def populate_widgets(cls, dataset_test):
    """populate_dataset: Auto create dataset test functions."""
    for dataset in dataset_test:
        base_funcname = "test_" + dataset["dataset_name"]
        funcname = base_funcname
        i = 1
        while funcname in cls.__dict__.keys():
            funcname = base_funcname + str(i)
            i += 1
        _method = gtf_(**dataset)
        setattr(cls, _method.__name__, _method)


class MyWidget:
    def __init__(self):
        

def MyCheckbox(**args):
    """Deal with behaviour where value is passed as an np.bool_ by wrapping Chec
kbox"""

    def on_value_change(change):
        change.owner.value = bool(change.new)
    
    if "value" in args:
        args["value"] = bool(args["value"])
    mycheck = ipywidgets.Checkbox(**args)
    mycheck.observe(on_value_change, names='value')
    
    return mycheck
    
def Markdown(**args):
    """Create a simple markdown widget based on the HTML widget."""

    def on_value_change(change):
        change.owner.value = display.markdown2html(change.new)
        
    if "value" in args:
        args["value"] = display.markdown2html(args["value"])

    mymark = ipywidgets.HTMLMath(**args)
    mymark.observe(on_value_change, names='value')
        
    return mymark

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
    
    return ipywidgets.Dropdown(**args)
