import os
import datetime
import pandas as pd
import liquid as lq

from lynguine.config.context import Context
from lynguine.log import Logger

from ...config.interface import Interface

from ...util.misc import add_one_to_max, return_shortest, return_longest, identity

from lynguine.util.misc import get_url_file, remove_nan
from lynguine.assess.data import CustomDataFrame
import lynguine.assess.compute

from lynguine.util.dataframe import addmonth, fillna, addyear, ascending, augmentcurrency, augmentmonth, augmentyear, columncontains, columnis, convert_datetime, convert_int, convert_string, convert_year_iso, current, descending, former, onbool, recent

from lynguine.util.text import render_liquid

from ...util.text import word_count, text_summarizer, paragraph_split, list_lengths, named_entities, sentence_split, comment_list, pdf_extract_comments, pdf_extract_text
from ...util.system import most_recent_screen_shot
from ...util.plot import bar_plot, histogram
from ...util.files import file_from_re, files_from_re
from .grain_fit import subject_grain_fit, subject_grain_reset
from .vq import subject_vq_fit
from .mppca import (
    subject_grain_confirm_split,
    subject_grain_propose_split,
    subject_grain_seed_fit,
    subject_grain_undo_split,
)
from .phrases import llm_extract_phrases, segment_dialogue_units, stamp_dialogue_doc_ids
from .embed import llm_embed, llm_embed_extraction_phrases
from .compare import (
    jsd,
    run_format_share_compare,
    run_question_type_stress,
    run_wordlist_floor,
)
from .distance import (
    axis_correlates,
    classical_mds,
    cluster_ids_missing,
    cosine_ground_cost,
    document_soft_topic_distributions,
    emd_distance_matrix,
    load_document_titles,
    permanova,
    permdisp,
    run_document_distance_analysis,
    topic_means_from_responsibilities,
)
from .grounds import llm_classify_grounds
from .stores import named_store_status
from .topic_naming import (
    subject_grain_apply_focus_label,
    subject_grain_keys_needing_names,
    subject_grain_parse_label_reply,
    subject_grain_prepare_label,
    subject_grain_stub_label,
)

# LLM integration (optional - graceful fallback if not installed)
try:
    from ...util.llm import get_llm_manager, LLMError
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    get_llm_manager = None
    LLMError = Exception

from ...exceptions import ComputeError


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
        self._interface = interface
        self._data = None
        super().__init__(interface=interface)

    def _named_store_status(self, llm_cache_dir=None, **kwargs):
        """CIP-0017: file facts for named stores plus a labelled LLM cache line."""
        cache_dir = llm_cache_dir
        if cache_dir is None and LLM_AVAILABLE and get_llm_manager is not None:
            try:
                mgr = get_llm_manager()
                cache = getattr(mgr, "cache", None)
                cache_dir = getattr(cache, "directory", None)
            except Exception:
                cache_dir = None
        return named_store_status(
            getattr(self, "_interface", None),
            data=getattr(self, "_data", None),
            llm_cache_dir=cache_dir,
        )

    def _config_info_dir(self):
        """Directory of the packed corpus / scores stores (``../info``)."""
        from pathlib import Path

        iface = getattr(self, "_interface", None)
        if iface is None:
            return None
        base = getattr(iface, "directory", None)
        getter = getattr(iface, "get", None)
        details = None
        if callable(getter):
            for key in ("data", "input", "output", "cache"):
                details = getter(key)
                if details is not None:
                    break
        rel = None
        if details is not None:
            dget = getattr(details, "get", None)
            if callable(dget):
                rel = dget("directory")
        if base and rel:
            return Path(str(base)) / str(rel)
        if rel and Path(str(rel)).is_absolute():
            return Path(str(rel))
        if base:
            return Path(str(base)) / ".." / "info"
        return None

    def _run_document_distance_analysis(
        self, cluster_ids=None, doc_titles=None, **kwargs
    ):
        """Fill VQ ``cluster_ids`` and chapter titles from sibling info files."""
        info = self._config_info_dir()
        if cluster_ids_missing(cluster_ids) and info is not None:
            codebook = info / "codebook.parquet"
            if codebook.exists():
                try:
                    frame = pd.read_parquet(codebook)
                    if "cluster_ids" in frame.columns and len(frame):
                        cluster_ids = frame.iloc[0]["cluster_ids"]
                except Exception:
                    pass
        if not doc_titles and info is not None:
            documents = info / "documents.yml"
            if documents.exists():
                doc_titles = load_document_titles(documents)
        return run_document_distance_analysis(
            cluster_ids=cluster_ids, doc_titles=doc_titles, **kwargs
        )

    def _load_info_yaml_rows(self, filename: str) -> list[dict]:
        info = self._config_info_dir()
        if info is None:
            return []
        path = info / filename
        if not path.exists():
            return []
        cached = getattr(self, "_info_yaml_cache", None)
        if cached is None:
            cached = {}
            self._info_yaml_cache = cached
        key = str(path)
        if key in cached:
            return cached[key]
        import yaml

        try:
            from yaml import CSafeLoader as SafeLoader
        except ImportError:
            from yaml import SafeLoader
        with open(path, encoding="utf-8") as handle:
            data = yaml.load(handle, Loader=SafeLoader)
        rows = data if isinstance(data, list) else []
        cached[key] = rows
        return rows

    def _run_format_share_compare(
        self, cluster_ids=None, kinds=None, **kwargs
    ):
        """Fill VQ ``cluster_ids`` and phrase ``kinds`` from sibling info."""
        info = self._config_info_dir()
        if cluster_ids_missing(cluster_ids) and info is not None:
            codebook = info / "codebook.parquet"
            if codebook.exists():
                try:
                    frame = pd.read_parquet(codebook)
                    if "cluster_ids" in frame.columns and len(frame):
                        cluster_ids = frame.iloc[0]["cluster_ids"]
                except Exception:
                    pass
        if kinds is None:
            phrases = self._load_info_yaml_rows("phrases.yml")
            if phrases:
                kinds = [row.get("kind") for row in phrases]
                kwargs.setdefault(
                    "groups",
                    kwargs.get("groups")
                    or [row.get("format") or row.get("group") for row in phrases],
                )
                kwargs.setdefault(
                    "doc_ids",
                    kwargs.get("doc_ids")
                    or [row.get("doc_id") for row in phrases],
                )
        return run_format_share_compare(
            cluster_ids=cluster_ids, kinds=kinds, **kwargs
        )

    def _run_question_type_stress(self, contexts=None, formats=None, **kwargs):
        if contexts is None:
            chunks = self._load_info_yaml_rows("chunks.yml")
            contexts = [row.get("context") or "" for row in chunks]
            formats = [row.get("format") or row.get("group") for row in chunks]
        return run_question_type_stress(
            contexts, formats=formats, **kwargs
        )

    def _run_wordlist_floor(self, quotes=None, bases=None, groups=None, **kwargs):
        if quotes is None:
            phrases = self._load_info_yaml_rows("phrases.yml")
            quotes = [row.get("quote") for row in phrases]
            groups = groups or [
                row.get("format") or row.get("group") for row in phrases
            ]
            kwargs.setdefault(
                "doc_ids", [row.get("doc_id") for row in phrases]
            )
        if bases is None:
            grounds = self._load_info_yaml_rows("grounds.yml")
            if grounds:
                by_id = {
                    row.get("phrase_id"): row.get("basis") for row in grounds
                }
                phrases = self._load_info_yaml_rows("phrases.yml")
                if phrases:
                    bases = [by_id.get(row.get("phrase_id")) for row in phrases]
                else:
                    bases = [row.get("basis") for row in grounds]
        return run_wordlist_floor(
            quotes, bases=bases, groups=groups, **kwargs
        )

    def _phrase_siding_rows(self, kwargs):
        rows = self._load_info_yaml_rows("phrases.yml")
        kwargs.setdefault(
            "groups",
            [row.get("format") or row.get("group") for row in rows],
        )
        kwargs.setdefault("doc_ids", [row.get("doc_id") for row in rows])
        kwargs.setdefault("verified", [row.get("verified") for row in rows])
        kwargs.setdefault(
            "phrase_ids", [row.get("phrase_id") for row in rows]
        )
        return rows, kwargs

    def _run_kind_reconstruction(
        self, phrases=None, kinds=None, **kwargs
    ):
        kwargs.setdefault("label_name", "kind")
        kwargs.setdefault("missing_hint", "Run 02_embed first.")
        if phrases is None:
            rows, kwargs = self._phrase_siding_rows(kwargs)
            phrases = [row.get("phrase") for row in rows]
            kinds = [row.get("kind") for row in rows]
        from .verify import run_kind_reconstruction as _run

        return _run(phrases, kinds, **kwargs)

    def _run_basis_reconstruction(
        self, phrases=None, kinds=None, **kwargs
    ):
        kwargs.setdefault("label_name", "basis")
        kwargs.setdefault(
            "missing_hint",
            "Run 07_grounds Classify all + Save first.",
        )
        if phrases is None:
            rows, kwargs = self._phrase_siding_rows(kwargs)
            grounds = self._load_info_yaml_rows("grounds.yml")
            by_id = {
                str(row.get("phrase_id")): row.get("basis") for row in grounds
            }
            phrases = [row.get("phrase") for row in rows]
            kinds = [by_id.get(str(row.get("phrase_id"))) or "" for row in rows]
        from .verify import run_kind_reconstruction as _run

        return _run(phrases, kinds, **kwargs)

    def _run_lens_reconstruction(
        self, phrases=None, kinds=None, **kwargs
    ):
        kwargs.setdefault("label_name", "lens")
        kwargs.setdefault("missing_hint", "Run 03_vq and 04_grain first.")
        from .verify import hard_lens_labels, run_kind_reconstruction as _run

        if phrases is None:
            rows, kwargs = self._phrase_siding_rows(kwargs)
            phrases = [row.get("phrase") for row in rows]
            scores = self._load_info_yaml_rows("scores.yml")
            rec = scores[0] if scores else {}
            cluster_ids = rec.get("cluster_ids")
            info = self._config_info_dir()
            if cluster_ids_missing(cluster_ids) and info is not None:
                codebook = info / "codebook.parquet"
                if codebook.exists():
                    try:
                        frame = pd.read_parquet(codebook)
                        if "cluster_ids" in frame.columns and len(frame):
                            cluster_ids = frame.iloc[0]["cluster_ids"]
                    except Exception:
                        cluster_ids = None
            try:
                kinds = hard_lens_labels(
                    rec.get("responsibilities"),
                    cluster_ids,
                    rec.get("topic_labels"),
                )
            except Exception as exc:
                md = (
                    "Could not build hard lens labels from scores / codebook "
                    f"({exc}). Run 03_vq and 04_grain, then Save."
                )
                return {}, [], [], [], md, 0
            if len(kinds) != len(phrases):
                md = (
                    f"Hard lens length {len(kinds)} != {len(phrases)} phrases. "
                    "Re-Save 02_embed so pack order matches phrases.yml, "
                    "then refit 03_vq."
                )
                return {}, [], [], [], md, 0
        return _run(phrases, kinds, **kwargs)

    def _llm_classify_grounds(self, text, points=None, unit_id=None, **kwargs):
        if not points and unit_id is not None:
            phrases = self._load_info_yaml_rows("phrases.yml")
            uid = str(unit_id)
            points = [
                {
                    "phrase_id": row.get("phrase_id"),
                    "phrase": row.get("phrase"),
                    "quote": row.get("quote"),
                    "kind": row.get("kind"),
                }
                for row in phrases
                if str(row.get("unit_id")) == uid
            ]
        return llm_classify_grounds(text, points, **kwargs)


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
        self._data = data
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
            {
                "name": "subject_grain_propose_split",
                "function": self._subject_grain_propose_split,
                "default_args": {
                    "n_children": 2,
                    "mass_threshold": 0.05,
                    "em_accept": 40,
                    "seed": 0,
                    "label_model": "stub",
                },
                "docstr": (
                    "Propose a soft topic split: update catalogue geometry "
                    "(topic_parent genealogy + derived topic_tree) and "
                    "pending/undo; read σ² / em_accept as controls "
                    "(never write). When label_model is not stub, also "
                    "names provisional children via the configured LLM so "
                    "the UI does not leave «Parent» → (unnamed t)."
                ),
            },
            {
                "name": "subject_grain_confirm_split",
                "function": subject_grain_confirm_split,
                "default_args": {},
                "docstr": (
                    "Confirm a pending split: swap overlay for per-topic "
                    "planes; clear pending/undo. Genealogy already lives in "
                    "topic_parent from Propose. Does not touch EM controls."
                ),
            },
            {
                "name": "subject_grain_undo_split",
                "function": subject_grain_undo_split,
                "default_args": {},
                "docstr": (
                    "Undo a pending split: restore catalogue (including "
                    "topic_parent) from split_undo; redraw at live σ²; "
                    "never write EM / label controls."
                ),
            },
            {
                "name": "subject_grain_name_focus_topic",
                "function": self._subject_grain_name_focus_topic,
                "default_args": {
                    "n_exemplars": 8,
                    "temperature": 0.2,
                },
                "docstr": (
                    "Name the focus topic and any provisional labels "
                    "(Topic N seeds, '(unnamed…)' Propose placeholders): "
                    "reads label_prompt / label_model; writes topic_labels, "
                    "remaps topic_parent, clears seed ghost parents, "
                    "refreshes topic_tree, and relabels a pending split "
                    "plotly overlay (uq_spec / uq_by_topic). Uses the "
                    "configured LLM when label_model is not stub. Also "
                    "invoked automatically from Propose when label_model "
                    "is not stub."
                ),
            },
            {
                "name": "llm_extract_phrases",
                "function": llm_extract_phrases,
                "default_args": {
                    "model": "gpt-4o-mini",
                    "min_words": 3,
                    "max_words": 10,
                    "max_items": 8,
                    "temperature": 0.2,
                    "quote_support_threshold": 0.0,
                },
                "docstr": (
                    "Extract short concern/benefit/condition phrases from "
                    "chunk text. Writes extraction_payload and a list of "
                    "phrase dicts for explode (CIP-0015). Optional "
                    "quote_support_threshold drops unverified quotes and "
                    "quotes taken from the bot question / facilitator."
                ),
            },
            {
                "name": "stamp_dialogue_doc_ids",
                "function": stamp_dialogue_doc_ids,
                "default_args": {},
                "docstr": (
                    "Stamp conversation doc_id on unit dicts: "
                    "{round}::{participant_id} for chatbot, filename for "
                    "workshops. Optionally drop units under min_unit_words."
                ),
            },
            {
                "name": "segment_dialogue_units",
                "function": segment_dialogue_units,
                "default_args": {},
                "docstr": (
                    "document_segment then stamp_dialogue_doc_ids so pack "
                    "weights chatbot conversations, not Recollective dumps."
                ),
            },
            {
                "name": "llm_embed",
                "function": llm_embed,
                "default_args": {
                    "model": "text-embedding-3-large",
                },
                "docstr": (
                    "Embed phrase text; write an L2-normalised float list "
                    "(CIP-0015). Client injected; optional pca_dim on batches."
                ),
            },
            {
                "name": "llm_embed_extraction_phrases",
                "function": llm_embed_extraction_phrases,
                "default_args": {
                    "model": "text-embedding-3-large",
                },
                "docstr": (
                    "Embed each dict in extraction_phrases on a chunk row "
                    "(CIP-0015 listing). Writes embedding onto the dicts "
                    "so explode copies vectors onto phrase rows."
                ),
            },
            {
                "name": "subject_grain_seed_fit",
                "function": subject_grain_seed_fit,
                "default_args": {
                    "k": 1,
                    "force_refit": False,
                    "sigma2_mode": "fixed",
                    "em_accept": 40,
                    "seed": 0,
                },
                "docstr": (
                    "k=1 MPPCA seed on a packed corpus row. Writes "
                    "responsibilities and local U_q planes. Skip if "
                    "responsibilities already present unless force_refit."
                ),
            },
            {
                "name": "subject_vq_fit",
                "function": subject_vq_fit,
                "default_args": {
                    "n_vq": 64,
                    "force_refit": True,
                    "seed": 0,
                    "kmeans_init": "k-means++",
                    "kmeans_n_init": 10,
                    "kmeans_max_iter": 300,
                    "vq_walk_speed": 0.08,
                    "vq_walk_frames": 48,
                    "vq_walk_subspace": 8,
                    "vq_walk_linger": True,
                },
                "docstr": (
                    "K-means vector quantisation of phrase embeddings "
                    "(CIP-001A). Writes codebook centroids, masses, "
                    "cluster_ids, and a Brownian projection-walk figure."
                ),
            },
            {
                "name": "subject_grain_fit",
                "function": subject_grain_fit,
                "default_args": {
                    "cluster_method": "mppca",
                    "n_clusters": 8,
                    "force_refit": True,
                    "sigma2_mode": "fixed",
                    "em_accept": 40,
                    "seed": 0,
                    "kmeans_init": "k-means++",
                    "kmeans_n_init": 10,
                    "kmeans_max_iter": 300,
                    "agglo_linkage": "average",
                    "agglo_metric": "cosine",
                    "lens_weight": "uniform",
                },
                "docstr": (
                    "Fit grain catalogue for cluster_method (mppca, "
                    "kmeans, agglomerative). Hard methods write one-hot R."
                ),
            },
            {
                "name": "subject_grain_reset",
                "function": subject_grain_reset,
                "default_args": {
                    "cluster_method": "mppca",
                    "n_clusters": 8,
                    "force_refit": True,
                    "k": 1,
                    "seed": 0,
                },
                "docstr": (
                    "Refit grain: MPPCA returns to k=1; sklearn methods "
                    "refit current n_clusters. Clears pending split."
                ),
            },
            {
                "name": "document_soft_topic_distributions",
                "function": document_soft_topic_distributions,
                "default_args": {"min_mass": 50.0},
                "docstr": (
                    "Sum phrase responsibilities per document into a "
                    "row-stochastic histogram P (CIP-0016)."
                ),
            },
            {
                "name": "topic_means_from_responsibilities",
                "function": topic_means_from_responsibilities,
                "default_args": {},
                "docstr": "L2-normalised responsibility-weighted topic means.",
            },
            {
                "name": "cosine_ground_cost",
                "function": cosine_ground_cost,
                "default_args": {},
                "docstr": "Cosine distance between topic means (zero diagonal).",
            },
            {
                "name": "emd_distance_matrix",
                "function": emd_distance_matrix,
                "default_args": {},
                "docstr": (
                    "Pairwise EMD. Requires pip install 'referia[distance]'."
                ),
            },
            {
                "name": "classical_mds",
                "function": classical_mds,
                "default_args": {"n_components": 2},
                "docstr": "Classical MDS on an EMD matrix.",
            },
            {
                "name": "permanova",
                "function": permanova,
                "default_args": {"n_perm": 999, "seed": 0},
                "docstr": "One-way PERMANOVA on a distance matrix.",
            },
            {
                "name": "permdisp",
                "function": permdisp,
                "default_args": {"n_perm": 999, "seed": 0},
                "docstr": "PERMDISP on a distance matrix.",
            },
            {
                "name": "axis_correlates",
                "function": axis_correlates,
                "default_args": {"top": 5},
                "docstr": "Pearson r of MDS axes with document topic shares.",
            },
            {
                "name": "run_document_distance_analysis",
                "function": self._run_document_distance_analysis,
                "default_args": {
                    "min_mass": 1.0,
                    "n_perm": 999,
                    "seed": 0,
                    "n_components": 2,
                },
                "docstr": (
                    "Façade: P, topic means, EMD, MDS, tests, and Plotly "
                    "specs on a packed corpus row (CIP-0016)."
                ),
            },
            {
                "name": "run_format_share_compare",
                "function": self._run_format_share_compare,
                "default_args": {
                    "min_mass": 1.0,
                    "n_boot": 2000,
                    "seed": 42,
                    "min_gap": 3.0,
                },
                "docstr": (
                    "Document-weighted type mix, lens shares, and JSD "
                    "(CIP-001E). Paper Part A analogue on the current grain."
                ),
            },
            {
                "name": "llm_classify_grounds",
                "function": self._llm_classify_grounds,
                "default_args": {
                    "model": "gpt-4.1-mini",
                    "temperature": 0.1,
                },
                "docstr": (
                    "Classify the basis of each extracted point on a unit "
                    "(CIP-001E Part B). Writes payload and a grounds list."
                ),
            },
            {
                "name": "run_question_type_stress",
                "function": self._run_question_type_stress,
                "default_args": {},
                "docstr": (
                    "Share of chatbot units whose context matches each "
                    "question-type pattern (CIP-001E)."
                ),
            },
            {
                "name": "run_wordlist_floor",
                "function": self._run_wordlist_floor,
                "default_args": {},
                "docstr": (
                    "Word-list experience floor on each point's own quote "
                    "(CIP-001E). No model call."
                ),
            },
            {
                "name": "run_kind_reconstruction",
                "function": self._run_kind_reconstruction,
                "default_args": {
                    "n_folds": 5,
                    "seed": 0,
                    "model": "logreg",
                    "ngram_min": 1,
                    "ngram_max": 2,
                    "min_df": 2,
                    "max_features": 4000,
                    "C": 1.0,
                    "verified_only": True,
                },
                "docstr": (
                    "Siding: 5-fold bag-of-words reconstruction of extract "
                    "kind labels (CIP-001F). Not a pipeline stage."
                ),
            },
            {
                "name": "run_basis_reconstruction",
                "function": self._run_basis_reconstruction,
                "default_args": {
                    "n_folds": 5,
                    "seed": 0,
                    "model": "logreg",
                    "ngram_min": 1,
                    "ngram_max": 2,
                    "min_df": 2,
                    "max_features": 4000,
                    "C": 1.0,
                    "verified_only": True,
                },
                "docstr": (
                    "Siding: 5-fold bag-of-words reconstruction of Part B "
                    "basis labels (CIP-001F)."
                ),
            },
            {
                "name": "run_lens_reconstruction",
                "function": self._run_lens_reconstruction,
                "default_args": {
                    "n_folds": 5,
                    "seed": 0,
                    "model": "logreg",
                    "ngram_min": 1,
                    "ngram_max": 2,
                    "min_df": 2,
                    "max_features": 4000,
                    "C": 1.0,
                    "verified_only": True,
                },
                "docstr": (
                    "Siding: 5-fold bag-of-words reconstruction of hard "
                    "grain lens (CIP-001F). Not a check of Name strings."
                ),
            },
            {
                "name": "named_store_status",
                "function": self._named_store_status,
                "default_args": {},
                "docstr": (
                    "File facts + catalogue for named Access stores "
                    "(CIP-0017). LLM diskcache is labelled cost-only."
                ),
            },
            {
                "name": "subject_grain_ensure_seed_names",
                "function": self._subject_grain_ensure_seed_names,
                "default_args": {
                    "n_exemplars": 8,
                    "temperature": 0.2,
                },
                "docstr": (
                    "On load: if any topic_labels are still provisional "
                    "(Topic N / (unnamed…)) and label_model is not stub, "
                    "name them via the LLM. Idempotent when already named "
                    "(no LLM call). Intended as review precompute so the "
                    "k=1 seed is titled before the analyst starts."
                ),
            },
        ] + (self._llm_functions_list() if LLM_AVAILABLE else [])

    def _subject_grain_propose_split(
        self,
        embeddings,
        responsibilities,
        phrases=None,
        focus_topic="T0",
        sigma2: float = 0.05,
        em_accept: int = 40,
        mass_threshold: float = 0.05,
        n_children: int = 2,
        topic_labels=None,
        topic_parent=None,
        seed: int = 0,
        label_model: str = "stub",
        label_prompt=None,
        n_exemplars: int = 8,
        temperature: float = 0.2,
        cluster_method: str = "mppca",
        **_kwargs,
    ):
        """Propose a soft split, then name provisional children when not stub.

        Geometry / pending / undo come from
        :func:`subject_grain_propose_split`. Offline ``label_model=stub``
        keeps ``«Parent» → (unnamed t)`` placeholders; any other model
        runs :meth:`_subject_grain_name_focus_topic` so Focus / Topics /
        the Plotly overlay show real titles immediately after Propose.
        """
        packed = subject_grain_propose_split(
            embeddings,
            responsibilities,
            phrases=phrases,
            focus_topic=focus_topic,
            sigma2=sigma2,
            em_accept=em_accept,
            mass_threshold=mass_threshold,
            n_children=n_children,
            topic_labels=topic_labels,
            topic_parent=topic_parent,
            seed=seed,
            cluster_method=cluster_method,
        )
        (
            uq_spec,
            uq_by_topic,
            keys,
            R_list,
            focus,
            labels,
            parent,
            tree,
            pending,
            undo,
        ) = packed
        model = str(label_model or "stub").strip().lower()
        if model in ("", "stub", "none", "off"):
            log.info(
                "subject_grain_propose_split: geometry only "
                f"(label_model={label_model!r}); children stay provisional"
            )
            return packed

        log.info(
            "subject_grain_propose_split: naming provisional children "
            f"with model={label_model!r}"
        )
        labels, parent, tree, uq_spec, uq_by_topic, pending = (
            self._subject_grain_name_focus_topic(
                phrases=phrases,
                responsibilities=R_list,
                focus_topic=focus,
                topic_labels=labels,
                topic_parent=parent,
                topic_keys=keys,
                label_prompt=label_prompt,
                label_model=label_model,
                pending_proposal=pending,
                uq_spec=uq_spec,
                uq_by_topic=uq_by_topic,
                n_exemplars=n_exemplars,
                temperature=temperature,
            )
        )
        return (
            uq_spec,
            uq_by_topic,
            keys,
            R_list,
            focus,
            labels,
            parent,
            tree,
            pending,
            undo,
        )

    def _subject_grain_ensure_seed_names(
        self,
        phrases,
        responsibilities,
        focus_topic="T0",
        topic_labels=None,
        topic_parent=None,
        topic_keys=None,
        label_prompt=None,
        label_model="stub",
        n_exemplars: int = 8,
        temperature: float = 0.2,
        **_kwargs,
    ):
        """Name provisional seed labels on open; no-op when already titled.

        Unlike an explicit Name click, this never re-LLMs a topic that already
        has a human title. Returns ``(topic_labels, topic_parent, topic_tree)``.
        """
        from referia.assess.compute.mppca import format_topic_tree_markdown
        from referia.assess.compute.topic_naming import _is_provisional_label

        labels = dict(topic_labels) if isinstance(topic_labels, dict) else {}
        keys = [str(k) for k in (topic_keys or list(labels.keys()))]
        if not keys and labels:
            keys = [str(k) for k in labels.keys()]
        provisional = [
            key
            for key in keys
            if _is_provisional_label(labels.get(key, key), key)
        ]
        model = str(label_model or "stub").strip().lower()
        if not provisional or model in ("", "stub", "none", "off"):
            focus = str(focus_topic) if str(focus_topic) in keys else (
                keys[0] if keys else "T0"
            )
            parent = (
                {str(k): (None if v in (None, "", "null") else str(v))
                 for k, v in topic_parent.items()}
                if isinstance(topic_parent, dict)
                else {key: None for key in keys}
            )
            tree = format_topic_tree_markdown(
                keys,
                labels,
                parent,
                focus,
                responsibilities=responsibilities,
            )
            log.info(
                "subject_grain_ensure_seed_names: skip LLM "
                f"(provisional={provisional!r} model={label_model!r})"
            )
            return labels, parent, tree

        log.info(
            "subject_grain_ensure_seed_names: naming "
            f"{provisional} with model={label_model!r}"
        )
        labels_out, parent_out, tree, *_ = self._subject_grain_name_focus_topic(
            phrases=phrases,
            responsibilities=responsibilities,
            focus_topic=focus_topic,
            topic_labels=labels,
            topic_parent=topic_parent,
            topic_keys=keys,
            label_prompt=label_prompt,
            label_model=label_model,
            n_exemplars=n_exemplars,
            temperature=temperature,
        )
        return labels_out, parent_out, tree

    def _subject_grain_name_one_topic(
        self,
        phrases,
        responsibilities,
        focus_topic,
        label_prompt,
        label_model,
        *,
        n_exemplars: int = 8,
        temperature: float = 0.2,
    ) -> tuple[str, str]:
        """Return ``(topic_key, label)`` for one topic via stub or live LLM."""
        prompt, exemplars, focus = subject_grain_prepare_label(
            phrases,
            responsibilities,
            focus_topic=focus_topic,
            label_prompt=label_prompt,
            n_exemplars=n_exemplars,
        )
        model = str(label_model or "stub").strip()
        use_live = (
            model.lower() not in {"", "stub", "none", "offline", "fake"}
            and LLM_AVAILABLE
            and get_llm_manager is not None
        )
        if use_live:
            try:
                llm_config = (
                    getattr(self, "interface", {}).get("llm", {})
                    if hasattr(self, "interface")
                    else {}
                )
                manager = get_llm_manager(llm_config)
                reply = manager.call(
                    prompt=prompt,
                    model=model,
                    temperature=float(temperature),
                    system_prompt=(
                        "You name soft consultation topics for human analysts. "
                        "Reply with JSON only: {\"label\": \"...\", \"description\": \"...\"}."
                    ),
                )
                return focus, subject_grain_parse_label_reply(reply, exemplars)
            except Exception as exc:  # noqa: BLE001 — surface failure to UI
                log.warning(
                    f"subject_grain_name_focus_topic: LLM failed for {focus} ({exc})"
                )
                raise ComputeError(
                    f"LLM naming failed for {focus} (model={model}): {exc}"
                ) from exc
        return focus, subject_grain_stub_label(exemplars, focus)

    def _subject_grain_name_focus_topic(
        self,
        phrases,
        responsibilities,
        focus_topic="T0",
        topic_labels=None,
        topic_parent=None,
        topic_keys=None,
        label_prompt=None,
        label_model="stub",
        pending_proposal=None,
        uq_spec=None,
        uq_by_topic=None,
        n_exemplars: int = 8,
        temperature: float = 0.2,
        **_kwargs,
    ):
        """Name focus + unnamed Propose children via stub or live LLM.

        Catalogue writes: ``topic_labels``, remapped ``topic_parent``, and
        derived ``topic_tree``. When a pending split overlay is present,
        also rewrites ``uq_spec`` / ``uq_by_topic`` / ``pending_proposal``
        display names so Plotly stops showing ``(unnamed…)``. Controls
        ``label_prompt`` / ``label_model`` are inputs and are never
        returned. Propose does not call an LLM — it only leaves
        ``(unnamed…)`` placeholders; this action fills them.
        """
        keys_to_name = subject_grain_keys_needing_names(
            topic_labels, focus_topic, topic_keys
        )
        log.info(
            f"subject_grain_name_focus_topic: focus={focus_topic} "
            f"model={label_model} keys_to_name={keys_to_name}"
        )
        labels = topic_labels
        parent = topic_parent
        tree = None
        for key in keys_to_name:
            named_key, label = self._subject_grain_name_one_topic(
                phrases,
                responsibilities,
                key,
                label_prompt,
                label_model,
                n_exemplars=n_exemplars,
                temperature=temperature,
            )
            log.info(
                f"subject_grain_name_focus_topic: named {named_key} → {label!r}"
            )
            labels, parent, tree = subject_grain_apply_focus_label(
                labels,
                named_key,
                label,
                topic_parent=parent,
                topic_keys=topic_keys,
                responsibilities=responsibilities,
            )
        if tree is None:
            # Nothing to name — still refresh derived view.
            labels, parent, tree = subject_grain_apply_focus_label(
                topic_labels,
                focus_topic,
                (
                    (topic_labels or {}).get(str(focus_topic), str(focus_topic))
                    if isinstance(topic_labels, dict)
                    else str(focus_topic)
                ),
                topic_parent=topic_parent,
                topic_keys=topic_keys,
                responsibilities=responsibilities,
            )

        uq_out = uq_spec
        uq_map = uq_by_topic
        pending_out = pending_proposal
        if isinstance(pending_proposal, dict) and pending_proposal:
            children = list(pending_proposal.get("children") or [])
            if children and isinstance(labels, dict):
                from referia.util.plotly_figures import (
                    relabel_proposed_split_plotly_spec,
                )

                child_display = [
                    str(labels.get(str(ck), ck)) for ck in children
                ]
                # Soft split replaces the parent topic with children, so
                # pending.parent often collides with a child key. Prefer a
                # live named parent when the key is still distinct; otherwise
                # keep the sealed Propose parent_label. Always sanitize so a
                # nested provisional never remains in the overlay title.
                from referia.assess.compute.topic_naming import (
                    _is_provisional_label,
                    _short_parent_for_placeholder,
                )

                parent_display = (
                    pending_proposal.get("parent_label") or "parent"
                )
                parent_key = pending_proposal.get("parent")
                children_set = {str(c) for c in children}
                if (
                    parent_key is not None
                    and str(parent_key) not in children_set
                    and isinstance(labels, dict)
                    and str(parent_key) in labels
                ):
                    parent_display = labels[str(parent_key)]
                parent_display = _short_parent_for_placeholder(
                    parent_display, parent_key
                )
                if _is_provisional_label(parent_display, parent_key):
                    # Seed parent after soft split — title uses short form;
                    # children carry the LLM names.
                    log.info(
                        "subject_grain_name_focus_topic: sanitized "
                        f"provisional overlay parent → {parent_display!r}"
                    )

                base_spec = uq_spec
                if not isinstance(base_spec, dict) and isinstance(
                    uq_by_topic, dict
                ):
                    focus = pending_proposal.get("focus") or children[0]
                    base_spec = uq_by_topic.get(str(focus)) or uq_by_topic.get(
                        children[0]
                    )
                if isinstance(base_spec, dict):
                    uq_out = relabel_proposed_split_plotly_spec(
                        base_spec,
                        child_labels=child_display,
                        parent_label=str(parent_display),
                    )
                    log.info(
                        "subject_grain_name_focus_topic: relabelled pending "
                        f"overlay children={child_display} "
                        f"parent={parent_display!r}"
                    )
                    if isinstance(uq_by_topic, dict):
                        uq_map = dict(uq_by_topic)
                        for ck in children:
                            uq_map[str(ck)] = uq_out
                    pending_out = dict(pending_proposal)
                    pending_out["parent_label"] = str(parent_display)
                    he = pending_out.get("history_entry")
                    if isinstance(he, dict):
                        he = dict(he)
                        he["parent_label"] = str(parent_display)
                        pending_out["history_entry"] = he

        return labels, parent, tree, uq_out, uq_map, pending_out
    
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
                          temperature: float = 0.3, system_prompt: str = None,
                          include_history: bool = False, history: str = None,
                          **kwargs) -> str:
            """
            Extract text from a PDF and generate an LLM-based review/summary.
            
            Combines pdf_extract_text with LLM capabilities to automatically generate
            reviews or summaries of PDF content. Perfect for thesis chapter reviews,
            document analysis, or automated commenting.
            
            Optionally includes previous conversation history as context, enabling
            reviews that build on prior analysis or avoid repetition.
            
            :param filename: PDF filename to review
            :param directory: Directory containing the PDF
            :param review_type: Type of review ('general', 'strengths', 'weaknesses', 'technical', 'summary', 'questions')
            :param max_chars: Maximum characters to extract from PDF (for LLM context limits)
            :param model: LLM model to use
            :param temperature: Sampling temperature
            :param system_prompt: Custom system prompt (overrides review_type)
            :param include_history: If True, include conversation history as context (default: False)
            :param history: Previous conversation text to include as context (optional)
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
            
            # Build prompt with optional history
            prompt_parts = []
            
            # Add conversation history if enabled and available
            if include_history and history and str(history).strip():
                prompt_parts.append("## Previous Conversation\n\n")
                prompt_parts.append(str(history))
                prompt_parts.append("\n\n---\n\n")
            
            # Add document text
            prompt_parts.append("## Document Content\n\n")
            prompt_parts.append(text)
            
            full_prompt = "".join(prompt_parts)
            
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
                    "questions": (

                        "You are an academic domain expert. You want to explore the authors "
                        "understanding of their work and the broader context. Provide three "
                        "general questions and 3 more detailed questions that would allow "
                        "the author to demonstrate both their general understanding and "
                        "their detailed understanding of this work."
                        "Keep your response under 150 words."
                    ),
                        
                }
                system_prompt = prompts.get(review_type, prompts["general"])
            
            # Generate review using LLM
            llm_config = getattr(self, 'interface', {}).get("llm", {}) if hasattr(self, 'interface') else {}
            manager = get_llm_manager(llm_config)
            
            return manager.call(
                prompt=full_prompt,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
                max_tokens=300,  # Reasonable length for a review
                **kwargs
            )
        
        def llm_custom_query(custom_prompt: str, filename: str, 
                            start_page: int = None, end_page: int = None,
                            directory: str = "",
                            model: str = "gpt-4o-mini", 
                            max_chars: int = 50000,
                            temperature: float = 0.7,
                            system_prompt: str = None,
                            include_query: bool = False,
                            include_history: bool = False,
                            history: str = None,
                            **kwargs) -> str:
            """
            Answer a custom user prompt about a chapter using LLM.
            
            Extracts text from a PDF chapter and combines it with a user-provided
            prompt to generate a custom LLM response. This enables flexible 
            exploration of chapter content with arbitrary questions.
            
            Optionally includes previous conversation history as context, enabling
            follow-up questions that reference earlier exchanges.
            
            :param custom_prompt: The user's custom prompt/question (extracted from data via row_args)
            :param filename: PDF filename for the chapter
            :param start_page: Starting page of the chapter (optional)
            :param end_page: Ending page of the chapter (optional)
            :param directory: Directory containing the PDF
            :param model: LLM model to use (default: gpt-4o-mini)
            :param max_chars: Maximum characters to extract from PDF
            :param temperature: LLM temperature (default: 0.7)
            :param system_prompt: Optional system prompt to guide LLM behavior
            :param include_query: If True, include the question before the response (default: False)
            :param include_history: If True, include conversation history as context (default: False)
            :param history: Previous conversation text to include as context (optional)
            :return: LLM response text or error message (with question if include_query=True)
            
            **Example**:
            
            .. code-block:: yaml
            
                - type: Textarea
                  field: chapter1CustomPrompt
                  args:
                    description: "Ask a question about Chapter 1"
                    placeholder: "e.g., What are the key methodological contributions?"
                
                - type: Textarea
                  field: chapter1CustomResponse
                  args:
                    description: "LLM Response"
                
                - type: PopulateButton
                  args:
                    description: "Ask LLM"
                    target: chapter1CustomResponse
                    compute:
                      field: chapter1CustomResponse
                      function: llm_custom_query
                      view_args:
                        filename:
                          display: "{Name}_thesis_chapter1.pdf"
                      row_args:
                        custom_prompt: chapter1CustomPrompt
                        start_page: Chapter1FP
                      args:
                        directory: $HOME/Documents/theses/examined/
                        model: "gpt-4o-mini"
            """
            # 1. Check the user's custom prompt
            if not custom_prompt or not str(custom_prompt).strip():
                return "⚠️ Please enter a question in the prompt field above."
            
            custom_prompt = str(custom_prompt).strip()
            
            # 2. Extract chapter text from PDF
            try:
                chapter_text = pdf_extract_text(
                    filename=filename,
                    directory=directory,
                    start_page=start_page,
                    end_page=end_page,
                    max_chars=max_chars
                )
                
                if not chapter_text or not chapter_text.strip():
                    return f"⚠️ Could not extract text from {filename}"
                    
            except Exception as e:
                log.error(f"Error extracting PDF in llm_custom_query: {str(e)}")
                return f"❌ Error extracting PDF: {str(e)}"
            
            # 3. Build prompt with optional history
            prompt_parts = []
            
            # Add conversation history if enabled and available
            if include_history and history and str(history).strip():
                prompt_parts.append("## Previous Conversation\n\n")
                prompt_parts.append(str(history))
                prompt_parts.append("\n\n---\n\n")
            
            # Add chapter context
            prompt_parts.append("## Chapter Content\n\n")
            prompt_parts.append(chapter_text)
            prompt_parts.append("\n\n---\n\n")
            
            # Add current question
            prompt_parts.append("## Current Question\n\n")
            prompt_parts.append(custom_prompt)
            
            full_prompt = "".join(prompt_parts)
            
            # 4. Query LLM
            try:
                llm_config = getattr(self, 'interface', {}).get("llm", {}) if hasattr(self, 'interface') else {}
                manager = get_llm_manager(llm_config)
                
                # Use default system prompt if not provided
                if system_prompt is None:
                    system_prompt = (
                        "You are a helpful assistant analyzing academic thesis chapters. "
                        "Provide clear, structured answers to questions about the content. "
                        "Be specific and cite relevant parts of the text when appropriate."
                    )
                
                response = manager.call(
                    prompt=full_prompt,
                    model=model,
                    temperature=temperature,
                    system_prompt=system_prompt,
                    **kwargs
                )
                
                # Format output with question if requested
                if include_query:
                    return f"**Question:** {custom_prompt}\n\n**Response:** {response}"
                else:
                    return response
                
            except LLMError as e:
                log.error(f"LLM error in llm_custom_query: {str(e)}")
                return f"❌ LLM Error: {str(e)}"
            except Exception as e:
                log.error(f"Unexpected error in llm_custom_query: {str(e)}")
                return f"❌ Unexpected error: {str(e)}"
        
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
            {
                "name": "llm_custom_query",
                "function": llm_custom_query,
                "default_args": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_chars": 50000,
                    "directory": "",
                    "include_query": False,
                },
                "docstr": "Answer a custom user prompt about a chapter using LLM.",
            },
        ]
                  
