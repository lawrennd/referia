import os
import re
from unidecode import unidecode
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import Markdown, display
from ipywidgets import IntSlider, Text, Dropdown, Label
from ipywidgets import interact, interactive, fixed, interact_manual

from .config import *
from . import access

"""Place commands in this file to assess the data you have downloaded. How are missing values encoded, how are outliers encoded? What do columns represent, makes rure they are correctly labeled. How is the data indexed. Create visualisation routines to assess the data (e.g. in bokeh). Ensure that date formats are correct and correctly timezoned."""

def data():
    """Joint the two data together, the allocation and additional information."""
    allocation = access.allocation()
    if "additional" in config:
        additional = access.additional()    
        return allocation.join(additional, rsuffix="additional")
    else:
        return allocation
    
def view_series(ds):
    display(Markdown(view_text(ds)))
    if "localpdf" in config and "field" in config["localpdf"] and ds[config["localpdf"]["field"]] is str:
        os.system('open ' + '--background ' + '"' + os.path.join(config["localpdf"]["directory"],ds[config["localpdf"]["field"]]) + '"')
    if "search" in config and "url" in config["search"] and "field" in config["search"]:
        if "browser" in config:
            browser=config["browser"]
        else:
            browser="Google Chrome.app" 
        os.system('open ' + '-a "' + browser + '" --background ' + '"' + _search_url(ds) + '"')


def _search_url(ds):
    """Construct the search query"""
    query = ds[config["search"]["field"]].replace(' ', '%20')
    return unidecode(config["search"]["url"] + query)


def view_text(ds):
    """Text that views a a single record."""
    text = ""
    if "viewer" in config:
        for view in config["viewer"]:
            format = {}
            if "format" in view:
                for field, column in view["format"].items():
                    format[field] = ds[column] 
                
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
                text += view["display"].format(**format)
    return text

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
            fields[clean_string(display["field"])] = display["field"]
        for key, value in kwargs.items():
            if fields[key] in write_df.columns:
                write_df.at[index, fields[key]] = value
        write_df.at[index, config["timestamp_field"]] = pd.to_datetime("today")                    
        access.write_scores(write_df)


    def update_index(df, write_df, index):
        if index not in df.index:
            raise ValueError("Invalid index")

        ds = df.loc[index]
        write_ds = write_df.loc[index]
        view_series(ds)

        scored = write_df[config["scored"]["field"]].count()
        total = len(write_df[config["scored"]["field"]])
        remain = total - scored

        interact_args = {}
        if "scorer" in config:
            for score in config["scorer"]:
                if score["field"] in write_ds:
                    if pd.notna(write_ds[score["field"]]):
                        score["args"]["value"] = write_ds[score["field"]]
                globs = globals()
                if score["type"] in globs:
                    interact_args[clean_string(score["field"])] = globs[score["type"]](**score["args"])
                else:
                    raise Exception("Have not loaded " + score["type"] + " interaction type.")
        
        interact_args["progress_label"] = Label("{remain} to go. Scored {scored} from {total} which is {perc:.3g}%".format(remain=remain, scored=scored, total=total, perc=scored/total*100))
                    
        interact_manual(
            update_df, 
            index=fixed(index),
            df=fixed(df),
            write_df=fixed(write_df),
            **interact_args
        )



    index_select = Dropdown(options=df.index, value=index)
    interact(update_index, index=index_select, df=fixed(df), write_df=fixed(write_df))
    print("Saved")


