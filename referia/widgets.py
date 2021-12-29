import ipywidgets

def MyCheckbox(**args):
    # Deal with weird bug where value is passed as an np.bool_ by wrapping Checkbox
    args["value"] = bool(args["value"])
    return ipywidgets.Checkbox(**args)
