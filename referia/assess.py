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


def notempty(val):
    return pd.notna(val) and val!=""

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
        if "selector" in config["series"]:
            self._selector = config["series"]["selector"]
        self._writeseries = access.series(self.index)
        self._writeseries = self._finalize_df(self._writeseries, config['series'])

    def _load_data(self):
        """Load the data specified in the _referia.yml file."""
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

        if self._writeseries is not None and index not in self._writeseries[self.get_selector()].values:
            raise ValueError("Invalid subindex.")
        else:
            self._subindex=index
            log.info(f"Subindex {index} selected.")


    def get_index(self):
        if self._index is None and self._data is not None:
            log.info(f"No index set, using first index of data.")
            self.set_index(self._data.index[0])
        return self._index

    def set_column(self, column):
        """Set the current column focus."""
        if column not in self.columns:
            if self._writedata is not None or self._writeseries is not None:
                self.add_column(column)

        if column not in self.columns:
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
            raise ValueError("Invalid selector column.")
        else:
            self._selector = column
            if self.get_subindex() not in self._writeseries[column]:
                self.set_subindex(None)
            log.info(f"Column {column} of Data._writeseries selected for selection.")

    def get_subindex(self):
        if self._subindex is None and self._writeseries is not None and self._selector is not None:
            log.info(f"No subindex set, using first entry of Data._writeseries.")
            self.set_subindex(self.get_subseries().at[0, self.get_selector()])
        return self._subindex

    def get_subseries(self):
        return self._writeseries[self._writeseries.index.isin([self.get_index()])]

    def get_subindices(self):
        if self._selector is None:
            return []
        return self.get_subseries()[self._selector]

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
            return
        else:
            if column not in self._writedata.columns:
                self.add_column(column)

            self._update_type(self._writedata, column, value)
            self._writedata.at[index, column] = value
            return


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
            return self._writeseries.loc[
                self._writeseries.index.isin([index])
                & (self._writeseries[selector]==subindex).values,
                column,
            ][0]
        elif self._writedata is not None and column in self._writedata.columns:
            return self._writedata.at[index, column]
        elif self._data is not None and column in self._data.columns:
            return self._data.at[index, column]
        else:
            log.warning(f"\"{column}\" not selected in self._writeseries or in self._writedata or in self._data returning \"None\"")
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
                mapping = automapping(self.columns)

        format = {}
        for key, column in mapping.items():
            format[key] = self.get_value_column(column)

        return format


    def conditions(self, entry):

        show_display = True
        if "conditions" in entry:
            for condition in entry["conditions"]:
                if "present" in condition:
                    if not condition["present"]["field"] in columns():
                        return False

                if "equal" in condition:
                    if not self.get_value_column(condition["equal"]["field"]) == condition["equal"]["value"]:
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
                            self.set_index(index)
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
        
