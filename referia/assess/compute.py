import os
import datetime
import pandas as pd

from ..config.interface import Interface
import ndlpy as ndl

from ..util.misc import add_one_to_max, return_shortest, return_longest, identity

from ..util.text import word_count, text_summarizer, paragraph_split, list_lengths, named_entities, sentence_split, comment_list, pdf_extract_comments, render_liquid
from ..util.system import most_recent_screen_shot
from ..util.plot import bar_plot, histogram
from ..util.files import file_from_re, files_from_re

from ..exceptions import ComputeError

class Compute():
    def __init__(self, interface, data):
        """Initialize the compute object.

        :param data: The data object to be used.
        :type data: ndlpy.asses.data.CustomDataFrame
        :param user_file: The name of the user file to be used.
        :type user_file: str
        :param directory: The directory to be used.
        :type directory: str
        :return: None
        """

        self._data = data
        self._interface = interface
        self._cntxt = ndl.config.context.Context(name="referia")
           
        self._log = ndl.log.Logger(
            name=__name__,
            level=self._cntxt["logging"]["level"],
            filename=self._cntxt["logging"]["filename"],
            directory = self._interface._directory,
            
        )
        

        self._computes = {}
        for comptype in ["precompute", "compute", "postcompute"]:
            self._computes[comptype]=[]
            if comptype in self._interface:
                if type(self._interface[comptype]) is list:
                    computes = self._interface[comptype]
                else:
                    computes = [self._interface[comptype]]

                for compute in computes:
                    self._computes[comptype].append(
                        self.prep(compute)
                    )
        
    @classmethod
    def from_file(cls, data, user_file : str=None, directory : str=None) -> "Compute":
        """
        Return a compute object from a file.

        :param user_file: The name of the user file to be used.
        :type user_file: str
        :param directory: The directory to be used.
        :type directory: str
        :return: The compute object.
        :rtype: Compute
        """

        interface = Interface.from_file(user_file=user_file, directory=directory)
        data = data.from_interface(interface)
        return cls(interface, data)
        
    def prep(self, settings : dict ) -> dict:
        """
        Prepare a compute entry for use.

        :param settings: The settings to be used.
        :type settings: dict
        :return: The prepared compute entry.
        :rtype: dict

        """
        compute_prep = {
            "function": self.gcf_(function=settings["function"]),
            "args" : self.gca_(**settings),
            "refresh" : "refresh" in settings and settings["refresh"],
        }
        if "field" in settings:
            compute_prep["field"] = settings["field"]
        return compute_prep

            
    def copy_screen_capture(self) -> bytes:
        """
        Return an image of the most recent screenshot.

        :return: An image of the most recent screenshot.
        :rtype: bytes
        """
        filename = most_recent_screen_shot()
        with open(filename, 'rb') as file:
            image = file.read()
        return image

    def gca_(self, function, field=None, refresh=False, args={}, row_args={}, view_args={}, function_args={}, subseries_args={}, column_args={}):
        """
        Args generator for compute functions.

        :param function: The name of the function to be used.
        :type function: str
        :param field: The field to be used.
        :type field: str
        :param refresh: Whether to refresh the field.
        :type refresh: bool
        :param args: The arguments to be used.
        :type args: dict
        :param row_args: The row arguments to be used.
        :type row_args: dict
        :param view_args: The view arguments to be used.
        :type view_args: dict
        :param function_args: The function arguments to be used.
        :type function_args: dict
        :param subseries_args: The subseries arguments to be used.
        :type subseries_args: dict
        :param column_args: The column arguments to be used.
        :type column_args: dict
        :return: The arguments to be used.
        :rtype: dict
        """

        found_function = False
        for list_function in self._compute_functions_list():
            if list_function["name"] == function:
                found_function = True
                break
        if not found_function:
            errmsg = f"Function \"{function}\" not found in list_functions."
            self._log.error(errmsg)
            raise ValueError(errmsg)
        return {
            "subseries_args" : subseries_args,
            "column_args" : column_args,
            "row_args" : row_args,
            "view_args" : view_args,
            "function_args" : function_args,
            "args" : args,
            "default_args" : list_function["default_args"],
        }


    def gcf_(self, function):
        """
        Function generator for compute functions.

        :param function: The name of the function to be used.
        :type function: str
        :return: The function to be used.
        """
        found_function = False
        for list_function in self._compute_functions_list():
            if list_function["name"] == function:
                found_function = True
                break
        if not found_function:
            raise ValueError(f"Function \"{function}\" not found in list_functions.")

        def compute_function(args={}, subseries_args={}, column_args={}, row_args={}, view_args={}, function_args = {}, default_args={}):
            """
            Compute a function using arguments found in subseries (column of sub-series specified by value in dictionary), or columns (full column specified by value in dictionary) or the same row (value from row as specified in the dictionary).
            :param args: The arguments to be used.
            :type args: dict
            :param subseries_args: The subseries arguments to be used.
            :type subseries_args: dict
            :param column_args: The column arguments to be used.
            :type column_args: dict
            :param row_args: The row arguments to be used.
            :type row_args: dict
            :param view_args: The view arguments to be used.
            :type view_args: dict
            :param function_args: The function arguments to be used.
            :type function_args: dict
            :param default_args: The default arguments to be used.
            :type default_args: dict
            :return: The result of the computation.
            """

            kwargs = default_args.copy()
            kwargs.update(args)
            for key, value in function_args.items():
                kwargs[key] = self.gcf_(value)
            for key, column in column_args.items():
                if otherdf is None:
                    orig_col = self._data.get_column()
                    self._data.set_column(column)
                if key in kwargs:
                    self._log.warning(f"No key \"{key}\" already column_args found in kwargs.")
                kwargs[key] = self._data.get_column_values()
                self._data.set_column(orig_col)
                
            for key, column in subseries_args.items():
                orig_col = self._data.get_column()
                self._data.set_column(column)
                if key in kwargs:
                    self._log.warning(f"No key \"{key}\" from subseries_args already found in kwargs.")   
                kwargs[key] = self._data.get_subseries_values()
                self._data.set_column(orig_col)

            ## Arguments based on liquid, or format, or join.
            for key, view in view_args.items():
                orig_col = self._data.get_column()
                kwargs[key] = self._data.view_to_value(view)
                self._data.set_column(orig_col)
                
            for key, column in row_args.items():
                if key in kwargs:
                    self._log.warning(f"No key \"{key}\" from row_args already found in kwargs.")
                kwargs[key] = self._data.get_value_column(column)
            # kwargs.update(remove_nan(self._data.mapping(args)))
            self._log.debug(f"The keyword arguments for the compute function are {kwargs}.")
            return list_function["function"](**kwargs)

        compute_function.__name__ = list_function["name"]
        if "docstr" in list_function:
            compute_function.__doc__ = list_function["docstr"]
        return compute_function

    def run(self, compute, df=None, index=None, refresh=True):
        """
        Run the computation given in compute.

        :param compute: The compute to be run.
        :type compute: dict
        :param df: The data frame to be used.
        :type df: pandas.DataFrame or ndlpy.assess.data.CustomDataFrame
        :param index: The index to be used.
        :type index: object
        :param refresh: Whether to refresh the field.
        :type refresh: bool
        :return: The result of the computation.
        :rtype: object
        """
        
        multi_output = False
        fname = compute["function"].__name__
        fargs = compute["args"]
        if index is None:
            index = self._data.get_index()

        if "field" in compute:
            columns = compute["field"]
            if type(columns) is list:
                multi_output = True
            else:
                columns = [columns]
        else:
            columns = None

        # Determine which current values of field aren't set
        missing_vals = []
        if columns is not None:
            for column in columns:
                if df is None:
                    if column not in self._data.columns:
                        missing_vals.append(True)
                        continue
                else:
                    if column not in df.columns:
                        missing_vals.append(True)
                        continue
                if column == "_": # If the column is called "_" then ignore that argument
                    missing_vals.append(False)
                    continue
                if df is None:
                    val = self._data.get_value_column(column)
                else:
                    val = df.at[index, column]
                if type(val) is not list and pd.isna(val):
                    missing_vals.append(True)
                else:
                    missing_vals.append(False)

        if refresh or any(missing_vals) or columns is None:
            if columns is not None:
                self._log.debug(f"Running compute function \"{fname}\" storing in field(s) \"{columns}\" with index=\"{index}\" with refresh=\"{refresh}\" and arguments \"{fargs}\".")
            else:
                self._log.debug(f"Running compute function \"{fname}\" with no field(s) stored for index=\"{index}\" with refresh=\"{refresh}\" and arguments \"{fargs}\".")

            new_vals = compute["function"](**fargs)
        else:
            return

        if multi_output and type(new_vals) is not tuple:
            errmsg = f"Multiple columns provided for return values of \"{fname}\" but return value given is not a tuple."
            self._log.error(errmsg)
            raise ValueError(errmsg)
            
        if columns is None:
            return new_vals
        else:
            if multi_output:
                new_vals = [*new_vals]
            else:
                new_vals = [new_vals]
            for column, new_val, missing_val in zip(columns, new_vals, missing_vals):
                if column == "_":
                    continue
                if refresh or missing_val and self._data.ismutable(column):
                    self._log.debug(f"Setting column {column} in data structure to value {new_val} from compute.")
                    self._data.set_value_column(new_val, column)
  
    def preprocess(self):
        """
        Run all preprocess computations.

        :return: None
        """
        ##### Copied raw need to run on all elements.
        ## preprocess
        for op in ["preprocessor", "augmentor", "sorter"]:
            if op in self._interface["compute"]:
                computes = self._interface["compute"][op]
                if not isinstance(computes, list):
                    computes = [computes]
                for compute in computes:
                    compute_prep = self.prep(compute)
                    fargs = compute_prep["args"]
                    if "field" in compute:
                        self._data[compute["field"]] = compute_prep["function"](self._data, **fargs)
                    else:
                        compute_prep["function"](self._data, **fargs)
                        
        # Filter
        filt = pd.Series(True, index=self._data.index)
        if "filter" in self._interface["compute"]:
            computes = self._interface["compute"]["filter"]
            if not isinstance(computes, list):
                computes = [computes]    
                for compute in computes:
                    compute_prep = self.prep(compute)
                    fargs = compute_prep["args"]
                    newfilt = compute_prep["function"](self._data, **fargs)
                    filt = (filt & newfilt)
            self._data.filter_row(filt)
    
    def run_all(self, df=None, index=None, pre=False, post=False):
        """
        Run any computation elements on the data frame.

        :param df: The data frame to be used.
        :type df: pandas.DataFrame or ndlpy.assess.data.CustomDataFrame
        :param index: The index to be used.
        :type index: object
        :param pre: Whether to run precomputes.
        :type pre: bool
        :param post: Whether to run postcomputes.
        :type post: bool
        :return: None
        """

        self._log.debug(f"Running computes on index=\"{index}\" with pre=\"{pre}\" and post=\"{post}\"")
        computes = []
        if pre:
            computes += self._computes["precompute"]
        computes += self._computes["compute"]
        if post:
            computes += self._computes["postcompute"]
            
        for compute in computes:
            field = compute["field"]
            if self._data.ismutable(field):
                if compute["refresh"]:
                    self.run(compute, df, index, refresh=True)
                else:                    
                    self.run(compute, df, index, refresh=False)
            else:
                self._log.warning(f"Attempted to write to unmutable field \"{field}\"")
    

    def _compute_functions_list(self) -> list[dict]:
        """
        Return a list of compute functions.

        :return: A list of compute functions.
        :rtype: list
        """
        return  [
            {
                "name" : "liquid",
                "function" : render_liquid,
                "default_args" : {
                    "data" : self,
                },
                "docstr": "Render a liquid template.",
            },
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
                "function" : lambda values: max(values),
                "default_args" : {},
            },
            {
                "name" : "len",
                "function" : lambda values: len(values),
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
            {
                "name" : "file_from_re",
                "function" : file_from_re,
                "default_args": {
                },
                "docstr" : "Return the first file name that matches a given pattern.",
            },
            {
                "name" : "files_from_re",
                "function" : files_from_re,
                "default_args": {
                },
                "docstr" : "Return the list of file names that matches a given pattern.",
            },
            {
                "name" : "pdf_extract_comments",
                "function" : pdf_extract_comments,
                "default_args" : {
                },
                "docstr" : "Extract comments from a PDF file."
            },
            {
                "name" : "named_entities",
                "function" : named_entities,
                "default_args": {
                },
                "docstr" : "Return named entities from a given text.",
            },
            {
                "name" : "word_count",
                "function" : word_count,
                "default_args": {
                },
                "docstr" : "Return word count for a given text.",
            },
            {
                "name" : "return_longest",
                "function" : return_longest,
                "default_args": {
                },
                "docstr" : "Return the longest item in a list.",
            },
            {
                "name" : "return_shortest",
                "function" : return_shortest,
                "default_args": {
                },
                "docstr" : "Return the shortest item in a list.",
            },
            {
                "name" : "histogram",
                "function" : histogram,
                "default_args": {
                },
                "docstr" : "Create a histogram of a vector..",
            },
            {
                "name" : "identity",
                "function" : identity,
                "default_args": {
                },
                "docstr" : "Identity function for testing.",
            },
            {
                "name" : "most_recent_screen_shot",
                "function" : most_recent_screen_shot,
                "default_args": {
                },
                "docstr" : "Most recent screenshot's filename.",
            },
            {
                "name" : "text_summarizer",
                "function" : text_summarizer,
                "default_args": {
                },
                "docstr" : "Return a summary of given text.",
            },
            {
                "name" : "paragraph_split",
                "function" : paragraph_split,
                "default_args": {
                    "sep": "\n\n",
                },
                "docstr" : "Return a list from a text split into paragraphs.",
            },
            {
                "name" : "sentence_split",
                "function" : sentence_split,
                "default_args": {
                },
                "docstr" : "Return a list from a text split into sentences.",
            },
            {
                "name" : "comment_list",
                "function" : comment_list,
                "default_args": {
                },
                "docstr" : "Takes a list of paragraphs and returns comments  Return a list from a text split into sentences.",
            },
            {
                "name" : "list_lengths",
                "function" : list_lengths,
                "default_args": {
                },
                "docstr" : "Return the a list of lengths for each item in a list.",
            },
            {
                "name" : "map",
                "function" : lambda entries, function: list(map(function, entries)),
                "default_args": {
                },
                "docstr" : "Run map on a list for a given function",
            },
            {
                "name" : "get_url_file",
                "function" : ndl.util.misc.get_url_file,
                "default_args": {
                },
                "docstr" : "Download a file with the given name.",
            },
            {
                "name" : "addmonth",
                "function" : ndl.util.dataframe.addmonth,
                "default_args" : {
                },
                "docstr" : "Add month column based on source date field."
            },
            {
                "name" : "addsupervisor",
                "function" : ndl.util.dataframe.fillna, # FIXME: This is a hack
                "default_args" : {
                },
                "docstr" : "None"
            },
            {
                "name" : "addyear",
                "function" : ndl.util.dataframe.addyear,
                "default_args" : {
                },
                "docstr" : "Add year column and based on source date field."
            },
            {
                "name" : "ascending",
                "function" : ndl.util.dataframe.ascending,
                "default_args" : {
                },
                "docstr" : "Sort in ascending order"
            },
            {
                "name" : "augmentcurrency",
                "function" : ndl.util.dataframe.augmentcurrency,
                "default_args" : {
                },
                "docstr" : "Preprocessor to set integer type on columns."
            },
            {
            "name" : "augmentmonth",
                "function" : ndl.util.dataframe.augmentmonth,
                "default_args" : {
                },
                "docstr" : "Augment with a month column based on source date field."
            },
            {
                "name" : "augmentyear",
                "function" : ndl.util.dataframe.augmentyear,
                "default_args" : {
                },
                "docstr" : "Augment with a year column based on source date field."
            },
            {
                "name" : "columncontains",
                "function" : ndl.util.dataframe.columncontains,
                "default_args" : {
                },
                "docstr" : "Filter on whether column contains a given value"
            },
            {
                "name" : "columnis",
                "function" : ndl.util.dataframe.columnis,
                "default_args" : {
                },
                "docstr" : "Filter on whether item is equal to a given value"
            },
            {
                "name" : "convert_datetime",
                "function" : ndl.util.dataframe.convert_datetime,
                "default_args" : {
                },
                "docstr" : "Preprocessor to set datetime type on columns."
            },
            {
                "name" : "convert_int",
                "function" : ndl.util.dataframe.convert_int,
                "default_args" : {
                },
                "docstr" : "Preprocessor to set integer type on columns."
            },
            {
                "name" : "convert_string",
                "function" : ndl.util.dataframe.convert_string,
                "default_args" : {
                },
                "docstr" : "Preprocessor to set string type on columns."
            },
            {
                "name" : "convert_year_iso",
                "function" : ndl.util.dataframe.convert_year_iso,
                "default_args" : {
                },
                "docstr" : "Preprocessor to set string type on columns."
            },
            {
                "name" : "current",
                "function" : ndl.util.dataframe.current,
                "default_args" : {
                },
                "docstr" : "Filter on whether item is current"
            },
            {
                "name" : "descending",
                "function" : ndl.util.dataframe.descending,
                "default_args" : {
                },
                "docstr" : "Sort in descending order"
            },
            {
                "name" : "former",
                "function" : ndl.util.dataframe.former,
                "default_args" : {
                },
                "docstr" : "Filter on whether item is current"
            },
            {
                "name" : "onbool",
                "function" : ndl.util.dataframe.onbool,
                "default_args" : {
                },
                "docstr" : "Filter on whether column is positive (or negative if inverted)"
            },
            {
                "name" : "recent",
                "function" : ndl.util.dataframe.recent,
                "default_args" : {
                },
                "docstr" : "Filter on year of item"
            },
            {
                "name" : "remove_nan",
                "function" : ndl.util.misc.remove_nan,
                "default_args" : {
                },
                "docstr" : "Delete missing entries from dictionary"
            },
        ]
                  
