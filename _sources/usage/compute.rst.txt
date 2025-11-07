Working with the Compute Framework
============================

This guide covers how to use referia's compute framework, which inherits from and extends the lynguine compute system.

Understanding the Inheritance
--------------------------

The ``referia.assess.compute.Compute`` class inherits from ``lynguine.assess.compute.Compute``:

.. code-block:: text

    lynguine.assess.compute.Compute
        ↑
        └── referia.assess.compute.Compute

This inheritance relationship means:

1. All core compute methods from lynguine are available in referia
2. Referia extends the function registry with additional review-specific functions
3. Some methods are overridden to provide referia-specific functionality

Basic Usage
---------

Here's the basic pattern for using the compute framework:

.. code-block:: python

    from referia.assess.compute import Compute
    from referia.config.interface import Interface
    from lynguine.assess.data import CustomDataFrame
    
    # Load configuration
    interface = Interface.from_file("review_config.yml")
    
    # Create a compute object
    compute = Compute(interface=interface)
    
    # Load data
    data = CustomDataFrame.from_csv("reviews.csv")
    
    # Run all computations on the data
    compute.run_all(data, interface)

Core Methods (Inherited from lynguine)
-----------------------------------

The following methods are inherited from lynguine:

- ``prep``: Prepares a compute entry
- ``run``: Runs a single computation
- ``run_all``: Runs all computations on the data
- ``preprocess``: Runs preprocessing steps on the data

.. code-block:: python

    # Using inherited methods
    
    # Prepare a compute entry
    compute_entry = compute.prep(settings={"function": "word_count"}, data=data)
    
    # Run a single computation
    compute.run(data, compute_entry)
    
    # Run all computations
    compute.run_all(data, interface)

Referia-Specific Extensions
------------------------

Referia extends the compute framework with additional methods and functionality:

- ``copy_screen_capture``: Captures screenshots for review processes
- Extended preprocessing capabilities in ``preprocess``
- Additional compute functions in ``_compute_functions_list``

.. code-block:: python

    # Using referia-specific extensions
    
    # Capture a screenshot
    image_data = compute.copy_screen_capture()
    
    # Access the extended function list
    functions = compute._compute_functions_list()
    
    # Use referia-specific compute functions
    from referia.util.text import word_count, named_entities
    word_count_result = word_count("Sample text")
    entities = named_entities("John reviewed the paper")

Available Compute Functions
------------------------

Referia includes all lynguine compute functions plus these review-specific functions:

1. **Text Processing**:
   - ``word_count``: Count words in text
   - ``text_summarizer``: Generate text summaries
   - ``paragraph_split``: Split text into paragraphs
   - ``sentence_split``: Split text into sentences
   - ``named_entities``: Extract named entities from text

2. **Document Processing**:
   - ``pdf_extract_comments``: Extract comments from PDF files
   - ``file_from_re``: Find files matching patterns
   - ``files_from_re``: Find multiple files matching patterns

3. **Visualization**:
   - ``histogram``: Create histograms
   - ``bar_plot``: Create bar plots

Example Configuration
------------------

Here's an example configuration using both lynguine-inherited and referia-specific compute functions:

.. code-block:: yaml

    compute:
      # Preprocessing (lynguine functionality)
      preprocessor:
        - function: convert_datetime
          column: submission_date
      
      # Referia-specific computation
      compute:
        - function: word_count
          field: word_count
          args:
            column: review_text
        
        - function: text_summarizer
          field: summary
          args:
            column: review_text
            max_length: 200
            
        - function: named_entities
          field: entities
          args:
            column: review_text

Advanced Usage
-----------

For more advanced usage, you can:

1. **Create custom compute functions**:

   .. code-block:: python
   
       # Define a custom compute function
       def custom_review_score(review_text, criteria_weight=0.5):
           # Calculate score based on review text
           return score
       
       # Register the function
       interface["compute"]["compute"].append({
           "function": "custom_review_score",
           "field": "score",
           "args": {
               "column": "review_text",
               "criteria_weight": 0.7
           }
       })

2. **Chain computations together**:

   .. code-block:: yaml
   
       compute:
         compute:
           # First computation
           - function: word_count
             field: word_count
             args:
               column: review_text
           
           # Second computation uses result of first
           - function: histogram
             field: word_count_histogram
             args:
               column: word_count
               bins: 10

Future Extensions
--------------

**LLM Integration (Planned)**

Referia is being extended with Large Language Model capabilities for AI-powered text analysis, summarisation, and generation. Planned functions include:

- ``llm_complete``: General-purpose text completion
- ``llm_summarise``: AI-powered summarisation
- ``llm_extract``: Extract structured information
- ``llm_classify``: Intelligent text classification
- ``llm_chat``: Conversational interactions

For details, see `CIP-0006: LLM Integration for Compute Framework <../cip/cip0006.md>`_. 