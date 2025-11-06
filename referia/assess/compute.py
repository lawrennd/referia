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

from ..util.text import word_count, text_summarizer, paragraph_split, list_lengths, named_entities, sentence_split, comment_list, pdf_extract_comments, pdf_extract_text
from ..util.system import most_recent_screen_shot
from ..util.plot import bar_plot, histogram
from ..util.files import file_from_re, files_from_re

# LLM integration (optional - graceful fallback if not installed)
try:
    from ..util.llm import get_llm_manager, LLMError
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    get_llm_manager = None
    LLMError = Exception

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

    def run(self, data, interface):
        """
        Run the compute operations on the data.
        
        This method extends the parent class implementation by storing the interface
        configuration so that LLM functions can access it.
        
        :param data: The data to be processed.
        :type data: lynguine.assess.data.CustomDataFrame
        :param interface: The interface defining the compute operations.
        :type interface: lynguine.config.interface.Interface or dict
        :return: None
        """
        # Store interface for LLM functions to access
        self.interface = interface
        super().run(data, interface)
    
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
                "name" : "pdf_extract_text",
                "function" : pdf_extract_text,
                "default_args" : {
                },
                "docstr" : "Extract text content from a PDF file."
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
        ] + (self._llm_functions_list() if LLM_AVAILABLE else [])
    
    def _llm_functions_list(self) -> list[dict]:
        """
        Return the registry of LLM compute functions.
        
        These functions provide Large Language Model capabilities for text analysis,
        generation, summarisation, and transformation. They require the LLM dependencies
        to be installed (poetry install --with llm) and appropriate API keys configured.
        
        :return: A list of dictionaries, each containing:
                 
                 * name (str): The name of the function to be used in config files
                 * function (callable): The actual function to be called
                 * default_args (dict): Default arguments for the function
                 * docstr (str): Documentation string for the function
        :rtype: list of dict
        
        .. note::
            All LLM functions support these common arguments:
            
            * model (str): Model to use (e.g., 'gpt-4o-mini', 'claude-3-haiku-20240307')
            * temperature (float): Sampling temperature 0-1, higher = more creative
            * max_tokens (int): Maximum tokens in response
            * system_prompt (str): System prompt to guide the LLM's behavior
            * use_cache (bool): Whether to use cached responses (default: True)
            
        .. seealso::
            :class:`referia.util.llm.LLMManager` : Core LLM management class
        """
        
        def llm_complete(text: str, model: str = "gpt-4o-mini", temperature: float = 0.7,
                        max_tokens: int = None, system_prompt: str = None, **kwargs) -> str:
            """
            General-purpose LLM text completion.
            
            :param text: Input text/prompt
            :param model: Model to use
            :param temperature: Sampling temperature (0-1)
            :param max_tokens: Maximum tokens in response
            :param system_prompt: System prompt
            :return: LLM response text
            """
            llm_config = getattr(self, 'interface', {}).get("llm", {}) if hasattr(self, 'interface') else {}
            manager = get_llm_manager(llm_config)
            return manager.call(
                prompt=text,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
                **kwargs
            )
        
        def llm_summarise(text: str, model: str = "gpt-4o-mini", temperature: float = 0.3,
                         max_tokens: int = 150, system_prompt: str = None, **kwargs) -> str:
            """
            Summarise text using an LLM.
            
            :param text: Text to summarise
            :param model: Model to use (default: gpt-4o-mini for cost efficiency)
            :param temperature: Sampling temperature (default: 0.3 for consistency)
            :param max_tokens: Maximum tokens in summary
            :param system_prompt: Custom system prompt
            :return: Summary text
            """
            if system_prompt is None:
                system_prompt = (
                    "You are an expert at summarising text concisely while preserving "
                    "key information. Provide a clear, factual summary."
                )
            
            prompt = f"Summarise the following text:\n\n{text}"
            llm_config = getattr(self, 'interface', {}).get("llm", {}) if hasattr(self, 'interface') else {}
            manager = get_llm_manager(llm_config)
            return manager.call(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
                **kwargs
            )
        
        def llm_extract(text: str, extraction_type: str, model: str = "gpt-4o-mini",
                       temperature: float = 0.2, system_prompt: str = None, **kwargs) -> str:
            """
            Extract structured information from text.
            
            :param text: Text to extract from
            :param extraction_type: What to extract (e.g., 'key points', 'action items')
            :param model: Model to use
            :param temperature: Sampling temperature (default: 0.2 for precision)
            :param system_prompt: Custom system prompt
            :return: Extracted information
            """
            if system_prompt is None:
                system_prompt = (
                    "You are an expert at extracting structured information from text. "
                    "Provide clear, factual extractions."
                )
            
            prompt = f"Extract {extraction_type} from the following text:\n\n{text}"
            llm_config = getattr(self, 'interface', {}).get("llm", {}) if hasattr(self, 'interface') else {}
            manager = get_llm_manager(llm_config)
            return manager.call(
                prompt=prompt,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
                **kwargs
            )
        
        def llm_classify(text: str, categories: list, model: str = "gpt-4o-mini",
                        temperature: float = 0.1, system_prompt: str = None, **kwargs) -> str:
            """
            Classify text into one of the provided categories.
            
            :param text: Text to classify
            :param categories: List of possible categories
            :param model: Model to use
            :param temperature: Sampling temperature (default: 0.1 for consistency)
            :param system_prompt: Custom system prompt
            :return: Selected category
            """
            if system_prompt is None:
                system_prompt = (
                    "You are an expert at classifying text. Select the most appropriate "
                    "category and respond with only the category name."
                )
            
            categories_str = ", ".join(f"'{c}'" for c in categories)
            prompt = (
                f"Classify the following text into one of these categories: {categories_str}\n\n"
                f"Text: {text}\n\n"
                f"Category:"
            )
            llm_config = getattr(self, 'interface', {}).get("llm", {}) if hasattr(self, 'interface') else {}
            manager = get_llm_manager(llm_config)
            return manager.call(
                prompt=prompt,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
                **kwargs
            )
        
        def llm_chat(text: str, context: str = None, model: str = "gpt-4o-mini",
                    temperature: float = 0.7, system_prompt: str = None, **kwargs) -> str:
            """
            Chat-style interaction with context.
            
            :param text: User message
            :param context: Previous conversation context
            :param model: Model to use
            :param temperature: Sampling temperature
            :param system_prompt: System prompt
            :return: Assistant response
            """
            if system_prompt is None:
                system_prompt = "You are a helpful assistant."
            
            if context:
                prompt = f"Context: {context}\n\nUser: {text}\n\nAssistant:"
            else:
                prompt = text
            
            llm_config = getattr(self, 'interface', {}).get("llm", {}) if hasattr(self, 'interface') else {}
            manager = get_llm_manager(llm_config)
            return manager.call(
                prompt=prompt,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
                **kwargs
            )
        
        def llm_pdf_review(filename: str, directory: str = "", review_type: str = "general",
                          max_chars: int = 30000, model: str = "gpt-4o-mini",
                          temperature: float = 0.3, system_prompt: str = None, **kwargs) -> str:
            """
            Extract text from a PDF and generate an LLM-based review/summary.
            
            Combines pdf_extract_text with LLM capabilities to automatically generate
            reviews or summaries of PDF content. Perfect for thesis chapter reviews,
            document analysis, or automated commenting.
            
            :param filename: PDF filename to review
            :param directory: Directory containing the PDF
            :param review_type: Type of review ('general', 'strengths', 'weaknesses', 'technical', 'summary')
            :param max_chars: Maximum characters to extract from PDF (for LLM context limits)
            :param model: LLM model to use
            :param temperature: Sampling temperature
            :param system_prompt: Custom system prompt (overrides review_type)
            :return: LLM-generated review text
            
            **Example**:
            
            .. code-block:: yaml
            
                compute:
                  - function: llm_pdf_review
                    field: ch1GeneralComments
                    view_args:
                      filename:
                        display: "{Name}_thesis_ch1.pdf"
                    args:
                      directory: "$HOME/Documents/theses/examined"
                      review_type: "general"
                      model: "gpt-4o-mini"
            """
            # Extract text from PDF
            text = pdf_extract_text(filename, directory=directory, max_chars=max_chars)
            
            if not text:
                return ""
            
            # Set system prompt based on review type if not provided
            if system_prompt is None:
                prompts = {
                    "general": (
                        "You are an expert academic reviewer. Provide a concise, constructive "
                        "general comment on the following text. Focus on clarity, structure, "
                        "and key contributions. Keep your response under 200 words."
                    ),
                    "strengths": (
                        "You are an expert academic reviewer. Identify and describe the key "
                        "strengths of the following text. Focus on methodology, contribution, "
                        "clarity, and rigor. Keep your response under 200 words."
                    ),
                    "weaknesses": (
                        "You are an expert academic reviewer. Identify constructive areas for "
                        "improvement in the following text. Be specific and helpful. "
                        "Keep your response under 200 words."
                    ),
                    "technical": (
                        "You are an expert technical reviewer. Provide a detailed technical "
                        "assessment of the following text. Focus on methodology, correctness, "
                        "and technical rigor. Keep your response under 250 words."
                    ),
                    "summary": (
                        "You are an expert at summarizing academic text. Provide a clear, "
                        "concise summary of the key points, methods, and findings. "
                        "Keep your response under 150 words."
                    ),
                }
                system_prompt = prompts.get(review_type, prompts["general"])
            
            # Generate review using LLM
            llm_config = getattr(self, 'interface', {}).get("llm", {}) if hasattr(self, 'interface') else {}
            manager = get_llm_manager(llm_config)
            
            return manager.call(
                prompt=text,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
                max_tokens=300,  # Reasonable length for a review
                **kwargs
            )
        
        return [
            {
                "name": "llm_complete",
                "function": llm_complete,
                "default_args": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                },
                "docstr": "General-purpose LLM text completion.",
            },
            {
                "name": "llm_summarise",
                "function": llm_summarise,
                "default_args": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.3,
                    "max_tokens": 150,
                },
                "docstr": "Summarise text using an LLM.",
            },
            {
                "name": "llm_extract",
                "function": llm_extract,
                "default_args": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.2,
                },
                "docstr": "Extract structured information from text using an LLM.",
            },
            {
                "name": "llm_classify",
                "function": llm_classify,
                "default_args": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                },
                "docstr": "Classify text into categories using an LLM.",
            },
            {
                "name": "llm_chat",
                "function": llm_chat,
                "default_args": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                },
                "docstr": "Chat-style interaction with context using an LLM.",
            },
            {
                "name": "llm_pdf_review",
                "function": llm_pdf_review,
                "default_args": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.3,
                    "max_chars": 30000,
                    "review_type": "general",
                },
                "docstr": "Extract text from PDF and generate LLM-based review/summary.",
            },
        ]
                  
