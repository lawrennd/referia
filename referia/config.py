import os
import yaml
import numpy as np

GSPREAD_AVAILABLE=True
try:
    import gspread_pandas.conf as gspdconf
except ImportError:
    GSPREAD_AVAILABILE=False
    

default_file = os.path.join(os.path.dirname(__file__), "defaults.yml")
local_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "machine.yml"))
user_file = '_referia.yml'

config = {}

if os.path.exists(default_file):
    with open(default_file) as file:
        config.update(yaml.load(file, Loader=yaml.FullLoader))

if os.path.exists(local_file):
    with open(local_file) as file:
        config.update(yaml.load(file, Loader=yaml.FullLoader))

if os.path.exists(user_file):
    with open(user_file) as file:
        config.update(yaml.load(file, Loader=yaml.FullLoader))

if config=={}:
    raise ValueError(
        "No configuration file found at either "
        + user_file
        + " or "
        + local_file
        + " or "
        + default_file
        + "."
    )

for key, item in config.items():
    if item is str:
        config[key] = os.path.expandvars(item)

if "logging" in config:
    if not "level" in config["logging"]:
        config["logging"]["level"] = 20
    
    if not "filename" in config["logging"]:
        config["logging"]["filename"] = "referia.log"
else:
    config["logging"] = {"level": 20, "filename": "referia.log"}

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

