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


class MyCheckbox(ipywidgets.Checkbox):
    def __init__(self, **args):
        ipywidgets.Checkbox.__init__(self, **args)

    @property
    def value(self):
        return ipywidgets.Checkbox.value

    @value.setter
    def value(self, v):
        ipywidgets.Checkbox.value = bool(v)

class Markdown(ipywidgets.HTMLMath):
    def __init__(self, **args):
        if "value" in args:
            self.value = args["value"]
            args["value"] = self._html_value
        else:
            self.value = ""
        ipywidgets.HTMLMath.__init__(self, **args)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v
        self._html_value = display.markdown2html(self._value)
        ipywidgets.HTMLMath.value = self._html_value


def OldMyCheckbox(**args):
    """Deal with behaviour where value is passed as an np.bool_ by wrapping Checkbox"""

    def on_value_change(change):
        change.owner.value = bool(change.new)
    
    if "value" in args:
        args["value"] = bool(args["value"])
    mycheck = ipywidgets.Checkbox(**args)
    mycheck.observe(on_value_change, names='value')
    
    return mycheck

    
def OldMarkdown(**args):
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
