Assess Module
============

The ``assess`` module provides functionality for assessment and computation in referia.
Most of the core classes in this module inherit from lynguine's assess module.

.. contents:: Contents
   :local:
   :depth: 2

Compute Class
------------

.. autoclass:: referia.assess.compute.Compute
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:

The ``Compute`` class extends lynguine's compute framework with referia-specific functionality:

Key Features
^^^^^^^^^^^

- **Data Processing Pipeline**: Supports preprocessing, computation, and postprocessing phases
- **Template Rendering**: Liquid template rendering for text generation
- **Text Analysis**: Word counting, summarization, and entity extraction
- **PDF Processing**: Extract comments and annotations from PDF files
- **Screen Capture**: Integration with system screen capture for assessment workflows

Function Registry
^^^^^^^^^^^^^^^

The Compute class maintains a registry of functions that can be used in computation tasks.
These are available through the ``_compute_functions_list`` method and include:

.. code-block:: python

   # Example of registering a compute function
   {
     "name": "word_count",
     "function": word_count,
     "default_args": {},
     "docstr": "Count words in text."
   }

Usage Example
^^^^^^^^^^^^

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

For details on the base functionality, see :py:class:`lynguine.assess.compute.Compute`.

Data Classes
----------

Referia uses the ``CustomDataFrame`` class from lynguine directly:

.. autoclass:: lynguine.assess.data.CustomDataFrame
   :noindex:
   :members: get_value_column, set_value_column
   
Review Classes
------------

The review module provides functionality specific to managing review processes.

.. autoclass:: referia.assess.review.Reviewer
   :members:
   :undoc-members:
   :show-inheritance:

Key Features
^^^^^^^^^^^

- Interactive web-based interface for reviews
- Customizable widget layouts
- Integration with computation engine
- Document generation capabilities

Inheritance Diagram
-----------------

The following diagram illustrates the inheritance relationships between referia and lynguine classes:

.. inheritance-diagram:: referia.assess.compute.Compute referia.assess.review.Reviewer
   :parts: 1

Module Functions
--------------

.. automodule:: referia.assess
   :members:
   :undoc-members:
   :show-inheritance: 