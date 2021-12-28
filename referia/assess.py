import os
import re

import copy
import tempfile
from shutil import copy2
import filecmp

from unidecode import unidecode
import random
import string
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import Markdown, display
from ipywidgets import IntSlider, FloatSlider, Checkbox, Text, Textarea, Combobox, Dropdown, Label, Layout, HTML, HTMLMath
from ipywidgets import interact, interactive, fixed, interact_manual

from .config import *
from .log import Logger
from .util import to_camel_case
from . import access

TMPPDFFILES={}

log = Logger(
    name=__name__,
    level=config["logging"]["level"],
    filename=config["logging"]["filename"]
)

def MyCheckbox(**args):
    # Deal with weird bug where value is passed as an np.bool_ by wrapping Checkbox
    args["value"] = bool(args["value"])
    return Checkbox(**args)

def data():
    """Joint the two data together, the allocation and additional information."""
    allocation = access.allocation()
    if "additional" in config:
        additional = access.additional()    
        return allocation.join(additional, rsuffix="additional")
    else:
        return allocation

def clear_temp_files():
    delete_keys = []
    for filename, values in TMPPDFFILES.items():
        destname = os.path.join(values["tmpdirectory"], filename)
        delete_keys.append(filename)
        if os.path.exists(destname):
            log.info("Removing temporary file {filename}.".format(filename=destname))
            os.remove(destname)

    for key in delete_keys:
        del TMPPDFFILES[key]

def open_pdf(filename):
    os.system('open ' + '--background ' + '"' + filename + '"')
    
def edit_pdfs(ds):
    """Use the system viewer to show a PDF containing relevant information to the assessment."""

    if "editpdf" in config:
        for display in config["editpdf"]:
            if "field" in display and type(ds[display["field"]]) is str:
                storedirectory = os.path.expandvars(display["storedirectory"])
                origfile = os.path.join(os.path.expandvars(display["sourcedirectory"]),ds[display["field"]])
                editfilename = ds[config["allocation"]["index"]] + "_" + to_camel_case(display["field"]) + ".pdf"
                destfile = os.path.join(storedirectory,editfilename)
                if not os.path.exists(storedirectory):
                    os.makedirs(storedirectory)
                
                if not os.path.exists(destfile):
                    if os.path.exists(origfile):
                        log.debug("Copying {origfile} to {destfile}.".format(origfile=origfile, destfile=destfile))
                        copy2(origfile, destfile)
                    else:
                        log.warning("Warning editpdf {origfile} does not exist.".format(origfile=origfile))
                open_pdf(destfile)

def view_pdfs(ds):
    """Use the system viewer to show a PDF containing relevant information to the assessment."""

    if "localpdf" in config:
        for display in config["localpdf"]:
            filename = ""
            tmpname = ""
            if "field" in display and type(ds[display["field"]]) is str:
                filename = os.path.expandvars(os.path.join(display["directory"],ds[display["field"]]))
                tmpname = to_camel_case(display["field"])
            elif "file" in display:
                filename = os.path.expandvars(os.path.join(display["directory"], display["file"]))
            if os.path.exists(filename):
                if len(tmpname)>0:
                    tmpdirectory = tempfile.gettempdir()
                    destfile = ds[config["allocation"]["index"]] + "_" + tmpname + ".pdf"
                    destname = os.path.join(tmpdirectory, destfile)
                    if not os.path.exists(destname):
                        log.debug("Copying {origfile} to {destfile}.".format(origfile=filename, destfile=destname))
                        copy2(filename, destname)
                    TMPPDFFILES[destfile] = {
                        "origfile": filename,
                        "tmpdirectory": tmpdirectory,
                    }
                    open_pdf(destname)
                else:
                    open_pdf(filename)
            else:
                log.warning("localpdf {filename} does not exist.".format(filename=filename))

def view_urls(ds):
    if "browser" in config:
        browser=config["browser"]
    else:
        browser="Google Chrome.app" 
    if "urls" in config:
        for display in config["urls"]:
            if "url" in display:
                if "field" in display and type(ds[display["field"]]) is str:
                    urlterm = ds[display["field"]]
                elif "display" in display:
                    urlterm = view_to_text(display, ds)
                else:
                    urlterm = ""
                os.system('open ' + '-a "' + browser + '" --background ' + '"' + unidecode(display["url"] + urlterm.replace(" ", "%20")) + '"')

def view_series(ds):
    clear_temp_files()    
    view_pdfs(ds)
    edit_pdfs(ds)
    view_urls(ds)
    display(Markdown(view_text(ds)))


def view_to_text(view, ds):
    format = {}
    if "format" in view:
        for key, column in view["format"].items():
            format[key] = ds[column] 

    show_display = True
    if "conditions" in view:
        for condition in view["conditions"]:
            if "present" in condition:
                if not condition["present"]["field"] in ds:
                    show_display = False
                    break
            if "equal" in condition:
                if not ds[condition["equal"]["field"]] == condition["equal"]["value"]:
                    show_display = False
                    break
    if show_display:
        return view["display"].format(**format)
    else:
        return ""
    
def viewer_to_text(key, ds):
    """Create a formatted text output from a yaml entry with base text and format keys."""
    text = ""
    if key in config:
        for view in config[key]:
            text += view_to_text(view, ds)
    return text



def view_text(ds):
    """Text that views a a single record."""
    if "viewer" in config:
        return viewer_to_text("viewer", ds)
    else:
        return ""

def view(data):
    """Provide a view of the data that allows the user to verify some aspect of its quality."""
    fig, ax = plt.subplots(figsize=(8, 5))
    data.hist('Score', bins=np.linspace(-.5, 12.5, 14), width=0.8, ax=ax)
    ax.set_xticks(range(0,13))




def clean_string(instring):
    return re.sub("\W+|^(?=\d)","_", instring)

def score(index, df, write_df):
                    
    def update_df(df, write_df, index, progress_label, **kwargs):
        details = config["scorer"]
        fields = {}
        for display in details:
            if "field" in display:
                fields[clean_string(display["field"])] = display["field"]
        for key, value in kwargs.items():
            if key in fields:
                if fields[key] in write_df.columns:
                    write_df.at[index, fields[key]] = value
                else:
                    log.info("{field} not in write columns ... adding.".format(field=fields[key]))
                    write_df[fields[key]] = None
                    write_df.at[index, fields[key]] = value

        if "timestamp_field" in config:
            timestamp_field = config["timestamp_field"]
        else:
            timestamp_field = "Timestamp"
        write_df.at[index, timestamp_field] = pd.to_datetime("today")
        if "created_field" in config:
            created_field = config["created_field"]
        else:
            created_field = "Created"
        if created_field not in write_df.columns or write_df.at[index, created_field] == "" or pd.isna(write_df.at[index, created_field]):
            write_df.at[index, created_field] = pd.to_datetime("today")
        if "combinator" in config:
            for view in config["combinator"]:
                if "field" in view:
                    write_df.at[index, view["field"]] = view_to_text(view, write_df.loc[index])
                else:
                    log.error("Missing key 'field' in combinator view.")
            
        access.write_scores(write_df)

        


    def update_index(df, write_df, index):
        if index not in df.index:
            raise ValueError("Invalid index")
        log.info("Index {index} selected.".format(index=index))

        
        ds = df.loc[index]
        write_ds = write_df.loc[index]
        view_series(ds)
        
        if config["scored"]["field"] in write_df:
            scored = write_df[config["scored"]["field"]].count()
            total = len(write_df[config["scored"]["field"]])
            remain = total - scored

        interact_args = {}
        if "scorer" in config:
            for orig_score in config["scorer"]:
                score = copy.deepcopy(orig_score)
                if "field" in score:
                    name = clean_string(score["field"])
                    if score["field"] in write_ds:
                        if pd.notna(write_ds[score["field"]]):
                            score["args"]["value"] = write_ds[score["field"]]
                    else:
                        log.warning("{field} not in write_ds".format(field=score["field"]))
                else:
                    name = "".join(random.choice(string.ascii_letters) for _ in range(39))
                globs = globals()
                if "layout" in score:
                    score["args"]["layout"] = Layout(**score["layout"])
                    
                if score["type"] in globs:
                    interact_args[name] = globs[score["type"]](**score["args"])
                else:
                    raise Exception("Have not loaded " + score["type"] + " interaction type.")
        
        if config["scored"]["field"] in write_df:
            interact_args["progress_label"] = Label("{remain} to go. Scored {scored} from {total} which is {perc:.3g}%".format(remain=remain, scored=scored, total=total, perc=scored/total*100))
        else:
            interact_args["progress_label"] = fixed("None")
        interact_manual(
            update_df, 
            index=fixed(index),
            df=fixed(df),
            write_df=fixed(write_df),
            **interact_args
        )

            
    if "sortby" in config and "field" in config["sortby"] and config["sortby"]["field"] in df:
        if "ascending" in config["sortby"]:
            ascending = config["sortby"]["ascending"]
        else:
            ascending=True
        log.info("Sorting by {field}".format(field=config["sortby"]["field"]))
        df.sort_values(by=config["sortby"]["field"], ascending=ascending, inplace=True)

    index_select = Dropdown(options=df.index, value=index)
    interact(update_index, index=index_select, df=fixed(df), write_df=fixed(write_df))


