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
    """
    Compute class for performing calculations and transformations on data.
    
    This class extends the lynguine.assess.compute.Compute base class and provides
    referia-specific computation functionality. It handles data processing, transformation,
    and analysis operations needed for review and assessment workflows.
    
    The Compute class follows a three-phase processing model:
    
    1. **Preprocessing**: Prepare data for computation (from parent class)
    2. **Computation**: Apply operations to data elements (from parent class)
    3. **Postprocessing**: Finalize results after computation (from parent class)
    
    The primary computation methods (prep, run, run_all) are inherited from the lynguine
    parent class and should not be reimplemented here.
    
    .. rubric:: Inheritance
    
    This class inherits from lynguine.assess.compute.Compute and extends it with:
    
    * Additional text analysis functions (word_count, text_summarizer, etc.)
    * Referia-specific functionality like screen capture
    * Extended preprocessing capabilities
    
    .. rubric:: Example
    
    Basic usage with an interface configuration:
    
    .. code-block:: python
    
        from referia.config.interface import Interface
        from referia.assess.compute import Compute
        from lynguine.assess.data import CustomDataFrame
        
        # Create compute instance
        interface = Interface(config_file="path/to/config.yml")
        compute = Compute(interface)
        
        # Create data
        data = CustomDataFrame({"text": ["Sample text for analysis"]})
        
        # Run computations
        compute.run_all(data)
        
        # Access results
        print(data)
    
    .. seealso::
        :class:`lynguine.assess.compute.Compute`
            Parent class providing core computation logic
        :class:`lynguine.assess.data.CustomDataFrame`
            Data class used with Compute
    """
    
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
        
        This method extends the parent class method to handle different computation types.
        
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
    
    def preprocess(self, data, interface):
        """
        Run all preprocess computations.
        
        This method extends the parent class functionality for preprocessing data.

        :param data: The data to be processed.
        :type data: lynguine.assess.data.CustomDataFrame
        :param interface: The interface to be used.
        :type interface: lynguine.config.interface.Interface
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

    def run_onchange(self, data, index, column):
        """
        Run computations triggered by changes to a specific data column.
        
        This method is called when a value in a specific column is modified. It runs any
        compute functions that are registered to respond to changes in that column.
        The method passes control to the parent class implementation after logging the event.
        
        :param data: The data frame containing the changed value.
        :type data: lynguine.assess.data.CustomDataFrame
        :param index: The index of the row where the change occurred.
        :type index: int, str, or other valid index type
        :param column: The name of the column where the change occurred.
        :type column: str
        :return: None
        :rtype: None
        
        .. note::
            This method provides a hook for reactive computations. When integrated with
            the Reviewer class, it allows for automatic updates to dependent values
            when input values change.
            
        **Example**:
        
        .. code-block:: python
        
            compute.run_onchange(data, 0, 'score')  # When the 'score' column changes
        """
        log.debug(f"Running onchange for {column} at index {index} (not yet implemented).")        
        super().run_onchange(data, index, column)
    
    def _compute_functions_list(self) -> list[dict]:
        """
        Return the registry of available compute functions.
        
        This method extends the parent class implementation by adding referia-specific 
        compute functions to the function registry. Each registered function is available 
        for use in compute operations defined in interface configurations.
        
        :return: A list of dictionaries, each containing:
                 
                 * name (str): The name of the function to be used in config files
                 * function (callable): The actual function to be called
                 * default_args (dict): Default arguments for the function
                 * docstr (str, optional): Documentation string for the function
        :rtype: list of dict
        
        .. note::
            The returned functions include:
            
            * liquid: Template rendering using Liquid syntax
            * word_count: Count words in text
            * pdf_extract_comments: Extract comments from PDF files
            * Plus various utility functions (max, len, sum, etc.)
            
            This function registry is used internally when processing compute specifications
            from configuration files. Users typically don't call this method directly.
            
        .. seealso::
            :meth:`lynguine.assess.compute.Compute._compute_functions_list` : Parent method providing base functions
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
                  
