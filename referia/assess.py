import os

import re

import pandas as pd

from pandas.api.types import is_string_dtype, is_numeric_dtype, is_bool_dtype

from .config import *
from .log import Logger
from .util import to_camel_case
from . import access

log = Logger(
    name=__name__,
    level=config["logging"]["level"],
    filename=config["logging"]["filename"]
)



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
        # The series data for writing to (where there may be multiple entries associated with one index)
        self._writeseries = None
        # Which entry column in the series to disambiguate the selection of the focus.
        self._selector = None
        # The value in the selected entry column entry column value from the series to use
        self._subindex = None
        self.load_flows()

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
        series = config["series"]
        if "selector" in series:
            self._selector = series["selector"]
        self._writeseries = access.series(self.index)
        self._writeseries = self._finalize_df(self._writeseries, config['series'])
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
        
    def set_index(self, index):
        """Index setter"""
        if self._data is not None and index not in self.index:
            self.add_row(index=index)
            self.set_index(index)
        else:
            self._index = index
            self._subindex = None
            log.info(f"Index {index} selected.")

    def set_subindex(self, subindex):
        """Subindex setter"""
        if subindex is None:
            self._subindex = None
            log.info(f"Subindex set to None.")
            return

        if self._writeseries is not None and subindex not in self.get_subindices():
            self.add_row(subindex=subindex)
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
        if column != self.index.name and column not in self.columns:
            if self._writedata is not None or self._writeseries is not None:
                self.add_column(column)

        if column != self.index.name and column not in self.columns:
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
            self._selector = None
            return

        if column not in self.get_selectors():
            self.add_column(column)
            self.set_selector(column)
        else:
            self._selector = column
            if self.get_subindex() not in self._writeseries[column]:
                self.set_subindex(None)
            log.info(f"Column {column} of Data._writeseries selected for selection.")

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
            self.add_new_row_to_series()

    def add_new_row_to_series(self):
        """Add a row with a generated subindex to the series."""
        subindex = self.generate_subindex()
        log.info(f"Generated new subindex \"{subindex}\".")
        self.add_row(index=self.get_index(), subindex=subindex)

    
    def generate_subindex(self):
        """Generate a new subindex for use."""
        if "subindex_generator" in config["series"]:
            generator = config["series"]["subindex_generator"]
        else:
            generator = "today"

        if generator == "today":
            return pd.to_datetime(pd.to_datetime("today").strftime('%Y-%m-%d'))
        elif generator == "hour":
            return pd.to_datetime(pd.to_datetime("today").strftime('%Y-%m-%d %H:00'))

    def get_subseries(self):
        return self._writeseries[self._writeseries.index.isin([self.get_index()])]

    def get_subindices(self):
        if self._selector is None:
            return []
        return pd.Index(self.get_subseries()[self._selector].values, name=self._selector)

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
        index = self.get_index()
        selector = self.get_selector()
        subindex = self.get_subindex()
        # If trying to set a numeric valued column's entry to a string, set the type of column to object.      
        if column in self._data.columns:
            log.warning(f"Warning attempting to write to {column} in self._data.")

        if selector is not None:
            if column not in self._writeseries.columns:
                self.add_series_column(column)
            self._update_type(self._writeseries, column, value)
            self._writeseries.loc[
                self._writeseries.index.isin([index])
                & (self._writeseries[selector]==subindex).values,
                column
            ] = value
        else:
            if column not in self._writedata.columns:
                self.add_column(column)

            self._update_type(self._writedata, column, value)
            self._writedata.at[index, column] = value


    def get_value(self):
        """Return the value of the current cell under focus."""
        # Ordering here dictates the priority of selection, first series, then writedata, then data.
        column = self.get_column()
        index = self.get_index()
        if index == None or column == None:
            return None
        selector = self.get_selector()
        subindex = self.get_subindex()
        if self._selector is not None and self._writeseries is not None and column in self._writeseries.columns:
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
            return self._writedata.at[index, column]
        elif self._data is not None and column in self._data.columns:
            return self._data.at[index, column]
        elif self._data is not None and column==self._data.index.name:
            return index
        else:
            log.warning(f"\"{column}\" not selected in self._writeseries or in self._writedata or in self._data returning \"None\"")
            return None

    def add_column(self, column):
        if column not in self._writedata.columns:
            log.info(f"\"{column}\" not in write columns ... adding.")
            self._writedata[column] = None
        else:
            log.warning(f"\"{column}\" requested to be added to write data but already exists.")

    def add_row(self, index=None, subindex=None):
        """Add a row with a given index (and optionally subindex) to the data structure."""
        def append_row(df, index, subindex=None, selector=None):
            """Add an empty row with a given index to a data frame."""
            row = pd.Series(index=df.columns)
            row.name = index
            if selector is not None and subindex is not None:
                row[selector] = subindex
            # Handle the fact that the index is stored as a column also
            if df.index.name in row:
                row[df.index.name] = index
            return df.append(row)            
        if index is None:
            index = self.get_index()
        if subindex is None and self._writeseries is not None:
            subindex = self.get_subindex()

        selector = self.get_selector()
        if self._data is not None and index not in self.index:
            self._data = append_row(self._data, index)
            self.set_index(index)
            log.info(f"\"{index}\" added as row in Data._data.")

        if self._writedata is not None and index not in self._writedata.index:
            log.info(f"\"{index}\" added as row in Data._writedata.")
            self._writedata = append_row(self._writedata, index)
            self.set_index(index)

        if self._writeseries is not None and subindex not in self.get_subindices():
            self._writeseries = append_row(self._writeseries, index, subindex, selector)
            log.info(f"\"{index}\" with subindex \"{subindex}\" added as row in Data._writeseries.")
            self.set_index(index)
            self.set_subindex(subindex)
            self.sort_series()
            
    def add_series_column(self, column):
        """Add a column to the data series"""
        if column not in self._writeseries.columns:
            log.info(f"\"{column}\" not in series columns ... adding.")
            self._writeseries[column] = None
        else:
            log.warning(f"\"{column}\" requested to be added to series data but already exists.")

    def mapping(self, mapping=None, series=None):
        """Generate dictionary of mapping between variable names and column values."""
        if mapping is None:
            if "mapping" in config:
                mapping = config["mapping"]
            else:
                mapping = automapping(self.columns)

        format = {}
        for key, column in mapping.items():
            if series is None:
                self.set_column(column)
                format[key] = self.get_value()
            else:
                if column in series:
                    format[key] = series[column]
                else:
                    log.info(f"No column \"{column}\" found in series.")
                    format[key] = None

        return format

        
    def viewer_to_value(self, viewer):
        """Convert a viewer structure to populated values."""
        value = ""
        if type(viewer) is not list:
            viewer = [viewer]
        for view in viewer:
            value += self.view_to_value(view)
            if value != "":
                value += "\n\n"
        return value

    def view_to_value(self, view):
        """Create the text of the view."""
        value = ""
        if self.conditions(view):
            if "display" in view:
                value += self.display_to_value(view["display"])
            if "tally" in view:
                value += self.tally_to_value(view["tally"])
            return value
        else:
            return ""

    def conditions(self, view):
        """Check if the viewer should be displayed."""
        if "conditions" not in view:
            return True
        else:
            for condition in view["conditions"]:
                if "present" in condition:
                    if not condition["present"]["field"] in self._parent._parent.columns():
                        return False

                if "equal" in condition:
                    self._parent.set_column(condition["equal"]["field"])
                    if not self._parent.get_value() == condition["equal"]["value"]:
                        return False
        return True

    def display_to_value(self, display):
        format = self.mapping()
        return display.format(**format)    

    def tally_to_value(self, tally):
        format = self.mapping()
        orig_subindex = self.get_subindex()
        value = ""
        if "begin" in tally:
            value += self.display_to_value(tally["begin"])
            if value != "":
                value += "\n\n"
        subindices = self.tally_series(tally)
        # Reverse series so it's most distant event first.
        for subindex in subindices[::-1]:
            self.set_subindex(subindex)
            value += self.display_to_value(tally["display"])
            if value != "":
                value += "\n\n"
        self.set_subindex(orig_subindex)
        if "end" in tally:
            value += self.display_to_value(tally["end"])
            if value != "":
                value += "\n\n"
        return value    

    def tally_series(self, tally):
        orig_subindex = self.get_subindex()
        subindices = self.get_subindices()
        cur_loc = subindices.get_loc(orig_subindex)
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
        """for field in dtypes:
            if dtypes[field] is str_type:
                data[field].fillna("", inplace=True)"""

        if "fields" in details:
            for field in details["fields"]:
                column = pd.Series(index=df.index, dtype="object")
                if "name" in field:
                    if "value" in field:
                        for index in df.index:
                            format = self.mapping(series=df.loc[index])
                            column[index] = field["value"].format(**format)

                    elif "source" in field and "regexp" in field:
                        regexp = field["regexp"]
                        if field["source"] not in df.columns:
                            log.warning("No column \"{source}\" in DataFrame.".format(source=field["source"]))
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

        
def data():
    return Data()
        
