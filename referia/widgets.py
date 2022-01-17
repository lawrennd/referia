import ipywidgets
from ipyfilechooser import FileChooser
import os
import glob

def MyCheckbox(**args):
    # Deal with weird bug where value is passed as an np.bool_ by wrapping Checkbox
    args["value"] = bool(args["value"])
    return ipywidgets.Checkbox(**args)


def MyFileChooser(**args):

    if "directory" not in args:
        directory = "."
    else:
        directory = args["directory"]
        
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
