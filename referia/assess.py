import os
import re

import json
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
from ipywidgets import IntSlider, FloatSlider, Checkbox, Text, Textarea, Combobox, Dropdown, Label, Layout, HTML, HTMLMath, DatePicker
from ipywidgets import interact, interactive, fixed, interact_manual

from pandas.api.types import is_string_dtype, is_numeric_dtype

import pypdftk as tk

from .widgets import MyCheckbox, MyFileChooser
from .config import *
from .log import Logger
from .util import to_camel_case
from . import access

TMPPDFFILES={}
INTERACT_ARGS = {}
COLUMN_NAMES = {}
DEFAULT_WRITEDF_VALS = pd.Series()
DEFAULT_WRITEDF_SOURCE = pd.Series()

interact_manual.opts["manual_name"] = "Save Score"

log = Logger(
    name=__name__,
    level=config["logging"]["level"],
    filename=config["logging"]["filename"]
)

class Data:
    def __init__(self):
        self._data = None
        self._writedata = None
        self._index = None
        # The series data associated with the input.
        self._writeseries = None
        # The entry column value from the series to use
        self._subindex = None
        # Which entry column in the series to choose from.
        self._selector = None
        self._load_data()

    @property
    def index(self):
        if self._data is not None:
            return self._data.index
        else:
            return None

    @property
    def columns(self):
        columns = []
        if self._data is not None:
            columns += list(self._data.columns)
        if self._writedata is not None:
            columns = list(self._writedata.columns)
        if self._writeseries is not None:
            columns = list(self._writeseries.columns)
        # Should perhaps make this unique column list? As in practice it behaves that way.
        return pd.Index(columns)
        
    def _allocation(self):
        """Load in the allocation spread sheet to data frames."""
        self._data = access.allocation()
        self._data = self._finalize_df(self._data, config["allocation"])

    def _additional(self):
        """Load in the allocation spread sheet to data frames."""

        if type(config["additional"]) is not list:
            configs = [config["additional"]]
        else:
            configs = config["additional"]

        for i, conf in enumerate(configs):
            if i == 0:
                additional = self._finalize_df(access.additional(conf), conf)
            else:
                additional = additional.join(
                    self._finalize_df(access.additional(conf), conf),
                    rsuffix="_" + str(i)
                )

        self._data = self._data.join(additional, rsuffix="additional")

    def _scores(self):
        """Load in the score data to data frames."""
        self._writedata = access.scores(self.index)
        self._writedata = self._finalize_df(self._writedata, config["scores"])


    def _series(self):
        """Load in the series data to data frames."""
        if "selector" in config["series"]:
            self._selector = config["series"]["selector"]
        self._writeseries = access.series(self.index)
        self._writeseries = self._finalize_df(self._writeseries, config['series'])

    def _load_data(self):
        """Load te data specified in the _referia.yml file."""
        self._allocation()
        if "additional" in config:
            log.info("Joining allocation and additional information.")
            self._additional()

        # If sorting is requested do it here.
        if "sortby" in config and "field" in config["sortby"] and config["sortby"]["field"] in self._data:
            if "ascending" in config["sortby"]:
                ascending = config["sortby"]["ascending"]
            else:
                ascending=True
            field=config["sortby"]["field"]
            log.info(f"Sorting by \"{field}\"")
            self._data.sort_values(by=field, ascending=ascending, inplace=True)
        if "series" in config:
            self._series()
        if "scores" in config:
            self._scores()

    def set_index(self, index):
        """Index setter"""
        if self._data is not None and index not in self._data.index:
            raise ValueError("Invalid index")
        else:
            self._index = index
            self._subindex = None
            log.info(f"Index {index} selected.")

    def set_subindex(self, index):
        """Subindex setter"""
        if index is None:
            self._subindex = None
            log.info(f"Subindex set to None.")
            return

        if self._writeseries is not None and index not in self._writeseries[get_selector()].values:
            raise ValueError("Invalid subindex.")
        else:
            self._subindex=index
            log.info(f"Subindex {index} selected.")


    def get_index(self):
        if self._index is None and self._data is not None:
            log.info(f"No index set, using first index of data.")
            self.set_index(self._data.index[0])
        return self._index

    def get_selector(self):
        return self._selector

    def set_selector(self, column):
        """Set which column of the series is to be used for selection."""
        # Set to None to indicate that self._writedata is correct place for recording.
        if column is None:
            self._selector = None
            return

        if self._writeseries is not None and column not in self._writeseries.columns:
            raise ValueError("Invalid selector column.")
        else:
            self._selector = column
            if self.get_subindex() not in self._writeseries[column]:
                self.set_subindex(None)
            log.info(f"Column {column} of Data._writeseries selected for selection.")

    def get_subindex(self):
        if self._subindex is None and self._writeseries is not None:
            log.info(f"No subindex set, using first entry of Data._writeseries.")
            self.set_subindex(self.get_subseries().at[0, self.get_selector()])
        return self._index

    def get_subseries(self):
        return self._writeseries[self._writeseries.index.isin([self.get_index()])]

    def get_subindices(self):
        return self.get_subseries()[self._selector]

    def get_subindex(self):
        if self._subindex is None and self._writeseries is not None:
            log.info(f"No index set, using first index of data.")
            self.set_subindex(self.get_subindices()[0])
        return self._subindex

    def set_series_value(self, value, column):
        """Set a value in the write series data frame"""
        if column in self._data.columns:
            log.warning(f"Warning attempting to write to {column} in self._data.")

        if column not in self._writeseries.columns:
            self.add_series_column(column)

        _update_type(self._writeseries, column, value)
        self.get_subseries().at[get]

    def set_current_value(self, value, column):
        """Set a value to the write data frame"""    
        # If trying to set a numeric valued column's entry to a string, set the type of column to object.                       
        if column in self._data.columns:
            log.warning(f"Warning attempting to write to {column} in self._data.")

        if self.get_selector() is not None:
            if column not in self._writeseries.columns:
                self.add_series_column(column)
            _update_type(self._writeseries, column, value)
            self._writeseries.loc[
                self._writeseries.index.isin([self.get_index()])
                & (self._writeseries[self.get_selector()]==self.get_subindex()).values,
                column
            ] = value
            return

        else:
            if column not in self._writedata.columns:
                self.add_column(column)

            _update_type(self._writedata, column, value)
            self._writedata.at[self.get_index(), column] = value
            return

    def get_current_value(self, column):
        """Get a value from the data frame(s)"""

        # Ordering here dictates the priority of selection, first series, then writedata, then data.
        if self._selector is not None and self._writeseries is not None and column in self._writeseries.columns:
            return self._writeseries.loc[
                self._writeseries.index.isin([self.get_index()])
                & (self._writeseries[self.get_selector()]==self.get_subindex()).values,
                column
                ][0]
        elif self._writedata is not None and column in self._writedata.columns:
            return self._writedata.at[self.get_index(), column]
        elif self._data is not None and column in self._data.columns:
            return self._data.at[self.get_index(), column]
        else:
            log.warning(f"\"{column}\" not selected _WRITESERIES or in _WRITEDATA or _DATA returning \"None\"")
            return None

    def add_column(self, column):
        if column not in self._writedata.columns:
            log.info(f"\"{column}\" not in write columns ... adding.")
            self._writedata[column] = None
        else:
            log.warning(f"\"{column}\" requested to be added to write data but already exists.")

    def add_series_column(self, column):
        if column not in self._writeseries.columns:
            log.info(f"\"{column}\" not in series columns ... adding.")
            self._writeseries[column] = None
        else:
            log.warning(f"\"{column}\" requested to be added to series data but already exists.")

    def mapping(self, mapping=None):
        """Generate dictionary of mapping between variable names and column values."""
        if mapping is None:
            if "mapping" in config:
                mapping = config["mapping"]
            else:
                mapping = automapping()

        format = {}
        for key, column in mapping.items():
            format[key] = self.get_current_value(column)

        return format


    def conditions(self, entry):

        show_display = True
        if "conditions" in entry:
            for condition in entry["conditions"]:
                if "present" in condition:
                    if not condition["present"]["field"] in columns():
                        return False

                if "equal" in condition:
                    if not self.get_current_value(condition["equal"]["field"]) == condition["equal"]["value"]:
                        return False

        return True
            

    def _finalize_df(self, df, details):
        """for field in dtypes:
            if dtypes[field] is str_type:
                data[field].fillna("", inplace=True)"""

        if "fields" in details:
            for field in details["fields"]:
                column = pd.Series(index=df.index, dtype="object")
                if "name" in field:
                    if "value" in field:
                        for index in df.index:
                            format = self.mapping()
                            column[index] = field["value"].format(**format)

                    elif "source" in field and "regexp" in field:
                        regexp = field["regexp"]
                        if field["source"] not in df.columns:
                            log.warning(f"No column {source} in DataFrame.".format(source=field["source"]))
                        for index in df.index:
                            source = df.at[index, field["source"]]
                            match = re.match(
                                regexp,
                                source,
                            )
                            if match:
                                if len(match.groups())>1:
                                    log.warning(f"Multiple regular expression matches in {regexp}.")
                                column[index] = match.group(1)
                            else:
                                log.warning(f"No match of regular expression \"{regexp}\" to \"{source}\".")
                    else:
                        log.warning(f"Missing \"source\" or \"regexp\" (for regular expression derived fields) or \"value\" (for format derived fields) in fields.")
                    df[field["name"]] = column
                else:
                    log.warning(f"No \"name\" associated with field entry.")

        df.set_index(df[details["index"]], inplace=True)
        return df
    
    def to_score(self):
        if self._writedata is not None:
            return len(self._writedata.index)
        else:
            return 0

    def scored(self):
        if "scored" in config:
            if config["scored"]["field"] in self._writedata.columns:
                return self._writedata[config["scored"]["field"]].count()
            else:
                return 0
        

        
def data():
    return Data()
        

        

    
def clear_temp_files():
    delete_keys = []
    for filename, values in TMPPDFFILES.items():
        destname = os.path.join(values["tmpdirectory"], filename)
        delete_keys.append(filename)
        if os.path.exists(destname):
            log.info(f"Removing temporary file \"{filename}\".")
            os.remove(destname)

    for key in delete_keys:
        del TMPPDFFILES[key]

def open_localfile(filename):
    """Open a local file."""
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext == ".pdf":
        open_pdf(filename)
    elif ext == ".mp4":
        open_video(filename)
    elif ext == ".py":
        open_python(filename)
    elif ext == ".md" or ext == ".markdown":
        open_markdown(filename)
    else:
        log.info(f"Opening file \"{filename}\".")
        os.system(f"open --background \"{filename}\"")


def open_markdown(filename):
    """Use the system viewer to open a markdown file."""
    log.info(f"Opening file \"{filename}\".")
    os.system(f"open --background \"{filename}\"")

def open_python(filename):
    """Use the system viewer to open a python file."""
    log.info(f"Opening file \"{filename}\".")
    os.system(f"open --background \"{filename}\"")
    
def open_pdf(filename):
    """Use the system viewer to open a PDF."""
    log.info(f"Opening file \"{filename}\".")
    os.system(f"open --background \"{filename}\"")

def open_video(filename):
    """Use the system viewer to open a video."""
    log.info(f"Opening file \"{filename}\".")
    os.system(f"open --background \"{filename}\"")
    
def open_url(urlname):
    """Use the browser to open URL."""
    if "browser" in config:
        browser=config["browser"]
    else:
        browser="Google Chrome.app" 
    
    log.info(f"Opening url \"{urlname}\".")
    os.system(f"open -a \"{browser}\" --background \"{urlname}\"")

def notempty(val):
    return pd.notna(val) and val!=""

def empty(val):
    return pd.isna(val) or val==""

def copy_file(origfile, destfile, display):
    """Copy a file, or pages from it, for separate editing or viewing."""
    _, ext = os.path.splitext(origfile)
    ext = ext.lower()

    if os.path.exists(origfile):
        if ext == ".pdf" and "pages" in display and "first" in display["pages"] and "last" in display["pages"]:
            # Extract pages from a PDF
            firstpage = get_current_value(display["pages"]["first"])
            lastpage = get_current_value(display["pages"]["last"])
            if notempty(firstpage) and notempty(lastpage) and notempty(display["field"]):
                firstpage = int(firstpage)
                lastpage = int(lastpage)
                log.info(f"Extracting \"{destfile}\" from \"{origfile}\" pages {firstpage}-{lastpage}")
                tk.get_pages(
                    pdf_path=origfile,
                    ranges=[[firstpage,
                             lastpage]],
                    out_file=destfile,
                )
        else:
            log.info(f"Copying \"{origfile}\" to \"{destfile}\".")
            copy2(origfile, destfile)
    else:
        log.warning(f"Warning edit file \"{origfile}\" does not exist.")


def edit_files(data):
    """Use the system viewer to show a PDF containing relevant information to the assessment."""

    displays = []
    if "editpdf" in config:
        displays += config["editpdf"]
        
    for display in displays:
        if "field" in display:
            val = data.get_current_value(display["field"])
        if type(val) is str:
            storedirectory = os.path.expandvars(display["storedirectory"])
            origfile = os.path.join(os.path.expandvars(display["sourcedirectory"]),val)
            if "name" in display:
                filestub = display["name"] + ".pdf"
            else:
                filestub = to_camel_case(display["field"]) + ".pdf"
            editfilename = str(data.get_current_value(config["allocation"]["index"])) + "_" + filestub
            destfile = os.path.join(storedirectory,editfilename)
            if not os.path.exists(storedirectory):
                os.makedirs(storedirectory)
            if not os.path.exists(destfile):
                copy_file(origfile, destfile, display)
            open_localfile(destfile)


def view_directory(display):
    """View a directory containing relevant information to the assessment."""
    pass

def view_file(display, data):
    """View a file containing relevant information to the assessment."""
    filename = ""
    tmpname = ""
    val = data.get_current_value(display["field"])
    if type(val) is str:
        filename = os.path.expandvars(os.path.join(display["directory"],val))
        tmpname = to_camel_case(display["field"])
    elif "file" in display:
        filename = os.path.expandvars(os.path.join(display["directory"], display["file"]))
    if os.path.exists(filename):
        _, ext = os.path.splitext(filename)
        if len(tmpname)>0:
            tmpdirectory = tempfile.gettempdir()
            destfile = str(data.get_current_value(config["allocation"]["index"])) + "_" + tmpname + ext
            destname = os.path.join(tmpdirectory, destfile)
            if not os.path.exists(destname):
                log.debug(f"Copying \"{filename}\" to \"{destname}\".")
                copy2(filename, destname)
            TMPPDFFILES[destfile] = {
                "origfile": filename,
                "tmpdirectory": tmpdirectory,
            }
            open_localfile(destname)
        else:
            open_localfile(filename)
    else:
        log.warning(f"view_file \"{filename}\" does not exist.")
    
    
def view_files(data):
    """Use the system viewer to show a PDF containing relevant information to the assessment."""
    displays = []
    if "localpdf" in config:
        displays += config["localpdf"]
    if "localvideo" in config:
        displays += config["localvideo"]

    for display in displays:
        view_file(display, data)
            
                
def view_urls(data):
    """View any urls that are provided."""
    displays = []
    if "urls" in config:
        displays += config["urls"]
        
    for display in displays:
        if "url" in display:
            if "field" in display:
                val = data.get_current_value(display["field"])
            else:
                val = None
            if "field" in display and type(val) is str:
                urlterm = val
            elif "display" in display:
                urlterm = view_to_text(display, data)
            else:
                urlterm = ""
            urlname = unidecode(display["url"] + urlterm.replace(" ", "%20"))
            open_url(urlname)


def view_series(data):
    clear_temp_files()
    view_files(data)
    view_urls(data)
    edit_files(data)
    display(Markdown(view_text(data)))

def automapping():
    """Generate dictionary of mapping between variable names and column names."""
    mapping = {}
    for column in columns:
        field = to_camel_case(column)
        mapping[field] = column


def view_to_text(view, data):
    """Create the text of the view."""
    if "format" in view:
        format = data.mapping(view["format"])
    else:
        format = data.mapping()

    if data.conditions(view):
        return view["display"].format(**format)
    else:
        return ""
    
def viewer_to_text(key, data):
    """Create a formatted text output from a yaml entry with base text and format keys."""
    text = ""
    if key in config:
        for view in config[key]:
            text += view_to_text(view, data)
    return text



def view_text(data):
    """Text that views a a single record."""
    if "viewer" in config:
        return viewer_to_text("viewer", data)
    else:
        return ""

def view(data):
    """Provide a view of the data that allows the user to verify some aspect of its quality."""
    fig, ax = plt.subplots(figsize=(8, 5))
    data.hist('Score', bins=np.linspace(-.5, 12.5, 14), width=0.8, ax=ax)
    ax.set_xticks(range(0,13))


def extract_scorer(orig_score, data):
    """Interpret a scoring element from the yaml file and create the relevant widgets to be passed to the interact command"""
    global COLUMN_NAMES
    interact_args = {}
    score = json.loads(json.dumps(orig_score))

    if score["type"] == "CriterionComment":
        prefix = score["prefix"]
        criterion = score["criterion"]
        if "width" in score:
            width = score["width"]
        else:
            width = "800px"
        criterion = {
            "field": "_" + prefix + " Criterion",
            "type": "HTML",
            "args": {
                "value": criterion,
                "layout": {"width": width},
            }
        }
        comment = {
            "field": prefix + " Comment",
            "type": "Textarea",
            "args": {
                "value": "",
                "description": "Comment",
                "layout": {"width": width},
            }
        }
        for sub_score in [criterion, comment]:
            interact_args = {**interact_args, **extract_scorer(sub_score, data)}
        return interact_args
        

    if score["type"] == "CriterionCommentRaisesMeetsLowers":
        criterioncomment = json.loads(json.dumps(score))
        criterioncomment["type"] = "CriterionComment"

        prefix = score["prefix"]
        expectation = {
            "field": prefix + " Expectation",
            "type": "Dropdown",
            "args": {
                "placeholder": "Against expectations",
                "options": [
                    "",
                    "Raises",
                    "Meets",
                    "Lowers",
                    ],
                "description": "Expectation",
            }
        }
        for sub_score in [criterioncomment, expectation]:
            interact_args = {**interact_args, **extract_scorer(sub_score, data)}
        return interact_args

    if score["type"] == "CriterionCommentRaisesMeetsLowersFlag":
        criterioncomment = json.loads(json.dumps(score))
        criterioncomment["type"] = "CriterionComment"

        prefix = score["prefix"]
        expectation = {
            "field": prefix + " Expectation",
            "type": "Dropdown",
            "args": {
                "placeholder": "Against expectations",
                "options": [
                    "",
                    "Raises",
                    "Meets",
                    "Lowers",
                    "Flag",
                    ],
                "value": "",
                "description": "Expectation",
            }
        }
        for sub_score in [criterioncomment, expectation]:
            interact_args = {**interact_args, **extract_scorer(sub_score, data)}
        return interact_args
    
    if score["type"] == "CriterionCommentScore":
        criterioncomment = json.loads(json.dumps(score))
        criterioncomment["type"] = "CriterionComment"
        if "width" in score:
            width = score["width"]
        else:
            width = "800px"

        prefix = score["prefix"]
        if "min" in score:
            minval = score["min"]
        else:
            minval = 0
        if "max" in score:
            maxval = score["max"]
        else:
            maxval = 10
        if "step" in score:
            step = score["step"]
        else:
            step = 1
        if "value" in score:
            value = score["value"]
        else:
            value = int(((maxval-minval)/2)/step)*step + minval

        score = {
            "field": prefix + " Score",
            "type": "FloatSlider",
            "args": {
                "min": minval,
                "max": maxval,
                "step": step,
                "value": value,
                "description": "Score",
                "layout": {"width": width},
            }
        }
        for sub_score in [criterioncomment, score]:
            interact_args = {**interact_args, **extract_scorer(sub_score, data)}
        return interact_args
    
    global_variables = globals()
    if "field" in score:
        name = clean_string(score["field"])
        COLUMN_NAMES[name] = score["field"]

        # Create an instance of the object to extract default value.
        DEFAULT_WRITEDF_VALS[score["field"]] = global_variables[score["type"]]().value
        if "value" in score:
            DEFAULT_WRITEDF_VALS[score["field"]] = score["value"]               
        if "args" in score and "value" in score["args"]:
            DEFAULT_WRITEDF_VALS[score["field"]] = score["args"]["value"]
        if "default" in score:
            if "source" in score["default"]:
                source = score["default"]["source"]
                if source in data.columns:
                    DEFAULT_WRITEDF_SOURCE[score["field"]] = source
                else:
                    log.warning(f"Missing column \"{source}\" in _DATA and _WRITEDATA.")
            if "value" in score["default"]:
                DEFAULT_WRITEDF_VALS[score["field"]] = score["default"]["value"]
                
    else:
        # Field name is missing, generate a random one.
        name = "_" + "".join(random.choice(string.ascii_letters) for _ in range(39))
        COLUMN_NAMES[name] = name

    # Deal with HTML descriptions (setting them to blank if not set)
    if score["type"] in ["HTML", "HTMLMath"]:
        if "args" not in score:
            score["args"] = {"description": " "}
        else:
            if "description" not in score:
                score["args"]["description"] = " "

    if "source" in score:
        # Set arguments of widget from data fields if source is given
        if "args" in score["source"]:
            for arg, field in score["source"]["args"]:
                if arg not in score["args"]:
                    score["args"][arg] = data.get_current_value(field)
        if "criterion" in score["source"]:
            criterion = score["source"]["criterion"]
            if "display" in criterion:
                score["criterion"] = criterion["display"].format(**data.mapping())
                                 
    # Set arguments of widget from data fields if appropriate.                
    global_variables = globals()
    if "layout" in score:
        score["args"]["layout"] = Layout(**score["layout"])
    elif score["type"] in global_variables:
        interact_args[name] = global_variables[score["type"]](**score["args"])
    else:
        raise Exception("Have not loaded " + score["type"] + " interaction type.")
    return interact_args

def clean_string(instring):
    return re.sub("\W+|^(?=\d)","_", instring)


def _update_type(df, column, value):
    """Update the type of a given column according to a value passed."""
    coltype = df.dtypes[column]
    if is_numeric_dtype(coltype) and is_string_dtype(type(value)):
        log.info(f"Changing column \"{column}\" type to 'object' due to string input.")
        df[column] = df[column].astype('object')


        
        
def score(index=None, data=None):
    global INTERACT_ARGS

    if data is None:
        data = Data()
        
    if index is not None:
        data.set_index(index)

    INTERACT_ARGS = {}
    # Process the different scorers in from the _referia.yml file 
    if "scorer" in config:
        for score in config["scorer"]:
            INTERACT_ARGS = {**INTERACT_ARGS, **extract_scorer(score, data)}

    
    def update_df(progress_label, **kwargs):

        for key, value in kwargs.items():
            # fields starting with "_" are not transferred
            # (typically HTML widgets for prompting input)
            if key[0] != "_":
                data.set_current_value(value, COLUMN_NAMES[key])

        if "timestamp_field" in config:
            timestamp_field = config["timestamp_field"]
        else:
            timestamp_field = "Timestamp"
        data.set_current_value(
            pd.to_datetime("today"),
            timestamp_field
        )
        if "created_field" in config:
            created_field = config["created_field"]
        else:
            created_field = "Created"
        if created_field not in data._writedata.columns or empty(data.get_current_value(created_field)):
            data.set_current_value(
                pd.to_datetime("today"),
                created_field
            )
        if "combinator" in config:
            for view in config["combinator"]:
                if "field" in view:
                    data.set_current_value(
                        view_to_text(view, data),
                        view["field"]
                    )                    
                else:
                    log.error("Missing key 'field' in combinator view.")
            
        access.write_scores(data._writedata)

        


    def update_score_row(data, index):
        global INTERACT_ARGS
        global COLUMN_NAMES
        
        data.set_index(index)
        view_series(data)


        # Now update the widget entries with values from the data
        for key, widget in INTERACT_ARGS.items():
            if COLUMN_NAMES[key][0] != "_":
                if COLUMN_NAMES[key] not in DEFAULT_WRITEDF_VALS:
                    DEFAULT_WRITEDF_VALS[COLUMN_NAMES[key]] = None
                widget.value = DEFAULT_WRITEDF_VALS[COLUMN_NAMES[key]]
                # Take default from existing column 
                if COLUMN_NAMES[key] in DEFAULT_WRITEDF_SOURCE:
                    dval = data.get_current_value(DEFAULT_WRITEDF_SOURCE[COLUMN_NAMES[key]])
                    if notempty(dval):
                        widget.value = dval
                # Take default from existing column in _WRITEDATA
                if COLUMN_NAMES[key] in data.columns:
                    dval = data.get_current_value(COLUMN_NAMES[key])
                    if notempty(dval):
                        widget.value = dval
                else:
                    self.add_column(COLUMN_NAMES[key])

                    
        total = data.to_score()
        remain = total
        progress_label = fixed("None")
        if "scored" in config:
            scored = data.scored()
            remain -= scored
            perc=scored/total*100
            progress_label = Label(f"{remain} to go. Scored {scored} from {total} which is {perc:.3g}%")

        interact_args = {
            "progress_label": progress_label,
            **INTERACT_ARGS
        }

        interact_manual(
            update_df, 
            **interact_args
        )

            
    index_select=Dropdown(options=data.index, value=data.get_index())
    interact(update_score_row, index=index_select, data=fixed(data))
    

