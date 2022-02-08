import os
import glob
import ipywidgets

def MyCheckbox(**args):
    """Deal with behaviour where value is passed as an np.bool_ by wrapping Checkbox"""
    args["value"] = bool(args["value"])
    return ipywidgets.Checkbox(**args)


def MyFileChooser(**args):
    """Simple file chooser based on Dropdown"""
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

