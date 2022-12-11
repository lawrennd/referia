import os

import re

import pandas as pd
import liquid as lq

import datetime

from liquid.filter import string_filter
import urllib.parse

from pandas.api.types import is_string_dtype, is_numeric_dtype, is_bool_dtype

from .config import *
from .log import Logger
from .util import to_camel_case, remove_nan, renderable, tallyable, markdown2html, add_one_to_max
from . import access
from . import system

log = Logger(
    name=__name__,
    level=config["logging"]["level"],
    filename=config["logging"]["filename"]
)

list_functions = [
    {
        "name" : "fromisoformat",
        "function" : datetime.datetime.fromisoformat,
        "default_args" : {},
        "docstr" : "Return date in isoformat.",
    },
    {
        "name" : "strptime",
        "function" : datetime.datetime.strptime,
        "default_args" : {},
        "docstr" : "Returns date in strptime format.",
    },
    {
        "name" : "max",
        "function" : lambda x: x.max(),
        "default_args" : {},
    },
    {
        "name" : "sum",
        "function" : lambda x: x.sum(),
        "default_args" : {},
    },
    {
        "name" : "next_integer",
        "function" : add_one_to_max,
        "default_args" : {},
    },
    {
        "name" : "today",
        "function" : datetime.datetime.now().strftime,
        "default_args": {
            "format": "%Y-%m-%d",
        },
        "docstr" : "Return today's date as a string.",
    },
]



@string_filter
def url_escape(string):
    """Filter to escape urls for liquid"""
    return urllib.parse.quote(string.encode('utf8'))


@string_filter
def markdownify(string):
    """Filter to convert markdown to html for liquid"""
    return markdown2html(string.encode("utf8"))

def empty(val):
    return pd.isna(val) or val==""

def automapping(columns):
    """Generate dictionary of mapping between variable names and column names."""
    mapping = {}
    for column in columns:
        field = to_camel_case(column)
        mapping[field] = column
    return mapping

class Data:
    def __init__(self):
        # Data that is input (not for writing to)
        self._data = None
        # Which index is the current focus in the data.
        self._index = None
        # Data for writing outputs to.
        self._writedata = None
        # Which column is the current focus in the data.
        self._column = None
        # Which subindex is the current focus in the data.
        self._subindex = None
        # The series data for writing to (where there may be multiple entries associated with one index)
        self._writeseries = None
        # Which entry column in the series to disambiguate the selection of the focus.
        self._selector = None
        # The value in the selected entry column entry column value from the series to use

        self._computes=[]
        if "compute" in config:
            if type(config["compute"]) is list:
                computes = config["compute"]
            else:
                computes = [config["compute"]]

            for compute in computes:
                self._computes.append({
                    "function": self.gcf_(function=compute["function"]),
                    "args" : self.gca_(**compute),
                    "field" : compute["field"],
                    "refresh" : "refresh" in compute and compute["refresh"],
                })

        self.load_liquid()
        self.add_liquid_filters()
        self.load_flows()


    def gca_(self, field, function, args={}, subseries_args={}, column_args={}):
        """Args generator for compute functions."""

        found_function = False
        for list_function in list_functions:
            if list_function["name"] == function:
                found_function = True
                continue
        if not found_function:
            raise ValueError("Function \"{function}\" not found in list_functions.")
        return {
            "subseries_args" : subseries_args,
            "column_args" : column_args,
            "args" : args,
            "default_args" : {},# list_function["default_args"],
        }


    def gcf_(self, function):
        """Function generator for compute functions."""

        found_function = False
        for list_function in list_functions:
            if list_function["name"] == function:
                found_function = True
                break
        if not found_function:
            raise ValueError("Function \"{function}\" not found in list_functions.")

        def compute_function(args={}, subseries_args={}, column_args={}, default_args={}):

            kwargs = default_args.copy()
            kwargs.update(args)
            for key, value in column_args.items():
                self.set_column(value)
                kwargs[key] = self.get_column_values()
            for key, value in subseries_args.items():
                self.set_column(value)
                kwargs[key] = self.get_subseries_values()
            # kwargs.update(remove_nan(self.mapping(args)))

            return list_function["function"](**kwargs)

        compute_function.__name__ = list_function["name"]
        if "docstr" in list_function:
            compute_function.__docstr__ = list_function["docstr"]
        return compute_function


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
            columns += list(self._writedata.columns)
        if self._writeseries is not None:
            columns += list(self._writeseries.columns)
        # Should perhaps make this unique column list? As in practice it behaves that way.
        return pd.Index(columns)

    def _allocation(self):
        """Load in the allocation spread sheet to data frames."""
        df = access.allocation()
        df = self._finalize_df(df, config["allocation"])
        if df.index.is_unique:
            self._data = df
        else:
            strindex = pd.Series([str(ind) for ind in df.index])
            duplicates = ', '.join(strindex[df.index.duplicated()])
            raise ValueError(f"The index for the allocation must be unique. Index \"{duplicates}\" is/are duplicated.")

    def _additional(self):
        """Load in the allocation spread sheet to data frames."""

        if type(config["additional"]) is not list:
            configs = [config["additional"]]
        else:
            configs = config["additional"]

        for i, conf in enumerate(configs):
            df = self._finalize_df(access.additional(conf), conf)
            if df.index.is_unique:
                if i == 0:
                    additional = df
                else:
                    additional = additional.join(df, rsuffix="_" + str(i))
            else:
                strindex = pd.Series([str(ind) for ind in df.index])
                duplicates = ', '.join(strindex[df.index.duplicated()])
                raise ValueError(f"The index for additional data frame {i} must be unique. Index \"{duplicates}\" is/are duplicated.")

        self._data = self._data.join(additional, rsuffix="additional")

    def _scores(self):
        """Load in the score data to data frames."""
        df = access.scores(self.index)
        df = self._finalize_df(df, config["scores"])
        if df.index.is_unique:
            self._writedata = df
        else:
            strindex = pd.Series([str(ind) for ind in df.index])
            duplicates = ', '.join(strindex[df.index.duplicated()])
            raise ValueError(f"The index for writedata must be unique. Index \"{duplicates}\" is/are duplicated.")


    def _series(self):
        """Load in the series data to data frames."""
        series = config["series"]
        if "selector" in series:
            self.set_selector(series["selector"])
        else:
            raise ValueError(f"The series in _referia.yml does not specify a selector.")
        self._writeseries = access.series(self.index)
        self._writeseries = self._finalize_df(self._writeseries,
                                              config['series'])
        self.sort_series()

    def sort_series(self):
        """Sort the series by the column specified."""
        if "series" in config:
            series = config["series"]
        else:
            return
        if "sortby" in series and "field" in series["sortby"] and series["sortby"]["field"] in self._writeseries:
            if "ascending" in series["sortby"]:
                ascending = series["sortby"]["ascending"]
            else:
                ascending=True
            field=series["sortby"]["field"]
            log.info(f"Sorting series by \"{field}\"")
            self._writeseries.sort_values(by=field, ascending=ascending, inplace=True)

    def load_input_flows(self):
        """Load the input flows specified in the _referia.yml file."""
        self._allocation()
        if "additional" in config:
            log.info("Joining allocation and additional information.")
            self._additional()

        # If sorting is requested do it here.
        self.sort_data()

    def sort_data(self):
        if "sortby" in config and "field" in config["sortby"] and config["sortby"]["field"] in self._data:
            if "ascending" in config["sortby"]:
                ascending = config["sortby"]["ascending"]
            else:
                ascending=True
            field=config["sortby"]["field"]
            log.info(f"Sorting by \"{field}\"")
            self._data.sort_values(by=field, ascending=ascending, inplace=True)

    def load_output_flows(self):
        """Load the output flows data specified in the _referia.yml file."""
        if "scores" in config:
            self._scores()
        if "series" in config:
            self._series()

    def load_flows(self):
        self._data = None
        self._writedata = None
        self._writeseries = None
        self.load_input_flows()
        self.load_output_flows()

    def load_liquid(self):
        """Load the liquid environment."""
        loader = None
        if "liquid" in config:
            if "templates" in config["liquid"]:
                if "dir" in config["liquid"]["templates"]:
                    templates_path = [os.path.abspath(config["liquid"]["templates"])]
                else:
                    template_path = [
                        os.path.join(os.path.dirname(__file__), "templates"),
                    ]

                    if "ext" in config["liquid"]:
                        ext = config["liquid"]["ext"]
                        loader = lq.loaders.FileExtensionLoader(search_path=template_path, ext=ext)
                    else:
                        loader = lq.FileSystemLoader(template_path)
            elif "dict" in config["liquid"]["templates"]:
                loader = lq.loaders.DictLoader(config["liquid"]["templates"]["dict"])
        self._liquid_env = lq.Environment(loader=loader)


    def add_liquid_filters(self):
        self._liquid_env.add_filter("url_escape", url_escape)
        self._liquid_env.add_filter("markdownify", markdownify)

    def set_index(self, index):
        """Index setter"""
        orig_index = self._index
        if self._data is not None and index not in self.index:
            self.add_row(index=index)
            self.set_index(index)
        else:
            self._index = index
            log.info(f"Index \"{index}\" selected.")
            self.check_or_set_subseries()
        # If index has changed, run computes.
        if self._index != orig_index:
            self.run_compute()

    def check_or_set_subseries(self):
        """Check if there is a sub-series if so, use top subindex, if not create a row."""
        if self._writeseries is not None:
            subindices = self.get_subseries()
            if len(subindices) > 0:
                if self.get_subindex() is None:
                    self.set_subindex(subindices[0])
            else:
                self.add_series_row(self._index)

    def run_compute(self, series=None):
        """Interpret a computation element form the yaml file and return the relevant answer."""
        for compute in self._computes:

            # Run compute
            if series is None:
                for compute in self._computes:
                    self.set_column(compute["field"])
                    val = self.get_value()
                    if pd.isna(val) or compute["refresh"]:
                        self.set_value(compute["function"](**compute["args"]))
            else:
                if compute["field"] in series.index:
                    if pd.isna(series[compute["field"]]) or compute["refresh"]:
                        series[compute["field"]] = compute["function"](**compute["args"])


    def set_subindex(self, subindex):
        """Subindex setter"""
        if subindex is None:
            self._subindex = None
            log.info(f"Subindex set to None.")
            return

        if self._writeseries is not None and subindex not in self.get_subindices():
            index = self.get_index()
            raise ValueError(f"Subindex \"{subindex}\" under \"{index}\" not available in current series.")
        else:
            self._subindex=subindex
            log.info(f"Subindex \"{subindex}\" selected.")


    def get_index(self):
        if self._index is None and self._data is not None:
            log.info(f"No index set, using first index of data.")
            self.set_index(self._data.index[0])
        return self._index

    def set_column(self, column):
        """Set the current column focus."""
        if column not in self.columns and (self.index is not None and column != self.index.name) or self.index is None:
            # If column isn't present add it
            if self._writeseries is not None:
                self.add_series_column(column)
            elif self._writedata is not None:
                self.add_column(column)

        if column not in self.columns and (self.index is not None and column != self.index.name) or self.index is None:
            self._column = None
        else:
            self._column = column

    def get_column(self):
        """Get the current column focus."""
        return self._column

    def get_selector(self):
        return self._selector

    def get_selectors(self):
        if self._writeseries is None:
            return None
        else:
            return self._writeseries.columns

    def set_selector(self, column):
        """Set which column of the series is to be used for selection."""
        # Set to None to indicate that self._writedata is correct place for recording.
        if column is None:
            log.warning(f"No column selected for selector, setting to \"None\".")
            self._selector = None
            return

        if column not in self.get_selectors():
            log.info(f"Column {column} of chosen for selection not in Data._writeseries ... adding.")
            self.add_column(column)
            self.set_selector(column)
        else:
            self._selector = column
            log.info(f"Column {column} of Data._writeseries selected for selection.")
            if self.get_subindex() not in self._writeseries[column]:
                self.set_subindex(None)


    def get_subindex(self):
        if self._subindex is None and self._writeseries is not None and self._selector is not None:
            self.reset_subindex()
        return self._subindex

    def reset_subindex(self):
        subindices = self.get_subindices()
        if len(subindices)>0:
            index = self.get_index()
            log.info(f"No subindex set, using first entry of portion of Data._writeseries indexed by \"{index}\".")
            self.set_subindex(subindices[0])
        else:
            log.info(f"No subindex available.")
            self.add_series_row()



    def generate_subindex(self):
        """Generate a new subindex for use."""
        # Store state
        ind = self.get_index()
        selector = self.get_selector()
        col = self.get_column()
        # Generate subindex
        self._subindex_generator()
        # Restore state
        self.set_index(ind)
        self.set_selector(selector)
        self.set_column(col)

    def get_subseries(self):
        return self._writeseries[self._writeseries.index.isin([self.get_index()])]

    def get_subindices(self):
        if self._selector is None:
            return []
        try:
            return pd.Index(self.get_subseries()[self._selector].values, name=self._selector)
        except KeyError as err:
            raise KeyError(f"Could not find index \"{err}\" in the subseries when using it as a selector.")

    def set_series_value(self, value, column):
        """Set a value in the write series data frame"""
        if column in self._data.columns:
            log.warning(f"Warning attempting to write to {column} in self._data.")

        if column not in self._writeseries.columns:
            self.add_series_column(column)

        self._update_type(self._writeseries, column, value)
        self.get_subseries().at[get]

    def set_value_column(self, value, column):
        """Set a value to the write data frame"""
        self.set_column(column)
        self.set_value(value)

    def get_value_column(self, column):
        """Get a value from the data frame(s)"""
        self.set_column(column)
        return self.get_value()

    def set_value(self, value):
        """Set the value of the current cell under focus."""
        column = self.get_column()
        if column is None:
            raise KeyError(f"Warning attempting to write a value {value} when column is not set.")
        index = self.get_index()
        selector = self.get_selector()
        subindex = self.get_subindex()
        # If trying to set a numeric valued column's entry to a string, set the type of column to object.
        if column in self._data.columns:
            log.warning(f"Warning attempting to write to {column} in self._data.")

        if self._writedata is not None and column in self._writedata.columns:
            self._update_type(self._writedata, column, value)
            self._writedata.at[index, column] = value
        elif self._writeseries is None or selector is None:
            self.add_column(column)
            self.set_column(column)
            self.set_value(value)
        elif column in self._writeseries.columns:

            self._update_type(self._writeseries, column, value)
            self._writeseries.loc[
                self._writeseries.index.isin([index])
                & (self._writeseries[selector]==subindex).values,
                column
            ] = value
        else:
            self.add_series_column(column)
            self.set_series_value(value, column)

    def get_column_values(self):
        """Return a pd.Series containing all the values in a column."""
        column = self.get_column()
        if column == None:
            return None
        selector = self.get_selector()
        subindex = self.get_subindex()
        # Prioritise returning from the _data structure first.
        if self._data is not None and column in self._data.columns:
            try:
                return self._data[column]
            except KeyError as err:
                raise KeyError(f"Cannot find column: \"{column}\" in _data.") from err
        elif self._data is not None and column==self._data.index.name:
            return self._data.index
        elif self._writeseries is not None and column in self._writeseries.columns:
            try:
                return self._writeseries[column]
            except KeyError as err:
                raise KeyError(f"Cannot find column: \"{column}\" in _writeseries.") from err

        elif self._writedata is not None and column in self._writedata.columns:
            try:
                return self._writedata[column]
            except KeyError as err:
                raise KeyError(f"Cannot find column: \"{column}\" in _writedata.") from err
        else:
            log.warning(f"\"{column}\" not selected in self._writeseries or in self._writedata or in self._data returning \"None\"")
            return None

    def get_subseries_values(self):
        """Return a pd.Series containing all the values in a column."""
        column = self.get_column()
        if column == None:
            return None
        index = self.get_index()
        # Prioritise returning from the _data structure first.
        if self._writeseries is not None and column in self._writeseries.columns:
            indexer = self._writeseries.index.isin([index])
            if indexer.sum()>0:
                return self._writeseries.loc[indexer, column]
            else:
                log.warning(f"No data available with this index returning None.")
                return None
        else:
            log.warning(f"\"{column}\" not selected in self._writeseries or in self._writedata or in self._data returning \"None\"")
            return None

    def get_value(self):
        """Return the value of the current cell under focus."""
        # Ordering here dictates the priority of selection, first series, then writedata, then data.
        column = self.get_column()
        if column == None:
            return None
        index = self.get_index()
        if index == None:
            return None
        selector = self.get_selector()
        subindex = self.get_subindex()
        # Prioritise returning from the _data structure first.
        if self._data is not None and column in self._data.columns:
            try:
                return self._data.at[index, column]
            except KeyError as err:
                raise KeyError(f"Cannot find index: \"{index}\" and column: \"{column}\" in _data.") from err
        elif self._data is not None and column==self._data.index.name:
            return index
        elif self._selector is not None and self._writeseries is not None and column in self._writeseries.columns:
            if subindex is not None:
                indexer = (self._writeseries.index.isin([index])
                           & (self._writeseries[selector]==subindex).values)
                if indexer.sum()>0:
                    return self._writeseries.loc[indexer, column].iloc[0]
                else:
                    log.warning(f"No data available with this subindex and index , returning None.")
            else:
                log.warning(f"No subindex selected, returning None.")
        elif self._writedata is not None and column in self._writedata.columns:
            if index in self._data.index and not index in self._writedata.index:
                # If index isn't created in write data yet, return None.
                return None
            try:
                return self._writedata.at[index, column]
            except KeyError as err:
                raise KeyError(f"Cannot find index: \"{index}\" and column: \"{column}\" in _writedata.") from err
        else:
            log.warning(f"\"{column}\" not selected in self._writeseries or in self._writedata or in self._data returning \"None\"")
            return None

    def add_column(self, column):
        if self._writedata is None:
            raise ValueError("There is no _writedata loaded to add a column to.")
        if column not in self._writedata.columns:
            log.info(f"\"{column}\" not in write columns ... adding.")
            self._writedata[column] = None
        else:
            log.warning(f"\"{column}\" requested to be added to write data but already exists.")

    def set_dtype(self, column, dtype):
        """Set a Data._writedata column to the given data type."""
        if self._writedata is not None and column in self._writedata.columns:
            log.info(f"\"{column}\" being set to \"{dtype}\".")
            self._writedata[column] = self._writedata[column].astype(dtype)
        if self._writeseries is not None and column in self._writeseries.columns:
            log.info(f"\"{column}\" being set to \"{dtype}\".")
            self._writeseries[column] = self._writeseries[column].astype(dtype)


    def add_row(self, index=None, subindex=None):
        """Add a row with a given index (and optionally subindex) to the data structure."""
        def append_row(df, index):
            """Add an empty row with a given index to a data frame."""
            row = pd.Series(index=df.columns, dtype=object)
            row.name = index
            # Handle the fact that the index is stored as a column also
            if df.index.name in row:
                row[df.index.name] = index
            self.run_compute(row)
            return df.append(row)

        if index is None:
            index = self.get_index()

        selector = self.get_selector()
        if self._data is not None and index not in self.index:
            self._data = append_row(self._data, index)
            log.info(f"\"{index}\" added as row in Data._data.")
            self.set_index(index)

        if self._writedata is not None and index not in self._writedata.index:
            self._writedata = append_row(self._writedata, index)
            log.info(f"\"{index}\" added as row in Data._writedata.")
            self.set_index(index)

        if self._writeseries is not None and index not in self._writeseries.index:
            self._writeseries = append_row(self._writeseries, index)
            log.info(f"\"{index}\" added as row in Data._writeseries.")
            self.set_index(index)

    def add_series_row(self, index=None):
        """Add a row to the series."""

        def append_row(df, index):
            row = pd.Series(index=df.columns, dtype=object)
            row.name = index
            # Handle the fact that the index is stored as a column also
            if df.index.name in row:
                row[df.index.name] = index
            self.run_compute(row)
            return df.append(row)

        if index is None:
            index = self.get_index()
        self._writeseries = append_row(self._writeseries, index)
        selector = self.get_selector()
        log.info(f"\"{index}\" added subseries row in Data._writeseries.")


    def add_series_column(self, column):
        """Add a column to the data series"""
        if column not in self._writeseries.columns:
            log.info(f"\"{column}\" not in series columns ... adding.")
            self._writeseries[column] = None
        else:
            log.warning(f"\"{column}\" requested to be added to series data but already exists.")

    def _default_mapping(self):
        """Generate the default mapping from config or from columns"""
        # If a mapping is provided in _referia.yml use it, otherwise generate
        if "mapping" in config:
            mapping = config["mapping"]
        else:
            mapping = automapping(self.columns)
        if "entries" not in mapping:
            mapping["entries"] = "entries" # Covers series entries.
        return mapping

    def mapping(self, mapping=None, series=None):
        """Generate dictionary of mapping between variable names and column values."""
        if mapping is None:
            mapping = self._default_mapping()

        format = {}
        for key, column in mapping.items():
            if series is not None and column in series:
                format[key] = series[column]
            else:
                self.set_column(column)
                format[key] = self.get_value()

        return format


    def viewer_to_value(self, viewer, kwargs=None):
        """Convert a viewer structure to populated values."""
        value = ""
        if type(viewer) is not list:
            viewer = [viewer]
        for view in viewer:
            value += self.view_to_value(view, kwargs)
            if value != "":
                value += "\n\n"
        return value

    def view_to_value(self, view, kwargs=None):
        """Create the text of the view."""
        value = ""

        if self.conditions(view):
            if type(view) is dict:
                if "list" in view:
                    values = []
                    for v in view["list"]:
                        values.append(self.view_to_value(v, kwargs))
                    return values
                if "join" in view:
                    if "list" not in view["join"]:
                        log.warning("No field \"list\" in \"concat\" viewer.")
                    elements = self.view_to_value(view["join"], kwargs)
                    if "separator" in view["join"]:
                        sep = view["join"]["separator"]
                    else:
                        sep = "\n\n"
                    return sep.join(elements)
                if "liquid" in view:
                    value += self.liquid_to_value(view["liquid"], kwargs)
                if "tally" in view:
                    value += self.tally_to_value(view["tally"], kwargs)
                if "display" in view:
                    value += self.display_to_value(view["display"], kwargs)
                return value
            else:
                raise TypeError("View should be a \"dict\".")
        else:
            return None

    def view_to_tmpname(self, view):
        """Convert a view to a temporary name"""
        if "list" in view:
            name = "list_"
            for v in view["list"]:
                name += self.view_to_tmpname(v)
                name += "_"
            return name
        elif "join" in view:
            name = "join_"
            if "list" not in view["join"]:
                log.warning("No field \"list\" in \"concat\" viewer.")
            name += self.view_to_tmpname(view["join"])
            return name
        elif "liquid" in view:
            name = self.liquid_to_tmpname(view["liquid"])
            return name
        elif "display" in view:
            name = self.display_to_tmpname(view["display"])
            return name

    def tally_to_value(self, tally, kwargs=None):
        """Create the text of the view."""
        return self.tally_values(tally, kwargs)

    def tally_to_tmpname(self, tally):
        """Convert a view to a temporary name"""
        if "tally" in view:
            name = self.tally_to_tmpname(view["tally"])
        return name

    def conditions(self, view):
        """Check if the viewer should be displayed."""
        if "conditions" not in view:
            return True
        else:
            for condition in view["conditions"]:
                if "present" in condition:
                    if not condition["present"]["field"] in self.columns:
                        return False
                    else:
                        self.set_column(condition["present"]["field"])
                        if pd.isna(self.get_value()):
                            return False
                        else:
                            return True

                if "equal" in condition:
                    self._parent.set_column(condition["equal"]["field"])
                    if not self._parent.get_value() == condition["equal"]["value"]:
                        return False
        return True

    def display_to_tmpname(self, display):
        """Convert a display string to a temp name"""
        return to_camel_case(display.replace("/", "_").replace("{","").replace("}", ""))


    def display_to_value(self, display, kwargs=None):
        if kwargs is None:
            kwargs = self.mapping()
        try:
            return display.format(**kwargs)
        except KeyError as err:
            raise KeyError(f"The mapping doesn't contain the key {err} requested in \"{display}\". Set the mapping in \"_referia.yml\".") from err

    def liquid_to_tmpname(self, display):
        """Convert a display string to a temp name"""
        return to_camel_case(display.replace("/", "_").replace("{","").replace("}", "").replace("%","-"))

    def liquid_to_value(self, display, kwargs=None):
        if kwargs is None:
            kwargs = self.mapping()
        try:
            return self._liquid_env.from_string(display).render(**remove_nan(kwargs))
        except Exception as err:
            raise Exception(f"In {display}\n\n {err}") from err

    def tally_to_tmpname(self, tally):
        """Convert a tally to a temporary name"""
        tmpname = ""
        if "begin" in tally:
            tmpname += "begin_"
            tmpname += self.view_to_tmpname(tally["begin"])
        tmpname += "display_"
        tmpname += self.view_to_tmpname(tally)
        if "end" in tally:
            tmpname += "end_"
            tmpname += self.view_to_tmpname(tally["end"])
        return tmpname

    def tally_values(self, tally, kwargs=None):
        value = ""
        if "begin" in tally:
            value += tally["begin"]
            if value != "":
                value += "\n\n"
        orig_subindex = self.get_subindex()
        subindices = self.tally_series(tally)
        # Reverse series so it's most distant event first.
        for subindex in subindices[::-1]:
            self.set_subindex(subindex)
            value += self.view_to_value(tally, kwargs)
            if value != "":
                value += "\n\n"
        self.set_subindex(orig_subindex)
        if "end" in tally:
            value += tally["end"]
            if value != "":
                value += "\n\n"
        return value

    def tally_series(self, tally):
        orig_subindex = self.get_subindex()
        subindices = self.get_subindices()
        if subindices is None:
            return None
        if orig_subindex in subindices:
            cur_loc = subindices.get_loc(orig_subindex)
        else:
            cur_loc = 0
            orig_subindex = subindices[0]
        def subind_val(ind):
            try:
                return pd.Index([subindices[ind]])
            except IndexError as e:
                log.info(f"Requested invalid index in Data.tally_series()")
                return pd.Index([subindices[cur_loc]])

        def subind_series(ind, starter=True):
            try:
                if starter:
                    return pd.Index(subindices[ind:])
                else:
                    return pd.Index(subindices[:ind])

            except IndexError as e:
                log.info(f"Requested invalid index in Data.tally_series()")
                if starter:
                    return pd.Index(subindices[cur_loc:])
                else:
                    return pd.Index(subindices[:cur_loc])

        if "which" not in tally:
            return subindices
        elif tally["which"] == "pop":
            return subind_val(0)
        elif tally["which"] == "bottom":
            return subind_val(-1)
        elif tally["which"] == "previous":
            return subind_val(cur_loc+1)
        elif tally["which"] == "next":
            return subind_val(cur_loc-1)
        elif tally["which"] == "earlier":
            return subind_series(cur_loc+1)
        elif tally["which"] == "later":
            return subind_series(cur_loc, starter=False)
        elif tally["which"] == "others":
            return subind_series(cur_loc, starter=False).append(subind_series(cur_loc+1))
        elif tally["which"] == "all":
            return subindices
        else:
            raise ValueError("Unrecognised subindices specifier in tally.")


    def _finalize_df(self, df, details):
        """This function augments the raw data and sets the index of the data frame."""
        """for field in dtypes:
            if dtypes[field] is str_type:
                data[field].fillna("", inplace=True)"""

        if "series" in details and details["series"]:
            """The data frame is a series (with multiple identical indices)"""
            mapping = self._default_mapping()
            indexcol = list(set(df[details["index"]]))
            index = pd.Index(range(len(indexcol)))
            newdf = pd.DataFrame(index=index, columns=[details["index"], "entries"])
            newdf[details["index"]] = indexcol
            newdetails = details.copy()
            del newdetails["series"]
            for ind in range(len(indexcol)):
                entries = []
                for ind2 in df.index[df[details["index"]]==indexcol[ind]]:
                    entry = remove_nan(df.loc[ind2].to_dict())
                    map_entry = entry.copy()
                    del map_entry[details["index"]]
                    for key, key2 in mapping.items():
                        if key2 in entry:
                            map_entry[key] = entry[key2]
                            del map_entry[key2]
                    entries.append(map_entry)
                newdf.at[ind, "entries"] = entries
                newdf.at[ind, details["index"]] = indexcol[ind]
            return self._finalize_df(newdf, newdetails)


        if "fields" in details:
            for field in details["fields"]:
                column = pd.Series(index=df.index, dtype="object")
                if "name" in field:
                    if renderable(field):
                        for index in df.index:
                            if len(self.columns)>0:
                                # If there are existing columns, make sure index is set.
                                self.set_index(df.at[index, details["index"]])
                            kwargs = self.mapping(series=df.loc[index])
                            column[index] = self.view_to_value(field, kwargs)

                    elif "source" in field and "regexp" in field:
                        regexp = field["regexp"]
                        if field["source"] not in df.columns:
                            log.warning("No column \"{source}\" in DataFrame.".format(source=field["source"]))
                        for index in df.index:
                            try:
                                source = df.at[index, field["source"]]
                            except KeyError as err:
                                name = field["name"]
                                raise KeyError(f"Could not find the source field, \"{err}\", listed in _referia.yml under name: \"{name}\" in the DataFrame.")
                            match = re.match(
                                regexp,
                                source,
                            )
                            if match:
                                if len(match.groups())>1:
                                    log.warning(f"Multiple regular expression matches in \"{regexp}\".")
                                column[index] = match.group(1)
                            else:
                                log.warning(f"No match of regular expression \"{regexp}\" to \"{source}\".")
                    elif "value" in field:
                        for index in df.index:
                            column[index] = field["value"]
                    else:
                        log.warning(f"Missing \"source\" or \"regexp\" (for regular expression derived fields) or \"value\" (for format derived fields) in fields.")
                    df[field["name"]] = column
                else:
                    log.warning(f"No \"name\" associated with field entry.")
        if "index" not in details:
            raise ValueError("Missing index field in data frame specification in _referia.yml")
        index_col = details["index"]
        if index_col in df.columns:
            df.set_index(df[index_col], inplace=True)
            del df[index_col]
        else:
            log.warning(f"No index column \"{index_col}\" found in data frame.")

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


    def _update_type(self, df, column, value):
        """Update the type of a given column according to a value passed."""
        coltype = df.dtypes[column]
        if is_numeric_dtype(coltype) and is_string_dtype(type(value)):
            log.info(f"Changing column \"{column}\" type to 'object' due to string input.")
            df[column] = df[column].astype("object")
        if is_numeric_dtype(coltype) and is_bool_dtype(type(value)):
            log.info(f"Changing column \"{column}\" type to 'object' due to bool input.")
            df[column] = df[column].astype("boolean")
