import os

import re

import pandas as pd
import liquid as lq

import datetime

from liquid.filter import string_filter
import urllib.parse

from pandas.api.types import is_string_dtype, is_numeric_dtype, is_bool_dtype

from ndlpy.log import Logger
from ndlpy.context import Context
from ndlpy import access
from ndlpy import data
from ndlpy.util import to_camel_case, remove_nan

from .settings import Settings
from .compute import Compute


from .util import renderable, markdown2html

from . import settings

from keyword import iskeyword

def is_valid_variable_name(name):
    return name.isidentifier() and not iskeyword(name)

    

@string_filter
def url_escape(string):
    """Filter to escape urls for liquid"""
    return urllib.parse.quote(string.encode('utf8'))


@string_filter
def markdownify(string):
    """Filter to convert markdown to html for liquid"""
    return markdown2html(string)


@string_filter
def relative_url(string):
    """Filter to convert to a relative_url a jupyter notebook under liquid"""
    url = os.path.join("/notebooks", string)
    return url


@string_filter
def absolute_url(string):
    """Filter to convert to a absolute_url a jupyter notebook under liquid"""
    # Remove the absolute url from beginning if it exists
    while string[0] == "/":
       string = string[1:]
    return os.path.join("http://localhost:8888/notebooks/", string)


def to_i(string):
    """Filter to convert the liquid entry to an integer under liquid."""
    if type(string) is str and len(string) == 0:
        return 0
    return int(float(string))


def empty(val):
    return pd.isna(val) or val==""


def automapping(columns):
    """Generate dictionary of mapping between variable names and column names."""
    mapping = {}
    for column in columns:
        field = to_camel_case(column)
        mapping[field] = column
    return mapping

class Data(data.DataObject):
    """Class to hold merged data flows together perform operations on them."""
    def __init__(self, data=None, colspecs=None, index=None, column=None, selector=None, user_file="_referia.yml", directory="."):

        self._directory = directory
        self._user_file = user_file
        self._cntxt = Context(name="referia")
        self._settings = settings.Settings(user_file=self._user_file,
                                           directory=self._directory)
        self._name_column_map = {}
        self._column_name_map = {}
        if "mapping" in self._settings:
            for name, column in self._settings["mapping"].items():
                self.update_name_column_map(column=column, name=name)
        
        self._log = Logger(
            name=__name__,
            level=self._cntxt["logging"]["level"],
            filename=self._cntxt["logging"]["filename"],
            directory = self._directory,            
        )
        if data is None:
            self._d = {}
        if isinstance(data, dict):
            data = pd.DataFame(data)
        if isinstance(data, list):
            data = pd.DataFame(data)
        if data is not None:
            if colspecs is not None:
                self._d = {}
                for typ, cols in colspecs.items():
                    if typ in self._global_data:
                        self._d[typ] = pd.Series(index=cols)
                        for col in cols:
                            if all(data[col]==data[col][0]):
                                self._d[col] = data[col][0]
                            else:
                                raise ValueError(f"Column \"{col}\" does not contain values that are all the same, and it is being reset to a constant column.")
                    else:
                        d = data[cols]
                        if typ in self._series_data:
                            self._d[typ] = d
                        else:
                            # Drop duplicates created from series presence
                            self._d[typ] = d[~d.index.duplicated(keep='first')]
            else:
                self._d = {"data" : data}
                
        # Which index is the current focus in the data.
        self._index = index
        # Which column is the current focus in the data.
        self._column = column
        # Which entry column in the series to disambiguate the selection of
        # the focus.
        self._selector = selector
        # The value in the selected entry column entry column value from the
        # series to use
        # Which subindex is the current focus in the data.
        self._subindex = None

        # Load in compute function capability.
        self._compute = Compute(self)
        self.autocache = True
        self.augment = False
        self.load_liquid()
        self.add_liquid_filters()

        if data is None:
            self.load_flows()

        self.at = self._AtAccessor(self)
        self.loc = self._LocAccessor(self)
        self.iloc = self._IlocAccessor(self)

    @property
    def _readonly_data(self):
        if self.augment:
            return []
        else:
            return ["data", "global_consts"]

    @property
    def _global_data(self):
        return ["globals", "global_consts"]

    @property
    def _series_data(self):
        return ["writeseries"]
    
    @property
    def _colspecs(self):
        """Return the columns associated with different data types."""
        val = {}
        for typ, data in self._d.items():
            if typ in self._global_data:
                val[typ] = data.index
            else:
                val[typ] = data.columns
        return val
            
    @property
    def _data(self):
        # Data that is input (not for writing to)
        if len(self._d)>0:
            return self._d["data"]
        else:
            return None

    @_data.setter
    def _data(self, value):
        # Data for writing outputs to.
        self._d["data"] = value

    @property
    def _writedata(self):
        if "writedata" in self._d:
            return self._d["writedata"]
        else:
            return None

    @_writedata.setter
    def _writedata(self, value):
        self._d["writedata"] = value

    @property
    def _writeseries(self):
        if "writeseries" in self._d:
            return self._d["writeseries"]
        else:
            return None

    @_writeseries.setter
    def _writeseries(self, value):
        self._d["writeseries"] = value

    @property
    def _cache(self):
        if "cache" in self._d:
            return self._d["cache"]
        else:
            return None
    
    @_cache.setter
    def _cache(self, value):
        self._d["cache"] = value

    @property
    def _globals(self):
        if "globals" in self._d:
            return self._d["globals"]
        else:
            return None

    @_globals.setter
    def _globals(self, value):
        self._d["globals"] = value

    @property
    def _global_consts(self):
        if "global_consts" in self._d:
            return self._d["global_consts"]
        else:
            return None

    @_global_consts.setter
    def _global_consts(self, value):
        self._d["global_consts"] = value

            
    class _AtAccessor:
        def __init__(self, data):
            self._data_object = data

        def __getitem__(self, key):
            if type(key) is tuple:
                col = key[1]
            else:
                col = key
            for typ, data in self._data_object._d.items():
                if self._data_object.isglobal(col):
                    cols = data.index
                else:
                    cols = data.columns
                if col in cols:
                    return data.at[key]
            raise KeyError(f"Unknown key \"{col}\" in data object.")

        def __setitem__(self, key, value):
            if type(key) is tuple:
                col = key[1]
            else:
                col = key
            for typ, data in self._data_object._d.items():
                if self._data_object.isglobal(col):
                    cols = data.index
                else:
                    cols = data.columns
                if col in cols:
                    if self._data_object.iswritable(col):
                        data.at[key] = value
                        return
                    else:
                        raise KeyError(f"Column \"{col}\" is not writable in data object.")
            # Autocache allows new set values to be allocated to cache.
            if self._data_object.autocache:
                if self._data_object._cache is None:
                    self._data_object._cache = pd.DataFrame(columns=[col], index=self._data_object.index)
                self._data_object._cache[col] = None
                self._data_object._cache.at[key] = value
            else:
                raise KeyError(f"Unknown key \"{key}\" in data object.")

    class _IlocAccessor:
        def __init__(self, data):
            self._data_object = data

        def __getitem__(self, key):
            label_key = self._convert_to_label_key(key)
            return self._data_object.loc[label_key]

        def __setitem__(self, key, value):
            label_key = self._convert_to_label_key(key)
            self._data_object.loc[label_key] = value

        def _convert_to_label_key(self, key):
            if isinstance(key, tuple):
                row_key, col_key = key
                row_labels = self._get_row_labels(row_key)
                col_labels = self._get_col_labels(col_key)
                return (row_labels, col_labels)
            elif isinstance(key, slice) or isinstance(key, int):
                # Handle the case where only row indices are provided
                row_labels = self._get_row_labels(key)
                return row_labels
            else:
                raise TypeError("Invalid index type")

        def _get_row_labels(self, key):
            # Assuming uniform row index across all DataFrames in _d
            sample_df = next(iter(self._data_object._d.values()))
            return sample_df.index[key]

        def _get_col_labels(self, key):
            # Assuming uniform column index across all DataFrames in _d
            sample_df = next(iter(self._data_object._d.values()))
            return sample_df.columns[key]

    class _LocAccessor:
        def __init__(self, data):
            self._data_object = data

        def __getitem__(self, key):
            df1 = pd.DataFrame()
            for typ, data in self._data_object._d.items():
                if not data.empty:
                    if isinstance(key, tuple):
                        row_key, col_key = key
                        # Apply key only to relevant columns for each DataFrame
                        if typ in self._global_data:
                            cols = data.index
                        else:
                            cols = data.columns
                        if isinstance(col_key, (list, tuple, pd.Index)):
                            col_key = [col for col in col_key if col in cols]
                        if typ in self._global_data:
                            df1 = df1.assign(**data[data.index.get_indexer_for(col_key)])
                        else:
                            sdata = data.loc[row_key, col_key]
                            df1 = df1.join(sdata, how="outer")
                            coplspecs[typ] = sdata.columns
            return self.__class__(df1, colspecs)

        def __setitem__(self, key, value):
            for k, df in self._data_object._d.items():
                if not df.empty:
                    # Apply key only to relevant columns for each DataFrame
                    applicable_key = key
                    if isinstance(key, (list, tuple, pd.Index)):
                        applicable_key = [col for col in key if col in df.columns]
                    df.loc[:, applicable_key] = value


    def __getitem__(self, keys):
        result = pd.DataFrame()

        if not isinstance(keys, list):
            keys = [keys]  # Convert to list if a single column name is provided

        for key in keys:
            for attr in ['_data', '_writedata', '_writeseries', '_cache']:
                if getattr(self, attr) is not None and key in getattr(self, attr).columns:
                    result[key] = getattr(self, attr)[key]
                    break

        return result

    def __setitem__(self, keys, values):
        if not isinstance(keys, list):
            keys = [keys]  # Convert to list if a single column name is provided
        if not isinstance(values, list):
            values = [values]  # Convert to list if a single value is provided

        if len(keys) != len(values):
            raise ValueError(f"Key lengths and value lengths are not the same.")
        for key, value in zip(keys, values):
            # Immutable columns and constants
            if not self.iswritable(key):
                raise KeyError(f"Cannot modify an immutable column or constant: \"{key}\"")

            if self.isglobal(key):
                if not all(v == value[0] for v in value):
                    raise KeyError(f"All values for global column \"{key}\" must be the same.")

            found = False
            for typ in self._d:
                if self.isglobal(key):
                    self._d[typ][key] = value[0]  # Set only the first value for globals
                    found = True
                    break
                else:
                    self._d[typ][key] = value
                    found = True
                    break

            if not found:  # Initialize in _cache if the key doesn't exist in any structure
                if self.autocache:
                    if self._cache is None :
                        self._cache = pd.DataFrame({key: value}, index=self._data.index)
                    else:
                        self._cache[key] = value
                else:
                    raise KeyError(f"Unknown writable key \"{key}\" in data object.")

    
    @property
    def autocache(self):
        if self._autocache:
            return True
        else:
            return False
    @autocache.setter
    def autocache(self, value):
        if not isinstance(value, bool):
            raise ValueError(f"autocache value must be boolean, set as \"{value}\"")
        self._autocache = value

    @property
    def augment(self):
        if self._augment:
            return True
        else:
            return False
    @augment.setter
    def augment(self, value):
        if not isinstance(value, bool):
            raise ValueError(f"augment value must be boolean, set as \"{value}\"")
        self._augment = value
        
    @property
    def index(self):
        if self._data is not None:
            return self._data.index
        else:
            return None

    @index.setter
    def index(self, values):
        if self._data is not None:
            self._data.index = values
        else:
            raise ValueError("There is no data value for index to be set to.")
        
    @property
    def writable(self):
        if self.augment:
            return True
        if self.autocache:
            return True
        for typ in self._d:
            if typ not in self._readonly_data:
                return True
        return False
        
    @property
    def columns(self):        
        columns = []
        for typ, data in self._d.items():
            if typ in self._global_data:
                columns += list(data.index)
            else:
                columns += list(data.columns)
        # Should perhaps make this unique column list? As in practice it behaves that way.
        return pd.Index(columns)

    def _col_source(self, col):
        """Return the source of a column."""
        for typ, data in self._d.items():
            if col in data.columns:
                return typ
        if self.autocache:
            return "cache"
        else:
            return None
        
    def iswritable(self, col):
        """Is a given column writable?"""
        if self.augment:
            return True
        
        if col not in self.columns:
            if self.autocache:
                return True
            else:
                return False

        if self._col_source(col) in self._readonly_data:
            return False
        else:
            return True

    def isglobal(self, col):
        """Is a given column writable?"""
        if self._col_source(col) in self._global_data:
            return True
        else:
            return False
        
    def isseries(self, col):
        """Is a given column a series column?"""
        if self._col_source(col) in self._series_data:
            return True
        else:
            return False
        
    def _augment_global_consts(self, configs, suffix=''):
        """Augment the globals by joining the two series together."""
        if type(configs) is not list:
            configs = [configs]
        for i, conf in enumerate(configs):
            if "select" in conf:
                index_row = conf["select"]
            else:
                index_row = "globals"
            if "rsuffix" in conf:
                rsuffix = conf["rsuffix"]
            else:
                rsuffix = suffix.format(joinNo=i)
            if "local" in conf:
                if type(conf["local"]) is dict:
                    ds = pd.Series(conf["local"], name=index_row)
                    for cname in ds.index:
                        if cname not in self._column_name_map:
                            if is_valid_variable_name(cname):
                                self.update_name_column_map(column=cname, name=cname)
                else:
                    errmsg = f"In global_consts a \"local\" specification must contain a dictionary of fields and values."
                    self._log.error(errmsg)
                    raise ValueError(errmsg)
            else:

                df = self._finalize_df(*access.globals_data(conf, pd.Index([index_row], name="index")), strict_columns=True)
                ds = df.loc[index_row]

            if self._global_consts is None:
                self._global_consts = ds
            else:
                if self._global_consts.name != ds.name:
                    self._global_consts.name += "_" + ds.name
                    ds.name = self._global_consts.name
                self._global_consts = pd.DataFrame(self._global_consts).T.join(pd.DataFrame(ds).T, rsuffix=rsuffix).loc[ds.name]
                    
    def _augment_data(self, configs, how="left", suffix='', concat=False, axis=0):
        """Augment the data by joining or concatenating the new values."""
        if type(configs) is not list:
            configs = [configs]
        for i, conf in enumerate(configs):
            if "local" in conf:
                if type(conf["local"]) is dict:
                    try:
                        df = pd.DataFrame(**conf["local"])
                        if df.index.name is None:
                            df.index.name = "index"
                    except:
                        if "data" not in conf["local"]:
                            print("Missing data entry in local dataframe specification.")
                        if "index" not in conf["local"]:
                            print("Missing index entry in local dataframe specification.")
                        print("Could not create data frame from details specified in \"local\" entry.")
                        raise
                    for cname in df.columns:
                        if cname not in self._column_name_map:
                            if is_valid_variable_name(cname):
                                self.update_name_column_map(column=cname, name=cname)
                else:
                    errmsg = "\"local\" specified in config but not in form of a dictionary."
                    self._log.error(errmsg)
                    raise ValueError(errmsg)
            else:
                df = self._finalize_df(*access.read_data(conf))
                    
            if df.index.is_unique:
                if "join" in conf:
                    join = conf["join"]
                else:
                    join = how
                if "rsuffix" in conf:
                    rsuffix = conf["rsuffix"]
                else:
                    rsuffix = suffix.format(joinNo=i)
                if self._data is None:
                    self._data = df
                else:
                    if concat:
                        self._data = pd.concat([self._data, df], axis=axis, join=join)
                    else:
                        self._data = self._data.join(df, rsuffix=rsuffix, how=join)
            else:
                strindex = pd.Series([str(ind) for ind in df.index])
                duplicates = ', '.join(strindex[df.index.duplicated()])
                errmsg = f"The index for the incorporated data frame \"{i}\" must be unique. Index \"{duplicates}\" is/are duplicated."
                self._log.error(errmsg)
                raise ValueError(errmsg)

    def _remove_index_duplicates(self):
        """Rename the index of any duplicates"""
        existlist=[]
        count=0
        indseries = pd.Series(self.index)
        for i, ind in indseries.items():
            if ind not in existlist:
                existlist.append(ind)
                count=0
                continue
            else:
                count+=1
                indseries.at[i] = str(ind) + "_" + str(count)
        self.index = indseries

    def _load_allocation(self):
        """Load in the primary data source as a data frame."""
        # Augment the data with default augmentation as "outer"
        if "allocation" in self._settings:
            self._augment_data(self._settings["allocation"], how="outer", concat=True, axis=0)
            self._remove_index_duplicates()
        else:
            errmsg = f"No \"allocation\" field in config file."
            self._log.error(errmsg)
            raise ValueError(f"No \"allocation\" field in config file.")
            
    def _load_additional(self):
        """Load in the additional data sources as data frames."""
        # Augment the data with default augmentation as "inner"
        if "additional" in self._settings:
            self._augment_data(self._settings["additional"], how="inner", concat=False, suffix="_{joinNo}")

    def _load_globals(self):
        """Load in any global variables to a data series."""
        if "select" in self._settings["globals"]:
            index_row = self._settings["globals"]["select"]
        else:
            index_row = "globals"
            
        df = self._finalize_df(*access.globals_data(self._settings["globals"], pd.Index([index_row], name="index")), strict_columns=True)
        self._globals = df
        self._globals_index = index_row

    def _load_cache(self):
        """Load in any cached data to data frames."""
        df = self._finalize_df(*access.cache(self._settings["cache"], self.index), strict_columns=True)
        if df.index.is_unique:
            self._cache = df
        else:
            strindex = pd.Series([str(ind) for ind in df.index])
            duplicates = ', '.join(strindex[df.index.duplicated()])
            errmsg = f"The index for the cache must be unique. Index \"{duplicates}\" is/are duplicated."
            self._log.error(errmsg)
            raise ValueError(errmsg)
        
    def _load_scores(self):
        """Load in the score data to data frames."""
        df = self._finalize_df(*access.scores(self._settings["scores"], self.index))
        if df.index.is_unique:
            self._writedata = df
        else:
            strindex = pd.Series([str(ind) for ind in df.index])
            duplicates = ', '.join(strindex[df.index.duplicated()])
            errmsg = f"The index for writedata must be unique. Index \"{duplicates}\" is/are duplicated."
            self._log.error(errmsg)
            raise ValueError(errmsg)

    def _load_series(self):
        """Load in the series data to data frames."""
        if "selector" not in self._settings["series"]:
            self._log.error(errmsg)
            errmsg = f"A series entry must have a \"selector\" column."
            raise ValueError(errmsg)
        self._writeseries = self._finalize_df(*access.series(self._settings["series"], self.index))
        selector = self._settings["series"]["selector"]
        if selector not in self._writeseries.columns:
            self._writeseries[selector] = None
            
        self.sort_series()

    def sort_series(self):
        """Sort the series by the column specified."""
        if "series" in self._settings:
            series = self._settings["series"]
        else:
            return
        if "sortby" in series and "field" in series["sortby"] and series["sortby"]["field"] in self._writeseries:
            if "ascending" in series["sortby"]:
                ascending = series["sortby"]["ascending"]
            else:
                ascending=True
            field=series["sortby"]["field"]
            self._log.debug(f"Sorting series by \"{field}\"")
            self._writeseries.sort_values(by=field, ascending=ascending, inplace=True)

    def load_input_flows(self):
        """Load the input flows specified in the _referia.yml file."""
        self._load_allocation()
        if "additional" in self._settings:
            self._log.debug("Joining allocation and additional information.")
            self._load_additional()

        # If sorting is requested do it here.
        self.sort_data()
        self._load_global_consts()

    def _load_global_consts(self):
        """Load constants from the _referia.yml file."""
        if "global_consts" in self._settings:
            self._augment_global_consts(self._settings["global_consts"])
                    
        
    def sort_data(self):
        if "sortby" in self._settings and "field" in self._settings["sortby"] and self._settings["sortby"]["field"] in self.columns:
            if "ascending" in self._settings["sortby"]:
                ascending = self._settings["sortby"]["ascending"]
            else:
                ascending=True
            field=self._settings["sortby"]["field"]
            self._log.debug(f"Sorting by \"{field}\"")
            self.sort_values(by=field, ascending=ascending, inplace=True)

    def load_output_flows(self):
        """Load the output flows data specified in the _referia.yml file. 
        Different output flows are listed in the configuration file under "globals", "cache", "scores", "series".
        Those listed under "globals" are constants that don't change when the index changes. 
        Those specified under "cache" are variables that can be cached and used in liquid templates or comptue functions but are assumed as not needed to be stored.
        Those specified under "scores" are the variables that the user will want to store.
        Those specified under "series" are variabels that the user is storing, but there are multiple entries for each index."""
        if "globals" in self._settings:
            self._globals = None
            self._load_globals()
        if "cache" in self._settings:
            self._cache = None
            self._load_cache()
        if "scores" in self._settings:
            self._writedata = None
            self._load_scores()
        if "series" in self._settings:
            self._writeseries = None
            self._load_series()

    def load_flows(self):
        """Load the input and output flows."""
        autocache = self.autocache
        self.autocache = False
        self.load_input_flows()
        self.load_output_flows()
        self.augment = True
        self.preprocess()
        self.augment = False
        self.autocache = autocache
        
    def save_flows(self):
        """Save the output flows."""
        if self._globals is not None:
            self._log.debug(f"Writing _globals.")
            access.write_globals(self._globals, self._settings)
        if self._cache is not None:
            self._log.debug(f"Writing _cache.")
            access.write_cache(self._cache, self._settings)
        if self._writedata is not None:
            self._log.debug(f"Writing _writedata.")
            access.write_scores(self._writedata, self._settings)
        if self._writeseries is not None:
            access.write_series(self._writeseries, self._settings)
            self._log.debug(f"Writing _writeseries.")

    def load_liquid(self):
        """Load the liquid environment."""
        loader = None
        if "liquid" in self._settings:
            if "templates" in self._settings["liquid"]:
                if "dir" in self._settings["liquid"]["templates"]:
                    templates_path = [os.path.abspath(self._settings["liquid"]["templates"])]
                else:
                    template_path = [
                        os.path.join(os.path.dirname(__file__), "templates"),
                    ]

                    if "ext" in self._settings["liquid"]:
                        ext = self._settings["liquid"]["ext"]
                        loader = lq.loaders.FileExtensionLoader(search_path=template_path, ext=ext)
                    else:
                        loader = lq.FileSystemLoader(template_path)
            elif "dict" in self._settings["liquid"]["templates"]:
                loader = lq.loaders.DictLoader(self._settings["liquid"]["templates"]["dict"])
        self._liquid_env = lq.Environment(loader=loader)


    def add_liquid_filters(self):
        """Add liquid filters to the liquid environment."""
        self._liquid_env.add_filter("url_escape", url_escape)
        self._liquid_env.add_filter("markdownify", markdownify)
        self._liquid_env.add_filter("relative_url", relative_url)
        self._liquid_env.add_filter("absolute_url", absolute_url)
        self._liquid_env.add_filter("to_i", to_i)
        
    def set_index(self, index):
        """Index setter"""
        orig_index = self._index
        # If index has changed, run computes.
        if orig_index is not None and index != orig_index:
            if orig_index in self.index:
                self.compute_post()
        # If 
        if self._data is not None and index not in self.index:
            self._log.warning(f"Index \"{index}\" not found in _data")
            self.add_row(index=index)
            self.set_index(index)
        else:
            self._index = index
            self._log.debug(f"Index \"{index}\" selected.")
            self.check_or_set_subseries()
        # If index has changed, run computes.
        if orig_index is None or self._index != orig_index:
            self.compute_pre()

    def check_or_set_subseries(self):
        """Check if there is a sub-series if so, use top subindex, if not create a row."""
        if self._writeseries is not None:
            subindices = self.get_subseries()
            if len(subindices) > 0:
                subindex = self.get_subindex()
                selector = self.get_selector()
                if subindex is None or not subindex in subindices[selector]:
                    self.set_subindex(subindices[selector][0])
            else:
                self.add_series_row(self._index)
                


    def set_subindex(self, subindex):
        """Subindex setter"""
        if subindex is None:
            self._subindex = None
            self._log.debug(f"Subindex set to None.")
            return

        if self._writeseries is not None and subindex not in self.get_subindices():
            index = self.get_index()
            errmsg = f"Subindex \"{subindex}\" under \"{index}\" not available in current series."
            self._log.error(errmsg)
            raise ValueError(errmsg)
        else:
            self._subindex=subindex
            self._log.debug(f"Subindex \"{subindex}\" selected.")


    def get_index(self):
        if self._index is None and self._data is not None:
            self._log.debug(f"No index set, using first index of data.")
            self.set_index(self._data.index[0])
        return self._index

    def _strict_columns(self, group):
        if "strict_columns" in self._settings:
            return self._settings["strict_columns"]
        elif "strict_columns" in self._settings[group]:
            return self._settings[group]["strict_columns"]
        elif group=="cache" or group=="globals":
            return True
        else:
            return False # historic default, should shift this to True.

    def preprocess(self):
        """Run any preprocessing computations."""
        self._compute.preprocess()

    def compute_pre(self):
        """Run pre-computation on the index."""
        self._compute.run_all(pre=True)
        
    def compute_post(self):
        """Run post-computation on the index."""
        self._compute.run_all(post=True)

    def compute_append(index, row):
        """Run computation for an appended row."""
        self._compute.run_all(df=row, index=index, pre=True)
        
    def set_column(self, column):
        """Set the current column focus."""
        if column == "_":
            self._column = "_"
            self._log.debug(f"Set column to \"_\".")
            return
        if column is None:
            self._log.warning(f"Was asked to set column to None.")
            return
        if column not in self.columns and column!=self.index.name:
            self._log.warning(f"Attempting to add column \"{column}\" as a set request has been given to non existent column.")
            self.add_column(column)

        if column not in self.columns and column != self.index.name:
            errmsg = f"Cannot set column \"{column}\"  as it does not exist."
            self._log.error(errmsg)
            raise ValueError(errmsg)
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
            selectors = list(self._writeseries.columns)
            if self._selector is not None and self._selector in selectors:
                # Return selectors with selector at front (to ensure it is default) for widgets)
                selectors.insert(0, selectors.pop(selectors.index(self._selector)))
            return selectors

    def set_selector(self, column):
        """Set which column of the series is to be used for selection."""
        # Set to None to indicate that self._writedata is correct place for recording.
        if column is None:
            self._log.warning(f"No column selected for selector, setting to \"None\".")
            self._selector = None
            return

        if column not in self.get_selectors():
            self._log.info(f"Column \"{column}\" of chosen for selection not in Data._writeseries ... adding.")
            self.add_column(column)
            self.set_selector(column)
        else:
            self._selector = column
            self._log.debug(f"Column \"{column}\" of Data._writeseries selected for selection.")
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
            self._log.debug(f"No subindex set, using first entry of portion of Data._writeseries indexed by \"{index}\".")
            self.set_subindex(subindices[0])
        else:
            self._log.info(f"No subindex available.")
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
            subseries = self.get_subseries()[self._selector]
            return pd.Index(subseries.values, name=self._selector, dtype=subseries.dtype)
        except KeyError as err:
            raise KeyError(f"Could not find index \"{err}\" in the subseries when using it as a selector.")

    def set_series_value(self, value, column):
        """Set a value in the write series data frame"""
        if not self.iswritable(column):
            self._log.warning(f"Warning attempting to write to non writable column \"{column}\".")

        if not self.isseries(column):
            self.add_series_column(column)

        self._update_type(self._writeseries, column, value)

    def set_value_column(self, value, column):
        """Set a value to a column in the write data frame"""
        orig_col = self.get_column()
        self.set_column(column)
        self.set_value(value)
        if orig_col is not None:
            self.set_column(orig_col)

    def get_value_column(self, column):
        """Get a value from a column in the data frame(s)"""
        orig_col = self.get_column()
        self.set_column(column)
        value = self.get_value()
        if orig_col is not None:
            self.set_column(orig_col)
        return value
    

    def set_value(self, value):
        """Set the value of the current cell under focus."""
        column = self.get_column()
        if column is None:
            raise KeyError(f"Warning attempting to write a value {value} when column is not set.")
        if self._globals is not None and column in self._globals.index:
            self._globals.at[self._globals_index, column] = value
            return

        
        index = self.get_index()
        selector = self.get_selector()
        subindex = self.get_subindex()
        # If trying to set a numeric valued column's entry to a string, set the type of column to object.
        if not self.iswritable(column):
            raise KeyError(f"Attempting to write to column \"{column}\" which is read only.")
        
        col_source = self._col_source(column)
        if not self.isglobal(column):
            self._d[col_source].at[index, column] = value
        elif not self.isseries(column):
            self._d[col_source].at[column] = value
        else:
            self._update_type(self._d[col_source], column, value)
            self._d[col_source].loc[
                self._d[col_source].index.isin([index])
                & (self._d[col_source][selector]==subindex).values,
                column
            ] = value
        # else:
        #     self.add_series_column(column)
        #     self.set_series_value(value, column)

    def drop_column(self, column_name):
        if column_name not in self.columns:
            raise KeyError(f"No column \"{column}\" in data object.")           
        elif not self.iswritable(column_name):
            raise KeyError(f"Attempting to drop column \"{column}\" in which is read only.")
        for typ, data in self._d.items():
            if not self.isglobal(column_name):
                if column_name in data.columns:
                    self._log.debug(f"Dropping column \"{column_name}\" from _{typ}.")
                    self._d[typ].drop(column_name, axis=1, inplace=True)
            else:
                if column_name in data.index:
                    self._log.debug(f"Dropping value \"{column_name}\" from _{typ}.")
                    self._d[typ].drop(column_name, inplace=True)

    def filter_rows(self, condition):
        for typ in self._d:
            if not self.isglobal(typ):
                 self._d[typ] = self._d[typ][condition]
           
    def get_shape(self):
        return self.to_pandas().shape

    def to_pandas(self):
        df1 = pd.DataFrame()
        for typ, data in self._d.items():
            if typ in self._global_data:
                df1 = df1.assign(**data)
            else:
                df1 = df1.join(data, how="outer")
        return df1
        
            
    def get_value_by_element(self, element):
        """Return the value of an element from the under focus cell (e.g. a list entry or a dict entry)."""
        value = self.get_value()
        if type(element) is int and type(value) is not list:
            self._log.warning(f"Attempt to get element of a non list entry with an element \"{element}\" that is an integer.")
            return None
        elif type(element) is str and type(value) is not dict:
            self._log.warning(f"Attempt to get element of a non dictionary entry with an element \"{element}\" that is a string.")
            return None
        else:
            if type(element) is int and not len(value)>element:
                return None
            if type(element) is str and element not in value:
                return None
            return value[element]

    def set_value_by_element(self, value, element):
        """Set the value of an element from the under focus cell (e.g. a list entry or a dict entry)."""
        orig_value = self.get_value()
        if type(element) is int and type(orig_value) is not list:
            self._log.warning("Value wasn't a list and element was set as integer, so converting to a list.")
            orig_value = [orig_value]
            
        elif type(element) is str and type(orig_value) is not dict:
            self._log.warning("Value wasn't a dictionary and element was set as string, so converting to a dictionary.")
            orig_value = {"original": orig_value}

        if type(element) is int and not len(orig_value)>element:
            while not len(orig_value)>element:
                orig_value.append(None)
        orig_value[element] = value
        self.set_value(orig_value)
        
    def get_column_values(self):
        """Return a pd.Series containing all the values in a column."""
        column = self.get_column()
        if column == None:
            return None
        return self.__getitem__(column)
        

    def get_subseries_values(self):
        """Return a pd.Series containing all the values in a column."""
        column = self.get_column()
        if column == None:
            return None
        index = self.get_index()

        if self.isseries(column):
            indexer = self._writeseries.index.isin([index])
            if indexer.sum()>0:
                return self._writeseries.loc[indexer, column]
            else:
                self._log.warning(f"No data available with this index returning None.")
                return None
        else:
            self._log.warning(f"\"{column}\" not selected in self._writeseries or in self._writedata or in self._data returning \"None\"")
            return None

    def get_value(self):
        """Return the value of the current cell under focus."""
        # Ordering here dictates the priority of selection, global constants, then globals, then series, then writedata, then cache then data.
        column = self.get_column()
        if column == "_":
            return None
        if column == None:
            return None
        if self._global_consts is not None and column in self._global_consts.index:
            return self._global_consts[column]

        if self._globals is not None and column in self._globals.columns:
            return self._globals.at[self._globals_index, column]

        index = self.get_index()
        if index == None:
            return None
        selector = self.get_selector()
        subindex = self.get_subindex()
        # Prioritise returning from the _writeseries then the _writedata structure first.
        if self._selector is not None and self._writeseries is not None and column in self._writeseries.columns:
            if subindex is not None:
                indexer = (self._writeseries.index.isin([index])
                           & (self._writeseries[selector]==subindex).values)
                if indexer.sum()>0:
                    return self._writeseries.loc[indexer, column].iloc[0]
                else:
                    self._log.warning(f"No data available with this subindex and index , returning None.")
            else:
                self._log.warning(f"No subindex selected, returning None.")
        elif self._writedata is not None and column in self._writedata.columns:
            if index in self._data.index and not index in self._writedata.index:
                # If index isn't created in write data yet, return None.
                return None
            try:
                return self._writedata.at[index, column]
            except KeyError as err:
                raise KeyError(f"Cannot find index: \"{index}\" and column: \"{column}\" in _writedata.") from err
        elif self._cache is not None and column in self._cache.columns:
            if index in self._data.index and not index in self._cache.index:
                # If index isn't created in write data yet, return None.
                return None
            try:
                return self._cache.at[index, column]
            except KeyError as err:
                raise KeyError(f"Cannot find index: \"{index}\" and column: \"{column}\" in _cache.") from err
        elif self._data is not None and column in self._data.columns:
            try:
                return self._data.at[index, column]
            except KeyError as err:
                raise KeyError(f"Cannot find index: \"{index}\" and column: \"{column}\" in _data.") from err
        elif self._data is not None and column==self._data.index.name:
            return index
        else:
            self._log.warning(f"\"{column}\" not selected in self._writeseries or in self._writedata or in self._cache or in self._data returning \"None\"")
            return None

    def add_column(self, column, data=None):
        if column in self.columns:
            errmsg = f"Was requested to add column \"{column}\" but it already exists in data."
            self._log.error(errmsg)
            raise ValueError(errmsg)
        if self._writedata is None and self._writeseries is None:
            errmsg = f"There is no _writedata or _writeseries loaded to add the column \"{column}\" to."
            self._log.error(errmsg)
            raise ValueError(errmsg)

        if self._writeseries is not None and column in self._writeseries.columns:
            self._log.warning(f"\"{column}\" requested to be added but it already exists in _writeseries.")
            return

        if self._writedata is not None and column in self._writedata.columns:
            self._log.warning(f"\"{column}\" requested to be added but it already exists in _writedata.")
            return
        
        if self._writeseries is not None and column not in self._writeseries.columns:
            if not self._strict_columns("series"):
                self._log.info(f"\"{column}\" not in writeseries columns ... adding.")
                self._writeseries[column] = data
                return
        
        if self._writedata is not None and column not in self._writedata.columns:
            if not self._strict_columns("scores"):
                self._log.info(f"\"{column}\" not in write columns ... adding.")
                self._writedata[column] = data
                return
        errmsg = f"Cannot add column \"{column}\" to either scores or series due to strict_columns being set and/or series or scores not being present."
        self._log.error(errmsg)
        raise ValueError(errmsg)

    def set_dtype(self, column, dtype):
        """Set a Data._writedata column to the given data type."""
        if self._writedata is not None and column in self._writedata.columns:
            self._log.debug(f"\"{column}\" being set to \"{dtype}\".")
            self._writedata[column] = self._writedata[column].astype(dtype)
        if self._writeseries is not None and column in self._writeseries.columns:
            self._log.debug(f"\"{column}\" being set to \"{dtype}\".")
            self._writeseries[column] = self._writeseries[column].astype(dtype)

    def _append_row(self, df, index):
        row = pd.DataFrame(columns=df.columns, index=pd.Index([index], name=df.index.name))
        # Handle the fact that the index is stored as a column also
        if df.index.name in row:
            row[df.index.name] = index
        if self.writable:
            # Only precompute if something to write to
            self.compute_append(index=index, row=row)
        # was return df.append(row) before append deprecation
        return pd.concat([df, row])

    def add_row(self, index=None, subindex=None):
        """Add a row with a given index (and optionally subindex) to the data structure."""
        if index is None:
            index = self.get_index()

        selector = self.get_selector()
        if self._data is not None and index not in self.index:
            self._data = self._append_row(self._data, index)
            self._log.info(f"\"{index}\" added as row in Data._data.")
            self.set_index(index)

        if self._writedata is not None and index not in self._writedata.index:
            self._writedata = self._append_row(self._writedata, index)
            self._log.info(f"\"{index}\" added as row in Data._writedata.")
            self.set_index(index)

        if self._writeseries is not None and index not in self._writeseries.index:
            self._writeseries = self._append_row(self._writeseries, index)
            self._log.info(f"\"{index}\" added as row in Data._writeseries.")
            self.set_index(index)

    def add_series_row(self, index=None):
        """Add a row to the series."""
        if index is None:
            index = self.get_index()
        self._writeseries = self._append_row(self._writeseries, index)
        self._log.info(f"\"{index}\" added subseries row in Data._writeseries.")


    def add_series_column(self, column):
        """Add a column to the data series"""
        if column not in self._writeseries.columns:
            self._log.info(f"\"{column}\" not in series columns ... adding.")
            self._writeseries[column] = None
        else:
            self._log.warning(f"\"{column}\" requested to be added to series data but already exists.")

    def update_name_column_map(self, name, column):
        """Update the map from valid variable names to columns in the data frame. Valid variable names are needed e.g. for Liquid filters."""
        if column in self._column_name_map and self._column_name_map[column] != name:
            original_name = self._column_name_map[column]
            errmsg = f"Column \"{column}\" already exists in the name-column map and there's an attempt to update its value to \"{name}\" when it's original value was \"{original_name}\" and that would lead to unexpected behaviours. Try looking to see if you're setting column values to different names across different files and/or file loaders."
            self._log.error(errmsg)
            raise ValueError(errmsg)
        self._name_column_map[name] = column
        self._column_name_map[column] = name
        
    def _default_mapping(self):
        """Generate the default mapping from config or from columns"""
        # If a mapping is provided in _referia.yml use it, otherwise generate
        #if self._name_column_map is None:
        #    for name, column in  automapping(self.columns).items():
        #        self.update_name_column_map(name=name, column=column)

        return self._name_column_map

    def mapping(self, mapping=None, series=None):
        """Generate dictionary of mapping between variable names and column values."""
        
        if mapping is None:
            if series is None: # remove any columns not in self.columns
                mapping = {name: column for name, column in self._default_mapping().items() if column in self.columns or column==self._data.index.name}
            else: # remove any columns not in provided series
                mapping = {name: column for name, column in self._default_mapping().items() if column in series.index}

        format = {}
        for name, column in mapping.items():
            if series is not None:
                if column in series:
                    format[name] = series[column]                    
            else:
                self.set_column(column)
                format[name] = self.get_value()
                
        return remove_nan(format)


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

    def view_to_value(self, view, kwargs=None, local={}):
        """Create the text of the view."""
        value = ""

        if self.conditions(view):
            if type(view) is dict:
                if "local" in view:
                    local.update(view["local"])
                if "list" in view:
                    values = []
                    for v in view["list"]:
                        values.append(self.view_to_value(v, kwargs, local))
                    return values
                if "field" in view:
                    return self.get_value_column(view["field"])
                if "join" in view:
                    if "list" not in view["join"]:
                        self._log.warning("No field \"list\" in \"concat\" viewer.")
                    elements = self.view_to_value(view["join"], kwargs, local)
                    if "separator" in view["join"]:
                        sep = view["join"]["separator"]
                    else:
                        sep = "\n\n"
                    return sep.join(elements)
                if "compute" in view:
                    return self.compute_to_value(view["compute"])
                if "liquid" in view:
                    return self.liquid_to_value(view["liquid"], kwargs, local)
                if "tally" in view:
                    return self.tally_to_value(view["tally"], kwargs, local)
                if "display" in view:
                    return self.display_to_value(view["display"], kwargs, local)
            else:
                raise TypeError("View should be a \"dict\".")
        else:
            return ""

    def summary_viewer_to_value(self, viewer, kwargs=None):
        """Convert a summary viewer structure to populated values."""
        value = ""
        if type(viewer) is not list:
            viewer = [viewer]
        for view in viewer:
            value += self.summary_view_to_value(view, kwargs)
            if value != "":
                value += "\n\n"
        return value
    
    def summary_view_to_value(self, view, kwargs=None):
        """Create the text of the summary view."""
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
                        self._log.warning("No field \"list\" in \"concat\" viewer.")
                    elements = self.view_to_value(view["join"], kwargs)
                    if "separator" in view["join"]:
                        sep = view["join"]["separator"]
                    else:
                        sep = "\n\n"
                    return sep.join(elements)
                if "compute" in view:
                    value += self.compute_to_value(view["compute"], kwargs)
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
        elif "field" in view:
            return to_camel_case(view["field"])
        elif "join" in view:
            name = "join_"
            if "list" not in view["join"]:
                self._log.warning("No field \"list\" in \"concat\" viewer.")
            name += self.view_to_tmpname(view["join"])
            return name
        elif "compute" in view:
            return self.compute_to_tmpname(view["compute"])
        elif "liquid" in view:
            return self.liquid_to_tmpname(view["liquid"])
        elif "display" in view:
            return self.display_to_tmpname(view["display"])

    def tally_to_value(self, tally, kwargs=None, local={}):
        """Create the text of the view."""
        return self.tally_values(tally, kwargs, local)

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
                    self.set_column(condition["equal"]["field"])
                    if not self.get_value() == condition["equal"]["value"]:
                        return False
        return True

    def display_to_tmpname(self, display):
        """Convert a display string to a temp name"""
        return to_camel_case(display.replace("/", "_").replace("{","").replace("}", ""))


    def display_to_value(self, display, kwargs=None, local={}):
        if kwargs is None:
            kwargs = self.mapping()
        kwargs.update(local)
        try:
            return display.format(**kwargs)
        except KeyError as err:
            raise KeyError(f"The mapping doesn't contain the key {err} requested in \"{display}\". Set the mapping in \"_referia.yml\".") from err

    def compute_to_value(self, compute):
        """Extract a value from a computation"""
        compute_prep = self._compute.prep(compute)
        return self._compute.run(compute_prep)
    
    def compute_to_tmpname(self, compute):
        """Convert a display string to a temp name"""
        return to_camel_case(compute["function"].replace("/", "_").replace("{","").replace("}", "").replace("%","-"))
        
    def liquid_to_tmpname(self, display):
        """Convert a display string to a temp name"""
        return to_camel_case(display.replace("/", "_").replace("{","").replace("}", "").replace("%","-"))

    
    def liquid_to_value(self, display, kwargs=None, local={}):
        if kwargs is None:
            kwargs = self.mapping()
        kwargs.update(local)
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

    def tally_values(self, tally, kwargs=None, local={}):
        value = ""
        if "begin" in tally:
            value += tally["begin"]
            if value != "":
                value += "\n\n"
        orig_subindex = self.get_subindex()
        subindices = self.tally_series(tally)
        for subindex in subindices:
            self.set_subindex(subindex)
            value += self.view_to_value(tally, kwargs, local)
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
                return pd.Index([subindices[ind]], dtype=subindices.dtypegg)
            except IndexError as e:
                self._log.warning(f"Requested invalid index in Data.tally_series()")
                return pd.Index([subindices[cur_loc]], dtype=subindices.dtype)

        def subind_series(ind, starter=True, reverse=False):
            try:
                if starter:
                    return pd.Index(subindices[ind:], dtype=subindices.dtype)
                else:
                    return pd.Index(subindices[:ind], dtype=subindices.dtype)

            except IndexError as e:
                self._log.warning(f"Requested invalid index in Data.tally_series()")
                if starter:
                    return pd.Index(subindices[cur_loc:], dtype=subindices.dtype)
                else:
                    return pd.Index(subindices[:cur_loc], dtype=subindices.dtype)

        if "reverse" not in tally or not tally["reverse"]:
            reverse=False
        else:
            reverse=True
            
        if "which" not in tally:
            return subindices
        elif tally["which"] == "pop":
            return subind_val(0, reverse=reverse)
        elif tally["which"] == "bottom":
            return subind_val(-1, reverse=reverse)
        elif tally["which"] == "previous":
            return subind_val(cur_loc+1, reverse=reverse)
        elif tally["which"] == "next":
            return subind_val(cur_loc-1, reverse=reverse)
        elif tally["which"] == "earlier":
            return subind_series(cur_loc+1, reverse=reverse)
        elif tally["which"] == "later":
            return subind_series(cur_loc, starter=False, reverse=reverse)
        elif tally["which"] == "others":
            return subind_series(cur_loc, starter=False, reverse=reverse).append(subind_series(cur_loc+1))
        elif tally["which"] == "all":
            return subindices
        else:
            errmsg = "Unrecognised subindices specifier in tally."
            self._log.error(errmsg)
            raise ValueError(errmsg)

    def _column_from_renderable(self, df, **kwargs):
        """Create a column from a renderable field."""
        return self._series_from_renderable(df, is_index=False, **kwargs)


    def _index_from_renderable(self, df, **kwargs):
        """Create an index from a renderable field."""
        return self._series_from_renderable(df, is_index=True, **kwargs)

    def _series_from_value(self, df, value, name, **kwargs):
        """Create a series from a given value."""
        series = pd.Series(index=df.index, dtype="object")
        for index in series.index:
            series[index] = value
        return series        

    def _series_from_renderable(self, df, is_index=False, index_col=None, **kwargs):
        """Extract a series from a renderable dictionary."""
        series = pd.Series(index=df.index, dtype="object")
        for index in series.index:
            
            if not is_index and len(self.columns)>0:
                #try:
                if index in self.index: # This prevents adding new indices.
                    self.set_index(index)
                #except ValueError as err:
                #    errmsg = f"Could not set index, \"{index}\", likely due to allocation augmentation."
                #    self._log.error(errmsg)
                #    raise ValueError(errmsg)
                    
                    
            kwargs2 = self.mapping(series=df.loc[index])
            series[index] = self.view_to_value(kwargs, kwargs2)
        return series
    
    def _series_from_regexp_of_field(self, df, source, regexp, name, **kwargs):
        """Extract a series from data frame field and regular expression."""
        series = pd.Series(index=df.index, dtype="object")
        for index in series.index:
            if source in df.columns:
                sourcetext = df.at[index, source]
            elif df.index.name == source:
                sourcetext = index
            else:
                raise KeyError(f"Could not find the source field, \"{err}\", listed in _referia.yml under name: \"{name}\" in the DataFrame.")
            match = re.match(
                regexp,
                sourcetext,
            )
            if match:
                if len(match.groups())>1:
                    self._log.warning(f"Multiple regular expression matches in \"{regexp}\".")
                series[index] = match.group(1)
            else:
                self._log.warning(f"No match of regular expression \"{regexp}\" to \"{source}\".")
        return series


    def _finalize_df(self, df, details, strict_columns=False):
        """This function augments the raw data and sets the index of the data frame."""
        """for field in dtypes:
            if dtypes[field] is str_type:
                data[field].fillna("", inplace=True)"""
        if "index" not in details:
            errmsg = "Missing index field in data frame specification in _referia.yml"
            self._log.errmsg(errmsg)
            raise ValueError(errmsg)

        if "columns" in details:
            # Make sure the listed columns are present.
            for column in details["columns"]:
                if column not in df.columns:
                    df[column] = None
            if strict_columns or ("strict_columns" in self._settings and self._settings["strict_columns"]) or ("strict_columns" in details and details["strict_columns"]):
                if "columns" not in details:
                    errmsg = f"You can't have strict_columns set to True and not list the columns in the details structure."
                    self._log.error(errmsg)
                    raise ValueError(errmsg)
                if type(details["index"]) is str:
                    index_column_name = details["index"]
                elif type(details["index"]) is dict:
                    if "name" in details["index"]:
                        index_column_name = details["index"]["name"]
                    else:
                        errmsg = f"Missing name in index dictionary."
                        self._log.error(errmsg)
                        raise ValueError(errmsg)
                else:
                    errmsg = f"Incorrect form of index."
                    self._log.error(errmsg)
                    raise ValueError(errmsg)
                    
                for column in df.columns:
                    if column not in details["columns"] and column!=index_column_name:
                        errmsg = f"DataFrame contains column: \"{column}\" which is not in the columns list of the specification and strict_columns is set to True."
                        self._log.error(errmsg)
                        raise ValueError(errmsg)
                    

        if "mapping" in details:
            
            for name, column in details["mapping"].items():
                self.update_name_column_map(column=column, name=name)


        for column in df.columns:
            # If column title is valid variable name, add it to the column name map
            if column not in self._column_name_map:
                if is_valid_variable_name(column):
                    self.update_name_column_map(name=column, column=column)
                else:
                    name = to_camel_case(column)
                    # Keep variable names as private
                    if column[0] == "_":
                        name = "_" + name

                    self._log.warning(f"Column \"{column}\" is not a valid variable name and there is no mapping entry to provide an alternative. Auto-generating a mapping entry \"{name}\" to provide a valid variable name to use as proxy for \"{column}\".")
                    if is_valid_variable_name(name):
                        self.update_name_column_map(name=name, column=column)
                    else:
                        errmsg = f"Column \"{column}\" is not a valid variable name. Tried autogenerating a camel case name \"{name}\" but it is also not valid. Please add a mapping entry to provide an alternative to use as proxy for \"{column}\"."
                        self._log.error(errmsg)
                        raise ValueError(errmsg)


                
        if "selector" in details:
            field = details["selector"]
            if type(field) is str:
                if field in df.columns:
                    self._selector = field 
                else:
                    if "set_selector" in details:
                        df[field] = details["set_selector"]
                    self._selector = field 
                    self._log.warning(f"No selector column \"{field}\" found in data frame.")
            elif type(field) is dict:
                if "name" in field:
                    if renderable(field):
                        column  = self._index_from_renderable(df, **field)
                    elif "source" in field and "regexp" in field:
                        column = self._series_from_regexp_of_field(df, **field)

                    cname = field["name"]
                    df[cname] = column
                    if cname not in self._column_name_map:
                        if is_valid_variable_name(cname):
                            self.update_name_column_map(column=cname, name=cname)
                        else:
                            errmsg = f"Column \"{cname}\" is not a valid variable name and there is no mapping entry to provide an alternative. Please add a mapping entry to provide a valid variable name to use as proxy for \"{cname}\"."
                            self._log.error(errmsg)
                            raise ValueError(errmsg)
                    self._selector = cname
                else:
                    self._log.warning(f"No \"name\" associated with selector entry.")
        
        if "index" in details:            
            field = details["index"]
            if type(field) is str:
                index_column_name = details["index"]
                
            elif type(field) is dict: # Index is created from existing columns
                if "name" not in field:
                    field["name"] = "index"
                if renderable(field):
                    column = self._index_from_renderable(df, **field)
                elif "source" in field and "regexp" in field:
                    column = self._series_from_regexp_of_field(df, **field)

                cname = field["name"]
                df[cname] = column
                if cname not in self._column_name_map:
                    if is_valid_variable_name(cname):
                        self.update_name_column_map(column=cname, name=cname)
                    else:
                        errmsg = f"Column \"{cname}\" is not a valid variable name and there is no mapping entry to provide an alternative. Please add a mapping entry to provide a valid variable name to use as proxy for \"{cname}\"."
                        self._log.error(errmsg)
                        raise ValueError(errmsg)
                index_column_name = field["name"]

            
        if index_column_name in df.columns:
            df.set_index(df[index_column_name], inplace=True)
            del df[index_column_name]


            
        if "fields" in details and details["fields"] is not None:
            for field in details["fields"]:
                if "name" in field:
                    if renderable(field):
                        column = self._column_from_renderable(df, **field)

                    elif "source" in field and "regexp" in field:
                        column = self._series_from_regexp_of_field(df, **field)
                        
                    elif "value" in field:
                        column = self._series_from_value(df, **field)
                    else:
                        self._log.warning(f"Missing \"source\" or \"regexp\" (for regular expression derived fields) or \"value\", \"liquid\", \"display\", (for renderable fields) in fields.")
                        
                    cname = field["name"]
                    df[cname] = column
                    if cname not in self._column_name_map:
                        if is_valid_variable_name(cname):
                            self.update_name_column_map(column=cname, name=cname)
                        else:
                            errmsg = f"Column \"{cname}\" is not a valid variable name and there is no mapping entry to provide an alternative. Please add a mapping entry to provide a valid variable name to use as proxy for \"{cname}\"."
                            self._log.error(errmsg)
                            raise ValueError(errmsg)
                    
                else:
                    self._log.warning(f"No \"name\" associated with field entry.")

        # If it's a series post-process by creating entries field.
        if "series" in details and details["series"]:
            """The data frame is a series (with multiple identical indices)"""
            mapping = self._default_mapping()
            # Make sure there's an entries entry in default mapping
            if "entries" not in mapping:
                mapping["entries"] = "entries" # Covers series entries.
            else:
                self._log.warning(f"Existing \"entries\" field in default mapping when incorporating a series.")
                
            self._log.info(f"Augmenting default mapping with an \"entries\" field for accessing series.")
            self._settings["mapping"] = mapping
            
            df[index_column_name] = df.index
            indexcol = list(set(df[index_column_name]))
            index = pd.Index(range(len(indexcol)))
            # selector_column_name = details["selector"]
            # selectorcol = list(set(df[selector_column_name]))
            # selector = pd.Index(range(len(selectorcol)))
            newdf = pd.DataFrame(index=index, columns=[index_column_name, "entries"])
            newdf[index_column_name] = indexcol
            newdetails = details.copy()
            del newdetails["series"]
            for ind in range(len(indexcol)):
                entries = []
                index_name = indexcol[ind]
                num_sub_entries = (df.index==index_name).sum()
                if num_sub_entries > 1:
                    sub_entries = []
                    for key, entry in df.loc[index_name].iterrows():
                        sub_entries.append(remove_nan(entry.to_dict()))
                        #entry = remove_nan(df.loc[index_name].to_dict(orient="list"))
                else:
                    sub_entries = [remove_nan(df.loc[index_name].to_dict())]
                    # Use the mapping to translate entry names.
                for entry in sub_entries:
                    map_entry = entry.copy()
                    del map_entry[index_column_name]

                    for key, key2 in mapping.items():
                        if key2 in entry:
                            map_entry[key] = entry[key2]
                            del map_entry[key2]
                    entries.append(map_entry)
                newdf.at[ind, "entries"] = entries
                newdf.at[ind, index_column_name] = indexcol[ind]
                                 
            if "fields" in details:
                """Fields have already been resolved."""
                del newdetails["fields"]
            if "selector" in details:
                del newdetails["selector"]
                
            newdetails["index"] = index_column_name
            return self._finalize_df(newdf, newdetails)
                    
        return df

    def to_score(self):
        if self._writedata is not None:
            return len(self._writedata.index)
        else:
            return 0

    def scored(self):
        if "scored" in self._settings:
            if self._writedata is not None and self._settings["scored"]["field"] in self._writedata.columns:
                return self._writedata[self._settings["scored"]["field"]].count()
            else:
                return 0


    def _update_type(self, df, column, value):
        """Update the type of a given column according to a value passed."""
        coltype = df.dtypes[column]
        if is_numeric_dtype(coltype) and is_string_dtype(type(value)):
            self._log.warning(f"Changing column \"{column}\" type to 'object' due to string input.")
            df[column] = df[column].astype("object")
        if is_numeric_dtype(coltype) and is_bool_dtype(type(value)):
            self._log.warning(f"Changing column \"{column}\" type to 'object' due to bool input.")
            df[column] = df[column].astype("boolean")

        
