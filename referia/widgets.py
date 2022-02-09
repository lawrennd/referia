import ipywidgets
from ipyfilechooser import FileChooser
import os
import glob


from . import display

def MyCheckbox(**args):
    """Deal with behaviour where value is passed as an np.bool_ by wrapping Chec
kbox"""
    if "value" in args:
        args["value"] = bool(args["value"])
    return ipywidgets.Checkbox(**args)

def MyMarkdown(**args):
    """Create a simple markdown widget based on the HTML widget."""
    if "value" in args:
        args["value"] = markdown2html(args["value"])
    mymark = ipywidgets.HTMLMath(**args)

    def on_value_change(mymark):
        mymark.value = display.markdown2html(mymark.new)
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
