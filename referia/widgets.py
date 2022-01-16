import ipywidgets
from ipyfilechooser import FileChooser
import os

def MyCheckbox(**args):
    # Deal with weird bug where value is passed as an np.bool_ by wrapping Checkbox
    args["value"] = bool(args["value"])
    return ipywidgets.Checkbox(**args)


def MyFileChooser(**args):    
    if "path" not in args:
        path = "."
    else:
        path = args["path"]
    root, dirs, files = os.walk(path)
    args["options"] =[''] + dirs + files
    return Dropdown(**args)
