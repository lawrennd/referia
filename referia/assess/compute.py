import os
import datetime
import pandas as pd
import liquid as lq

from lynguine.config.context import Context
from lynguine.log import Logger

from ..config.interface import Interface

from ..util.misc import add_one_to_max, return_shortest, return_longest, identity

from lynguine.util.misc import get_url_file, remove_nan
from lynguine.assess.data import CustomDataFrame
import lynguine.assess.compute

from lynguine.util.dataframe import addmonth, fillna, addyear, ascending, augmentcurrency, augmentmonth, augmentyear, columncontains, columnis, convert_datetime, convert_int, convert_string, convert_year_iso, current, descending, former, onbool, recent

from lynguine.util.text import render_liquid

from ..util.text import word_count, text_summarizer, paragraph_split, list_lengths, named_entities, sentence_split, comment_list, pdf_extract_comments
from ..util.system import most_recent_screen_shot
from ..util.plot import bar_plot, histogram
from ..util.files import file_from_re, files_from_re



from ..exceptions import ComputeError


cntxt = Context(name="referia")
           
log = Logger(
    name=__name__,
    level=cntxt["logging"]["level"],
    filename=cntxt["logging"]["filename"],
    
)

class Compute(lynguine.assess.compute.Compute):
    def __init__(self, interface):
        """Initialize the compute object.
        
        :param interface: The interface to be used.
        :type interface: lynguine.config.interface.Interface
        :return: None
        """
        super().__init__(interface=interface)
        
    def prep_all(self, interface, data):
        """
        Prepare all compute entries for use.
        
        :param interface: The interface to be used.
        :type interface: lynguine.config.interface.Interface
        :param data: The data object to be used.
        :type data: lynguine.assess.data.CustomDataFrame
        :return: None
        """
        for comptype in ["precompute", "compute", "postcompute"]:
            if comptype in interface:
                if type(interface[comptype]) is list:
                    computes = interface[comptype]
                else:
                    computes = [interface[comptype]]
                for compute in computes:
                    self._computes[comptype].append(
                        self.prep(compute, data)
                    )
                    
    def prep(self, settings : dict, data : lynguine.assess.data.CustomDataFrame ) -> dict:
        """
        Prepare a compute entry for use.
        
        :param settings: The settings to be used.
        :type settings: dict
        :param data: The data to be used.
        :type data: lynguine.assess.data.CustomDataFrame
        :return: The prepared compute entry.
        :rtype: dict
        
        """
        compute_prep = {
            "function": self.gcf_(function=settings["function"], data=data),
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
        super().interface = value
            

    # def run(self, data : "CustomDataFrame", interface : Interface) -> None:
    #     """
    #     Run the computation given in compute.

    #     :param compute: The compute to be run.
    #     :type compute: lynguine.config.interface.Interface
    #     :param df: The data frame to be used.
    #     :type df: pandas.DataFrame or lynguine.assess.data.CustomDataFrame
    #     :param index: The index to be used.
    #     :type index: object
    #     :param refresh: Whether to refresh the field.
    #     :type refresh: bool
    #     :return: The result of the computation.
    #     :rtype: object
    #     """

    #     #super().run(compute, data, df, index, refresh);
        
    #     multi_output = False
    #     fname = compute["function"].__name__
    #     fargs = compute["args"]
    #     if index is None:
    #         index = data.get_index()

    #     if "field" in compute:
    #         columns = compute["field"]
    #         if type(columns) is list:
    #             multi_output = True
    #         else:
    #             columns = [columns]
    #     else:
    #         columns = None

    #     # Determine which current values of field aren't set
    #     missing_vals = []
    #     if columns is not None:
    #         for column in columns:
    #             if df is None:
    #                 if column not in data.columns:
    #                     missing_vals.append(True)
    #                     continue
    #             else:
    #                 if column not in df.columns:
    #                     missing_vals.append(True)
    #                     continue
    #             if column == "_": # If the column is called "_" then ignore that argument
    #                 missing_vals.append(False)
    #                 continue
    #             if df is None:
    #                 val = data.get_value_column(column)
    #             else:
    #                 val = df.at[index, column]
    #             if type(val) is not list and pd.isna(val):
    #                 missing_vals.append(True)
    #             else:
    #                 missing_vals.append(False)

    #     if refresh or any(missing_vals) or columns is None:
    #         if columns is not None:
    #             log.debug(f"Running compute function \"{fname}\" storing in field(s) \"{columns}\" with index=\"{index}\" with refresh=\"{refresh}\" and arguments \"{fargs}\".")
    #         else:
    #             log.debug(f"Running compute function \"{fname}\" with no field(s) stored for index=\"{index}\" with refresh=\"{refresh}\" and arguments \"{fargs}\".")

    #         new_vals = compute["function"](**fargs)
    #     else:
    #         return

    #     if multi_output and type(new_vals) is not tuple:
    #         errmsg = f"Multiple columns provided for return values of \"{fname}\" but return value given is not a tuple."
    #         log.error(errmsg)
    #         raise ValueError(errmsg)
            
    #     if columns is None:
    #         return new_vals
    #     else:
    #         if multi_output:
    #             new_vals = [*new_vals]
    #         else:
    #             new_vals = [new_vals]
    #         for column, new_val, missing_val in zip(columns, new_vals, missing_vals):
    #             if column == "_":
    #                 continue
    #             if refresh or missing_val and data.ismutable(column):
    #                 log.debug(f"Setting column {column} in data structure to value {new_val} from compute.")
    #                 data.set_value_column(new_val, column)
  
    def preprocess(self, data, interface):
        """
        Run all preprocess computations.

        :return: None
        """
        super().preprocess(data, interface)
        ##### Copied raw need to run on all elements.
        ## preprocess
        for op in ["preprocessor", "augmentor", "sorter"]:
            if op in interface["compute"]:
                computes = interface["compute"][op]
                if not isinstance(computes, list):
                    computes = [computes]
                for compute in computes:
                    compute_prep = self.prep(compute)
                    fargs = compute_prep["args"]
                    if "field" in compute:
                        data[compute["field"]] = compute_prep["function"](data, **fargs)
                    else:
                        compute_prep["function"](data, **fargs)
                        
        # Filter
        filt = pd.Series(True, index=data.index)
        if "filter" in interface["compute"]:
            computes = interface["compute"]["filter"]
            if not isinstance(computes, list):
                computes = [computes]    
                for compute in computes:
                    compute_prep = self.prep(compute)
                    fargs = compute_prep["args"]
                    newfilt = compute_prep["function"](data, **fargs)
                    filt = (filt & newfilt)
            data.filter_row(filt)

    def run_onchange(self, index, column, data):
        """
        Run all onchange computations. These are computations that occur when a particular column is modified.

        :param index: The index to be used.
        :type index: object
        :param column: The column to be used.
        :type column: str
        :return: None
        """
        log.debug(f"Running onchange for {column} at index {index} (not yet implemented).")        
        super().run_onchange(index, column, data)
    
    def run_all(self, data, df=None, index=None, pre=False, post=False):
        """
        Run any computation elements on the data frame.

        :param df: The data frame to be used.
        :type df: pandas.DataFrame or lynguine.assess.data.CustomDataFrame
        :param index: The index to be used.
        :type index: object
        :param pre: Whether to run precomputes.
        :type pre: bool
        :param post: Whether to run postcomputes.
        :type post: bool
        :return: None
        """
        super().run_all(data, df, index, pre, post)
        
        log.debug(f"Running computes on index=\"{index}\" with pre=\"{pre}\" and post=\"{post}\"")
        computes = []
        if pre:
            computes += self._computes["precompute"]
        computes += self._computes["compute"]
        if post:
            computes += self._computes["postcompute"]
            
        for compute in computes:
            field = compute["field"]
            if data.ismutable(field):
                if compute["refresh"]:
                    self.run(compute, data, df, index, refresh=True)
                else:                    
                    self.run(compute, data, df, index, refresh=False)
            else:
                log.warning(f"Attempted to write to unmutable field \"{field}\"")
    

    def _compute_functions_list(self) -> list[dict]:
        """
        Return a list of compute functions.

        :return: A list of compute functions.
        :rtype: list
        """
        return super()._compute_functions_list() + [
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
                "function" : get_url_file,
                "default_args": {
                },
                "docstr" : "Download a file with the given name.",
            },
            {
                "name" : "addmonth",
                "function" : addmonth,
                "default_args" : {
                },
                "docstr" : "Add month column based on source date field."
            },
            {
                "name" : "addsupervisor",
                "function" : fillna, # FIXME: This is a hack
                "default_args" : {
                },
                "docstr" : "None"
            },
            {
                "name" : "addyear",
                "function" : addyear,
                "default_args" : {
                },
                "docstr" : "Add year column and based on source date field."
            },
            {
                "name" : "ascending",
                "function" : ascending,
                "default_args" : {
                },
                "docstr" : "Sort in ascending order"
            },
            {
                "name" : "augmentcurrency",
                "function" : augmentcurrency,
                "default_args" : {
                },
                "docstr" : "Preprocessor to set integer type on columns."
            },
            {
            "name" : "augmentmonth",
                "function" : augmentmonth,
                "default_args" : {
                },
                "docstr" : "Augment with a month column based on source date field."
            },
            {
                "name" : "augmentyear",
                "function" : augmentyear,
                "default_args" : {
                },
                "docstr" : "Augment with a year column based on source date field."
            },
            {
                "name" : "columncontains",
                "function" : columncontains,
                "default_args" : {
                },
                "docstr" : "Filter on whether column contains a given value"
            },
            {
                "name" : "columnis",
                "function" : columnis,
                "default_args" : {
                },
                "docstr" : "Filter on whether item is equal to a given value"
            },
            {
                "name" : "convert_datetime",
                "function" : convert_datetime,
                "default_args" : {
                },
                "docstr" : "Preprocessor to set datetime type on columns."
            },
            {
                "name" : "convert_int",
                "function" : convert_int,
                "default_args" : {
                },
                "docstr" : "Preprocessor to set integer type on columns."
            },
            {
                "name" : "convert_string",
                "function" : convert_string,
                "default_args" : {
                },
                "docstr" : "Preprocessor to set string type on columns."
            },
            {
                "name" : "convert_year_iso",
                "function" : convert_year_iso,
                "default_args" : {
                },
                "docstr" : "Preprocessor to set string type on columns."
            },
            {
                "name" : "current",
                "function" : current,
                "default_args" : {
                },
                "docstr" : "Filter on whether item is current"
            },
            {
                "name" : "descending",
                "function" : descending,
                "default_args" : {
                },
                "docstr" : "Sort in descending order"
            },
            {
                "name" : "former",
                "function" : former,
                "default_args" : {
                },
                "docstr" : "Filter on whether item is current"
            },
            {
                "name" : "onbool",
                "function" : onbool,
                "default_args" : {
                },
                "docstr" : "Filter on whether column is positive (or negative if inverted)"
            },
            {
                "name" : "recent",
                "function" : recent,
                "default_args" : {
                },
                "docstr" : "Filter on year of item"
            },
            {
                "name" : "remove_nan",
                "function" : remove_nan,
                "default_args" : {
                },
                "docstr" : "Delete missing entries from dictionary"
            },
        ]
                  
