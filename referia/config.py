import os
import yaml
import numpy as np

GSPREAD_AVAILABLE=True
try:
    import gspread_pandas.conf as gspdconf
except ImportError:
    GSPREAD_AVAILABILE=False



def load_user_config(user_file="_referia.yml", directory="."):
    filename = os.path.join(os.path.expandvars(directory), user_file)
    conf = {}
    if not os.path.exists(filename):
        return conf
    
    with open(filename) as file:
        conf = yaml.load(file, Loader=yaml.FullLoader)

    parent = None
    inherit = {}
    if "inherit" in conf:
        # Load in parent configuration
        inherit = conf["inherit"]
        writable = "writable" in inherit and inherit["writable"]
        if "ignore" not in inherit:
            inherit["ignore"] = []
        if "append" not in inherit:
            inherit["append"] = [] 

        del conf["inherit"]
        parent = load_user_config(user_file, inherit["directory"])
        viewelem = {"display": 'Parent assesser available <a href="' + os.path.join(inherit["directory"], "assessment.ipynb") + '" target="_blank">here</a>.'}

        # Add links to parent assessment by placing in viewer.
        if "viewer" in conf:
            if type(conf["viewer"]) is list:
                conf["viewer"] = [viewelem] + conf["viewer"]
            else:
                conf["viewer"] = [viewelem, conf["viewer"]]
        else:
            conf["viewer"] = [viewelem]
            inherit["append"].append("viewer")

    if parent is not None:
        # Place loaded conf under the parent conf.
        additional = []
        for key, item in parent.items():
            if key in inherit["ignore"]:
                # Ignore this key when inheriting
                continue
            if key in inherit["append"] and key in conf:
                # Append to this key when inheriting
                if key == "additional":
                    if type(item) is list:
                        additional = additional + item
                    else:
                        additional = additional + [item]
                    continue
                if type(conf[key]) is list:
                    if type(item) is list:
                        conf[key] = item + conf[key]
                    else:
                        conf[key] = [item] + conf[key]
                    continue
                if type(conf[key]) is dict:
                    item.update(conf[key])
                    conf[key] = item
                    continue
                if type(conf[key]) is None:
                    conf[key] = item
                else:
                    raise ValueError("Cannot append to non dictionary or list type.")
                continue
            
            if key == "scores" and not writable:
                additional = additional + [item]
                continue

            if key == "series" and not writable:
                item["series"] = True # Convert series to be readable only
                additional = additional + [item]
                continue

            if key not in conf:
                # Augment the configuration with the parent key.
                conf[key] = parent[key]
                continue

        if "additional" in conf:
            if type(conf["additional"]) is list:
                conf["additional"] = additional + conf["additional"]
            else:
                conf["additional"] = additional + [conf["additional"]]
        elif len(additional)>0:
            conf["additional"] = additional
    return conf

def load_config():
    default_file = os.path.join(os.path.dirname(__file__), "defaults.yml")
    local_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "machine.yml"))
    user_file = '_referia.yml'

    conf = {}

    if os.path.exists(default_file):
        with open(default_file) as file:
            conf.update(yaml.load(file, Loader=yaml.FullLoader))

    if os.path.exists(local_file):
        with open(local_file) as file:
            conf.update(yaml.load(file, Loader=yaml.FullLoader))

    conf.update(load_user_config(user_file))

    if conf=={}:
        raise ValueError(
            "No configuration file found at either "
            + user_file
            + " or "
            + local_file
            + " or "
            + default_file
            + "."
        )

    for key, item in conf.items():
        if item is str:
            conf[key] = os.path.expandvars(item)

    if "logging" in conf:
        if not "level" in conf["logging"]:
            conf["logging"]["level"] = 20

        if not "filename" in conf["logging"]:
            conf["logging"]["filename"] = "referia.log"
    else:
        conf["logging"] = {"level": 20, "filename": "referia.log"}
    return conf

config = load_config()

conf_dir = None
file_name = "google_secret.json"

if "google_oauth" in config:
    if "directory" in config["google_oauth"]:
        conf_dir = os.path.expandvars(config["google_oauth"]["directory"])
    if "keyfile" in config["google_oauth"]:
        file_name = config["google_oauth"]["keyfile"]


try:
    config["gspread_pandas"] = gspdconf.get_config(
        conf_dir=conf_dir,
        file_name=file_name,
    )
except:
    GSPREAD_AVAILABLE=False
