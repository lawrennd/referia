import os

import re

import pandas as pd

import datetime

from pandas.api.types import is_string_dtype, is_numeric_dtype, is_bool_dtype

from lynguine.log import Logger
from lynguine.config.context import Context
from lynguine import access
from lynguine.assess import data
from ..assess import compute # move to lynguine.assess??
from lynguine.util.misc import to_camel_case, remove_nan, is_valid_var

from ..config.interface import Interface
from ..assess.compute import Compute

from ..util.misc import renderable


cntxt = Context()
log = Logger(
    name=__name__,
    level=cntxt["logging"]["level"],
    filename=cntxt["logging"]["filename"],
)


def empty(val):
    """
    Is a value empty?

    :param val: The value to be tested.
    :type val: object
    :return: True if the value is empty.
    :rtype: bool
    """
    
    return pd.isna(val) or val==""


def automapping(columns):
    """
    Generate dictionary of mapping between variable names and column names.

    :param columns: The list of column names.
    :type columns: list
    :return: The dictionary of mapping between variable names and column names.
    :rtype: dict
    """
    mapping = {}
    for column in columns:
        field = to_camel_case(column)
        mapping[field] = column
    return mapping

class CustomDataFrame(data.CustomDataFrame):
    """Class to hold merged data flows together perform operations on them."""
    def __init__(self, data=None, colspecs=None, index=None, column=None, selector=None, subindex=None, compute=None, interface=None):

        # Call the parent class with data, colspecs, index, column, selector
        super().__init__(data=data, colspecs=colspecs, index=index, column=column, selector=selector, subindex=subindex, compute=compute, interface=interface)
        self.augment = False

                        
    @property
    def _data(self):
        """
        This property recreates the original structure of data storage for referia where data was stored under _data not _d.
        """
        if len(self._d)>0:
            if "data" in self._d:
                # Data that is input (not for writing to)
                return self._d["data"]
            raise ValueError(f"There is no \"data\" key in self._d. Keys are \"{self._d.keys()}\"")
        raise ValueError("There is no data in self._d when calling _data.")

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
                
    def _augment_global_consts(self, configs, suffix=''):
        """
        Augment the globals by joining the two series together.

        :param configs: The configurations for the globals.
        :type configs: list
        :param suffix: The suffix to be added to the column names.
        :type suffix: str
        :return: None
        """
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
                            if is_valid_var(cname):
                                self.update_name_column_map(column=cname, name=cname)
                else:
                    errmsg = f"In global_consts a \"local\" specification must contain a dictionary of fields and values."
                    log.error(errmsg)
                    raise ValueError(errmsg)
            else:

                df = self._finalize_df(*access.io.globals_data(conf, pd.Index([index_row], name="index")), strict_columns=True)
                ds = df.loc[index_row]

            if self._global_consts is None:
                self._global_consts = ds
            else:
                if self._global_consts.name != ds.name:
                    self._global_consts.name += "_" + ds.name
                    ds.name = self._global_consts.name
                self._global_consts = pd.DataFrame(self._global_consts).T.join(pd.DataFrame(ds).T, rsuffix=rsuffix).loc[ds.name]
                    
    def _augment_data(self, configs, how="left", suffix='', concat=False, axis=0):
        """
        Augment the data by joining or concatenating the new values.

        :param configs: The configurations for the data.
        :type configs: list
        :param how: The type of join to be performed.
        :type how: str
        :param suffix: The suffix to be added to the column names.
        :type suffix: str
        :param concat: Whether to concatenate the data.
        :type concat: bool
        :param axis: The axis to concatenate the data on.
        :type axis: int
        :return: None
        """
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
                            if is_valid_var(cname):
                                self.update_name_column_map(column=cname, name=cname)
                else:
                    errmsg = "\"local\" specified in config but not in form of a dictionary."
                    log.error(errmsg)
                    raise ValueError(errmsg)
            else:
                df = self._finalize_df(*access.io.read_data(conf))
                    
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
                log.error(errmsg)
                raise ValueError(errmsg)

    def _remove_index_duplicates(self):
        """
        Rename the index of any duplicates

        :return: None
        """
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
        """
        Load in the primary data source as a data frame.

        :return: None
        """
        # Augment the data with default augmentation as "outer"
        if "allocation" in self.interface:
            self._augment_data(self.interface["allocation"], how="outer", concat=True, axis=0)
            self._remove_index_duplicates()
        else:
            errmsg = f"No \"allocation\" field in config file."
            log.error(errmsg)
            raise ValueError(f"No \"allocation\" field in config file.")
            
    def _load_additional(self):
        """
        Load in the additional data sources as data frames.

        :return: None
        """
        # Augment the data with default augmentation as "inner"
        if "additional" in self.interface:
            self._augment_data(self.interface["additional"], how="inner", concat=False, suffix="_{joinNo}")

    def _load_globals(self):
        """Load in any global variables to a data series."""
        if "select" in self.interface["globals"]:
            index_row = self.interface["globals"]["select"]
        else:
            index_row = "globals"
            
        df = self._finalize_df(*access.io.globals_data(self.interface["globals"], pd.Index([index_row], name="index")), strict_columns=True)
        self._globals = df
        self._globals_index = index_row

    def _load_cache(self):
        """Load in any cached data to data frames."""
        df = self._finalize_df(*access.io.cache(self.interface["cache"], self.index), strict_columns=True)
        if df.index.is_unique:
            self._cache = df
        else:
            strindex = pd.Series([str(ind) for ind in df.index])
            duplicates = ', '.join(strindex[df.index.duplicated()])
            errmsg = f"The index for the cache must be unique. Index \"{duplicates}\" is/are duplicated."
            log.error(errmsg)
            raise ValueError(errmsg)
        
    def _load_scores(self):
        """Load in the score data to data frames."""
        df = self._finalize_df(*access.io.scores(self.interface["scores"], self.index))
        if df.index.is_unique:
            self._writedata = df
        else:
            strindex = pd.Series([str(ind) for ind in df.index])
            duplicates = ', '.join(strindex[df.index.duplicated()])
            errmsg = f"The index for writedata must be unique. Index \"{duplicates}\" is/are duplicated."
            log.error(errmsg)
            raise ValueError(errmsg)

    def _load_series(self):
        """Load in the series data to data frames."""
        if "selector" not in self.interface["series"]:
            log.error(errmsg)
            errmsg = f"A series entry must have a \"selector\" column."
            raise ValueError(errmsg)
        self._writeseries = self._finalize_df(*access.io.series(self.interface["series"], self.index))
        selector = self.interface["series"]["selector"]
        if selector not in self._writeseries.columns:
            self._writeseries[selector] = None
            
        self.sort_series()

    def sort_series(self):
        """Sort the series by the column specified."""
        if "series" in self.interface:
            series = self.interface["series"]
        else:
            return
        if "sortby" in series and "field" in series["sortby"] and series["sortby"]["field"] in self._writeseries:
            if "ascending" in series["sortby"]:
                ascending = series["sortby"]["ascending"]
            else:
                ascending=True
            field=series["sortby"]["field"]
            log.debug(f"Sorting series by \"{field}\"")
            self._writeseries.sort_values(by=field, ascending=ascending, inplace=True)

    # def load_input_flows(self):
    #     """
    #     Load the input flows specified in the _referia.yml file.

    #     :return: None
    #     """
    #     self._load_allocation()
    #     if "additional" in self.interface:
    #         log.debug("Joining allocation and additional information.")
    #         self._load_additional()

    #     # If sorting is requested do it here.
    #     self.sort_data()
    #     self._load_global_consts()

    # def _load_global_consts(self):
    #     """Load constants from the _referia.yml file."""
    #     if "global_consts" in self.interface:
    #         self._augment_global_consts(self.interface["global_consts"])
                    
        
    # def sort_data(self):
    #     if "sortby" in self.interface and "field" in self.interface["sortby"] and self.interface["sortby"]["field"] in self.columns:
    #         if "ascending" in self.interface["sortby"]:
    #             ascending = self.interface["sortby"]["ascending"]
    #         else:
    #             ascending=True
    #         field=self.interface["sortby"]["field"]
    #         log.debug(f"Sorting by \"{field}\"")
    #         self.sort_values(by=field, ascending=ascending, inplace=True)

    # def load_output_flows(self):
    #     """
    #     Load the output flows data specified in the _referia.yml file. 
    #     Different output flows are listed in the configuration file under "globals", "cache", "scores", "series".
    #     Those listed under "globals" are constants that don't change when the index changes. 
    #     Those specified under "cache" are variables that can be cached and used in liquid templates or comptue functions but are assumed as not needed to be stored.
    #     Those specified under "scores" are the variables that the user will want to store.
    #     Those specified under "series" are variabels that the user is storing, but there are multiple entries for each index.

    #     """
    #     if "globals" in self.interface:
    #         self._globals = None
    #         self._load_globals()
    #     if "cache" in self.interface:
    #         self._cache = None
    #         self._load_cache()
    #     if "scores" in self.interface:
    #         self._writedata = None
    #         self._load_scores()
    #     if "series" in self.interface:
    #         self._writeseries = None
    #         self._load_series()

    # def load_flows(self):
    #     """Load the input and output flows."""
    #     autocache = self.autocache
    #     self.autocache = False
    #     self.load_input_flows()
    #     self.load_output_flows()
    #     self.augment = True
    #     self.preprocess()
    #     self.augment = False
    #     self.autocache = autocache
        

        
    def set_index(self, value : str) -> None:
        """
        Index setter

        :param value: The index to be set.
        :type value: str
        :return: None
        """
        
        # If index has changed, run post computes (computes that take place after review).
        # post-computes are run on the index we're changing from
        if self.get_index() is not None and value != self.get_index():
            log.debug(f"Calling post-compute on index \"{self.get_index()}\".")
            self.compute_post()
        
        # Call parent to set index
        orig_index = self.get_index()
        super().set_index(value)

        # If index has changed, run pre computes (computes that take place before review).
        # pre-computes are run on the index we're changing to
        if orig_index is None or self.get_index() != orig_index:
            log.debug(f"Calling pre-compute on index \"{self.get_index()}\".")
            self.compute_pre()
                
        # If index has changed, check if there is a subseries, if so, use top subindex, if not create a row.
        self.check_or_set_subseries()
            
            

    def check_or_set_subseries(self) -> None:
        """
        Check if there is a sub-series if so, use top subindex, if not create a row.
        """
        if self._writeseries is not None:
            subindices = self.get_subseries()
            if len(subindices) > 0:
                subindex = self.get_subindex()
                selector = self.get_selector()
                if subindex is None or not subindex in subindices[selector]:
                    self.set_subindex(subindices[selector][0])
            else:
                self.add_series_row(self._index)
                


    def set_subindex(self, subindex : str) -> None:
        """
        Subindex setter

        :param subindex: The subindex to be set.
        :type subindex: str
        :return: None
        """
        if subindex is None:
            self._subindex = None
            log.debug(f"Subindex set to None.")
            return

        if self._writeseries is not None and subindex not in self.get_subindices():
            index = self.get_index()
            errmsg = f"Subindex \"{subindex}\" under \"{index}\" not available in current series."
            log.error(errmsg)
            raise ValueError(errmsg)
        else:
            self._subindex=subindex
            log.debug(f"Subindex \"{subindex}\" selected.")


    def get_index(self) -> str:
        """
        Index getter

        :return: The index.
        :rtype: str
        """
        _index = super().get_index()
        if _index is None and len(self.index)>0:
            log.debug(f"No index set, using first index of data.")
            _index = self.index[0]
            self.set_index(_index)
        return _index

    def _strict_columns(self, group):
        if "strict_columns" in self.interface:
            return self.interface["strict_columns"]
        elif "strict_columns" in self.interface[group]:
            return self.interface[group]["strict_columns"]
        elif group=="cache" or group=="globals":
            return True
        else:
            return False # historic default, should shift this to True.

    def preprocess(self):
        """Run any preprocessing computations."""
        if self.compute is not None:
            self.compute.preprocess(data=self)

    def compute_pre(self):
        """Run pre-computation on the index."""
        if self.compute is not None:
            self.compute.run_all(data=self, pre=True)
        
    def compute_post(self):
        """Run post-computation on the index."""
        if self.compute is not None:
            self.compute.run_all(data=self, post=True)

    def compute_append(index, row):
        """Run computation for an appended row."""
        if self.compute is not None:
            self.compute.run_all(data=self, df=row, index=index, pre=True)
        

    def set_selector(self, column):
        """Set which column of the series is to be used for selection."""
        # Set to None to indicate that self._writedata is correct place for recording.
        if column is None:
            log.warning(f"No column selected for selector, setting to \"None\".")
            self._selector = None
            return

        if column not in self.get_selectors():
            log.info(f"Column \"{column}\" of chosen for selection not in Data._writeseries ... adding.")
            self.add_column(column)
            self.set_selector(column)
        else:
            self._selector = column
            log.debug(f"Column \"{column}\" of Data._writeseries selected for selection.")
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
            log.debug(f"No subindex set, using first entry of portion of Data._writeseries indexed by \"{index}\".")
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


    def set_series_value(self, value, column):
        """Set a value in the write series data frame"""
        if not self.ismutable(column):
            log.warning(f"Warning attempting to write to non mutable column \"{column}\".")

        if not self.isseries(column):
            self.add_series_column(column)

        self._update_type(self._writeseries, column, value)

    

    # def set_value(self, value):
    #     """Set the value of the current cell under focus."""
    #     column = self.get_column()
    #     if column is None:
    #         raise KeyError(f"Warning attempting to write a value {value} when column is not set.")
    #     if self._globals is not None and column in self._globals.index:
    #         self._globals.at[self._globals_index, column] = value
    #         return

        
    #     index = self.get_index()
    #     selector = self.get_selector()
    #     subindex = self.get_subindex()
    #     # If trying to set a numeric valued column's entry to a string, set the type of column to object.
    #     if not self.ismutable(column):
    #         raise KeyError(f"Attempting to write to column \"{column}\" which is read only.")
        
    #     col_source = self._col_source(column)
    #     if not self.isglobal(column):
    #         self._d[col_source].at[index, column] = value
    #     elif not self.isseries(column):
    #         self._d[col_source].at[column] = value
    #     else:
    #         self._update_type(self._d[col_source], column, value)
    #         self._d[col_source].loc[
    #             self._d[col_source].index.isin([index])
    #             & (self._d[col_source][selector]==subindex).values,
    #             column
    #         ] = value

    def drop_column(self, column_name):
        if column_name not in self.columns:
            raise KeyError(f"No column \"{column}\" in data object.")           
        elif not self.ismutable(column_name):
            raise KeyError(f"Attempting to drop column \"{column}\" in which is read only.")
        for typ, data in self._d.items():
            if not self.isglobal(column_name):
                if column_name in data.columns:
                    log.debug(f"Dropping column \"{column_name}\" from _{typ}.")
                    self._d[typ].drop(column_name, axis=1, inplace=True)
            else:
                if column_name in data.index:
                    log.debug(f"Dropping value \"{column_name}\" from _{typ}.")
                    self._d[typ].drop(column_name, inplace=True)

    def filter_rows(self, condition):
        for typ in self._d:
            if not self.isglobal(typ):
                 self._d[typ] = self._d[typ][condition]
           
    def get_shape(self):
        return self.to_pandas().shape
            
    def get_value_by_element(self, element):
        """Return the value of an element from the under focus cell (e.g. a list entry or a dict entry)."""
        value = self.get_value()
        if type(element) is int and type(value) is not list:
            log.warning(f"Attempt to get element of a non list entry with an element \"{element}\" that is an integer.")
            return None
        elif type(element) is str and type(value) is not dict:
            log.warning(f"Attempt to get element of a non dictionary entry with an element \"{element}\" that is a string.")
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
            log.warning("Value wasn't a list and element was set as integer, so converting to a list.")
            orig_value = [orig_value]
            
        elif type(element) is str and type(orig_value) is not dict:
            log.warning("Value wasn't a dictionary and element was set as string, so converting to a dictionary.")
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
        """
        Return a pd.Series containing all the values in a column.
        """
        column = self.get_column()
        if column == None:
            return None
        index = self.get_index()

        if self.isseries(column):
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
        # Ordering here dictates the priority of selection, global constants, then globals, then series, then writedata, then cache then data.
        
        column = self.get_column()
        if column == "_":
            return None
        if column == None:
            return None
        return super().get_value()
        # if self._global_consts is not None and column in self._global_consts.index:
        #     return self._global_consts[column]

        # if self._globals is not None and column in self._globals.columns:
        #     return self._globals.at[self._globals_index, column]

        # index = self.get_index()
        # if index == None:
        #     return None
        # selector = self.get_selector()
        # subindex = self.get_subindex()
        # # Prioritise returning from the _writeseries then the _writedata structure first.
        # if self._selector is not None and self._writeseries is not None and column in self._writeseries.columns:
        #     if subindex is not None:
        #         indexer = (self._writeseries.index.isin([index])
        #                    & (self._writeseries[selector]==subindex).values)
        #         if indexer.sum()>0:
        #             return self._writeseries.loc[indexer, column].iloc[0]
        #         else:
        #             log.warning(f"No data available with this subindex and index , returning None.")
        #     else:
        #         log.warning(f"No subindex selected, returning None.")
        # elif self._writedata is not None and column in self._writedata.columns:
        #     if index in self._data.index and not index in self._writedata.index:
        #         # If index isn't created in write data yet, return None.
        #         return None
        #     try:
        #         return self._writedata.at[index, column]
        #     except KeyError as err:
        #         raise KeyError(f"Cannot find index: \"{index}\" and column: \"{column}\" in _writedata.") from err
        # elif self._cache is not None and column in self._cache.columns:
        #     if index in self._data.index and not index in self._cache.index:
        #         # If index isn't created in write data yet, return None.
        #         return None
        #     try:
        #         return self._cache.at[index, column]
        #     except KeyError as err:
        #         raise KeyError(f"Cannot find index: \"{index}\" and column: \"{column}\" in _cache.") from err
        # elif self._data is not None and column in self._data.columns:
        #     try:
        #         return self._data.at[index, column]
        #     except KeyError as err:
        #         raise KeyError(f"Cannot find index: \"{index}\" and column: \"{column}\" in _data.") from err
        # elif self._data is not None and column==self._data.index.name:
        #     return index
        # else:
        #     log.warning(f"\"{column}\" not selected in self._writeseries or in self._writedata or in self._cache or in self._data returning \"None\"")
        #     return None

    def add_column(self, column, data=None):
        """
        Add a column to the data structure.

        :param column: The name of the column to add.
        :type column: str
        :param data: The data to add to the column.
        :type data: pd.Series
        """
        
        if column in self.columns:
            errmsg = f"Was requested to add column \"{column}\" but it already exists in data."
            log.error(errmsg)
            raise ValueError(errmsg)
        
        if not self.mutable:
            errmsg = f"This is not a mutable object, so there is no data structure to add the column \"{column}\" to."
            log.error(errmsg)
            raise ValueError(errmsg)

        if self._strict_columns and not self.autocache:
            errmsg = f"Cannot add column \"{column}\" to data due to strict_columns being set and/or autocache being switched off."
            log.error(errmsg)
            raise ValueError(errmsg)
            
        
        if "series" in self._d:
            if not self._strict_columns("series"):
                log.info(f"\"{column}\" not in writeseries columns ... adding.")
                self._d["series"][column] = data
                return
        # TK, need to move away from self._writedata here.
        if self._writedata is not None and column not in self._writedata.columns:
            if not self._strict_columns("scores"):
                log.info(f"\"{column}\" not in write columns ... adding.")
                self._writedata[column] = data
                return
        errmsg = f"Cannot add column \"{column}\" to either scores or series due to strict_columns being set and/or series or scores not being present."
        log.error(errmsg)
        raise ValueError(errmsg)

    def set_dtype(self, column, dtype):
        """Set a Data._writedata column to the given data type."""
        if self._writedata is not None and column in self._writedata.columns:
            log.debug(f"\"{column}\" being set to \"{dtype}\".")
            self._writedata[column] = self._writedata[column].astype(dtype)
        if self._writeseries is not None and column in self._writeseries.columns:
            log.debug(f"\"{column}\" being set to \"{dtype}\".")
            self._writeseries[column] = self._writeseries[column].astype(dtype)

    def _append_row(self, df, index):
        row = pd.DataFrame(columns=df.columns, index=pd.Index([index], name=df.index.name))
        # Handle the fact that the index is stored as a column also
        if df.index.name in row:
            row[df.index.name] = index
        if self.mutable:
            # Only precompute if something to write to
            self.compute_append(index=index, row=row)
        # was return df.append(row) before append deprecation
        return pd.concat([df, row])

    def add_row(self, index=None, subindex=None):
        """Add a row with a given index (and optionally subindex) to the data structure."""
        if index is None:
            index = self.get_index()
        if index is None:
            log.warning("No index set to add row to.")
            return
        selector = self.get_selector()
        for typ, data in self._d.items():
            if typ in self.types["output"] or typ in self.types["cache"]:
                data = self._append_row(data, index)
                log.info(f"\"{index}\" added as row in Data._writedata.")
                self.set_index(index)
                return
        log.warning("No mutable data found to add row with index \"{index}\" to.")


    def add_series_row(self, index=None):
        """Add a row to the series."""
        if index is None:
            index = self.get_index()
        self._writeseries = self._append_row(self._writeseries, index)
        log.info(f"\"{index}\" added subseries row in Data._writeseries.")


    def add_series_column(self, column):
        """Add a column to the data series"""
        if column not in self._writeseries.columns:
            log.info(f"\"{column}\" not in series columns ... adding.")
            self._writeseries[column] = None
        else:
            log.warning(f"\"{column}\" requested to be added to series data but already exists.")

    def _column_from_renderable(self, df, **kwargs):
        """Create a column from a renderable field."""
        return self._series_from_renderable(df, is_index=False, **kwargs)


    def _index_from_renderable(self, df, **kwargs):
        """
        Create an index from a renderable field.

        :param df: The data frame to create the index from.
        :type df: pd.DataFrame
        :param kwargs: The mapping to use to populate the index.
        :type kwargs: dict
        :returns: The index created from the renderable field.
        :rtype: pd.Index
        """
        return self._series_from_renderable(df, is_index=True, **kwargs)

    def _series_from_value(self, df, value, name, **kwargs):
        """
        Create a series from a given value.

        """
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
                #    log.error(errmsg)
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
                    log.warning(f"Multiple regular expression matches in \"{regexp}\".")
                series[index] = match.group(1)
            else:
                log.warning(f"No match of regular expression \"{regexp}\" to \"{source}\".")
        return series
    
    def _finalize_df(self, df : "CustomDataFrame", interface  : Interface, strict_columns : bool = None) -> "CustomDataFrame":
        """
        This function augments the raw data and sets the index of the data frame.
        :param df: The data frame to be augmented.
        :param interface: The interface of the data frame.
        :param strict_columns: Whether to enforce strict columns.
        :return: The augmented data frame.
        """
        """for field in dtypes:
            if dtypes[field] is str_type:
                data[field].fillna("", inplace=True)"""
        #if "index" not in interface:
        #    errmsg = "Missing index field in data frame specification in _referia.yml"
        #    log.error(errmsg)
        #    raise ValueError(errmsg)
        #if "index" not in interface:
        #    interface["index"] = df.index.name

        if strict_columns is None:
            if "strict_columns" in interface and not interface["strict_columns"]:
                strict_columns = False
            elif self.interface is not None and "strict_columns" in self.interface and not self.interface["strict_columns"]:
                strict_columns = False
            else:
                strict_columns = True
                

        if strict_columns: # check that index is provided
            # TK: This should happen when interface is loaded and converted
            if isinstance(interface["index"],dict): # Legacy: Index is built through constructing a column
                if not "name" in interface["index"]:
                    errmsg = f"Missing name in index dictionary."
                    log.error(errmsg)
                    raise ValueError(errmsg)
                if "field" in interface:
                    interface["field"] += [interface["index"]]
                else:
                    interface["field"] = [interface["index"]]
                interface["index"] = interface["index"]["name"]
            elif not isinstance(interface["index"],str):
                errmsg = f"Incorrect form of index."
                log.error(errmsg)
                raise ValueError(errmsg)
        df = super()._finalize_df(df, interface, strict_columns)

        # if "selector" in interface:
        #     if isinstance(interface["selector"], str):
        #         self.set_selector(interface["selector"])
        #     else:
        #         errmsg = f'"selector" should be a string in interface.'
        #         log.error(errmsg)
        #         raise ValueError(errmsg)
        
        if "selector" in interface:
            field = interface["selector"]
            if type(field) is str:
                if field in df.columns:
                    self._selector = field 
                else:
                    if "set_selector" in interface:
                        df[field] = interface["set_selector"]
                    self._selector = field 
                    log.warning(f"No selector column \"{field}\" found in data frame.")
            elif type(field) is dict:
                if "name" in field:
                    if renderable(field):
                        column  = self._index_from_renderable(df, **field)
                    elif "source" in field and "regexp" in field:
                        column = self._series_from_regexp_of_field(df, **field)

                    cname = field["name"]
                    df[cname] = column
                    if cname not in self._column_name_map:
                        if is_valid_var(cname):
                            self.update_name_column_map(column=cname, name=cname)
                        else:
                            errmsg = f"Column \"{cname}\" is not a valid variable name and there is no mapping entry to provide an alternative. Please add a mapping entry to provide a valid variable name to use as proxy for \"{cname}\"."
                            log.error(errmsg)
                            raise ValueError(errmsg)
                    self._selector = cname
                else:
                    log.warning(f"No \"name\" associated with selector entry.")
        if "index" in interface:            
            field = interface["index"]
            if type(field) is str:
                index_column_name = interface["index"]
                
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
                    if is_valid_var(cname):
                        self.update_name_column_map(column=cname, name=cname)
                    else:
                        errmsg = f"Column \"{cname}\" is not a valid variable name and there is no mapping entry to provide an alternative. Please add a mapping entry to provide a valid variable name to use as proxy for \"{cname}\"."
                        log.error(errmsg)
                        raise ValueError(errmsg)
                index_column_name = field["name"]

            
        if index_column_name in df.columns:
            df.set_index(df[index_column_name], inplace=True)
            del df[index_column_name]


            
        if "fields" in interface and interface["fields"] is not None:
            for field in interface["fields"]:
                if "name" in field:
                    if renderable(field):
                        column = self._column_from_renderable(df, **field)

                    elif "source" in field and "regexp" in field:
                        column = self._series_from_regexp_of_field(df, **field)
                        
                    elif "value" in field:
                        column = self._series_from_value(df, **field)
                    else:
                        log.warning(f"Missing \"source\" or \"regexp\" (for regular expression derived fields) or \"value\", \"liquid\", \"display\", (for renderable fields) in fields.")
                        
                    cname = field["name"]
                    df[cname] = column
                    if cname not in self._column_name_map:
                        if is_valid_var(cname):
                            self.update_name_column_map(column=cname, name=cname)
                        else:
                            errmsg = f"Column \"{cname}\" is not a valid variable name and there is no mapping entry to provide an alternative. Please add a mapping entry to provide a valid variable name to use as proxy for \"{cname}\"."
                            log.error(errmsg)
                            raise ValueError(errmsg)
                    
                else:
                    log.warning(f"No \"name\" associated with field entry.")

        # If it's a series post-process by creating entries field.
        if "series" in interface and interface["series"]:
            """The data frame is a series (with multiple identical indices)"""
            mapping = self._default_mapping()
            # Make sure there's an entries entry in default mapping
            if "entries" not in mapping:
                mapping["entries"] = "entries" # Covers series entries.
            else:
                log.warning(f"Existing \"entries\" field in default mapping when incorporating a series.")
                
            log.info(f"Augmenting default mapping with an \"entries\" field for accessing series.")
            self.interface["mapping"] = mapping
            
            df[index_column_name] = df.index
            indexcol = list(set(df[index_column_name]))
            index = pd.Index(range(len(indexcol)))
            # selector_column_name = interface["selector"]
            # selectorcol = list(set(df[selector_column_name]))
            # selector = pd.Index(range(len(selectorcol)))
            newdf = pd.DataFrame(index=index, columns=[index_column_name, "entries"])
            newdf[index_column_name] = indexcol
            newinterface = interface.copy()
            del newinterface["series"]
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
                                 
            if "fields" in interface:
                """Fields have already been resolved."""
                del newinterface["fields"]
            if "selector" in interface:
                del newinterface["selector"]
                
            newinterface["index"] = index_column_name
            return self._finalize_df(newdf, newinterface)
                    
        return df

    def to_score(self):
        """
        Return the total number of entries to be scored.

        :return: The total number of entries to be scored.
        :rtype: int
        """
        if "output" in self._d:
            return len(self._d["output"].index)
        else:
            log.debug(f"No output flow in interface data types are \"{', '.join(self._d.keys())}\".")
            return 0

    def scored(self) -> int:
        """
        Return the number of scored entries in the data frame.

        :return: The number of scored entries.
        :rtype: int
        """
        
        if "scored" in self.interface:
            if "output" in self._d is not None and self.interface["scored"]["field"] in self._d["output"].columns:
                return self._d["output"][self.interface["scored"]["field"]].count()
            else:
                if "output" in self._d:
                    log.debug(f"No \"scored:field\" in output flow.")
                else:
                    log.debug(f"No output flow in interface types are \"{', '.join(self._d.keys())}\".")
                return 0
        log.debug("No \"scored:field\" in interface.") 

    def _update_type(self, df : pd.DataFrame, column : str, value) -> None:
        """
        Update the type of a given column according to a value passed.

        :param df: The data frame to update.
        :type df: pd.DataFrame
        :param column: The column to update.
        :type column: str
        :param value: The value whose type the column should be updated with.
        :type value: Any
        """
        coltype = df.dtypes[column]
        if is_numeric_dtype(coltype) and is_string_dtype(type(value)):
            log.warning(f"Changing column \"{column}\" type to 'object' due to string input.")
            df[column] = df[column].astype("object")
        if is_numeric_dtype(coltype) and is_bool_dtype(type(value)):
            log.warning(f"Changing column \"{column}\" type to 'object' due to bool input.")
            df[column] = df[column].astype("boolean")

           
