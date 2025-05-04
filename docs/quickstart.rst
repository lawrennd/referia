Quick Start Guide
===============

This guide will help you get started with referia quickly. We'll cover basic usage patterns 
and demonstrate how referia extends lynguine's functionality.

Basic Usage
---------

Here's a simple example of using referia for a basic review process:

.. code-block:: python

    # Import key classes
    from referia.assess.compute import Compute
    from referia.config.interface import Interface
    from lynguine.assess.data import CustomDataFrame
    
    # Load configuration from a YAML file
    interface = Interface.from_file("review_config.yml")
    
    # Create a compute object
    compute = Compute(interface=interface)
    
    # Load review data
    data = CustomDataFrame.from_csv("reviews.csv")
    
    # Run computations on the data
    compute.run_all(data, interface)
    
    # Access computed results
    results = data.to_dict(orient="records")

Understanding the Inheritance Structure
------------------------------------

In this example:

1. ``Interface`` class extends lynguine's configuration system
2. ``Compute`` class inherits from lynguine's compute framework
3. ``CustomDataFrame`` is used directly from lynguine

Review Configuration
-----------------

A typical review configuration file might look like:

.. code-block:: yaml

    # General configuration
    input:
      type: file
      file: reviews.csv
      index: id
    
    # Review-specific configuration
    compute:
      # Preprocessing steps
      preprocessor:
        - function: convert_datetime
          column: submission_date
        - function: word_count
          field: word_count
          args:
            column: review_text
      
      # Computation steps
      compute:
        - function: text_summarizer
          field: summary
          args:
            column: review_text
            max_length: 200
    
    # Output configuration
    output:
      type: file
      file: processed_reviews.csv

Working with Compute Functions
---------------------------

Referia extends lynguine's compute framework with additional functions:

.. code-block:: python

    # Using referia-specific compute functions
    
    # Text analysis
    from referia.util.text import word_count, named_entities
    
    # Count words in a text
    word_count = word_count("This is a sample review text.")
    
    # Extract named entities
    entities = named_entities("John Smith reviewed the paper.")
    
    # Plotting
    from referia.util.plot import histogram
    
    # Create a histogram of word counts
    histogram(word_counts, bins=10, title="Word Count Distribution")

Next Steps
---------

After getting familiar with the basics, you might want to explore:

1. The :doc:`usage/basic_concepts` section to understand referia's core concepts
2. The :doc:`modules/assess` documentation to learn about assessment functionality
3. The :doc:`inheritance` page to better understand the relationship with lynguine

For more complex examples, refer to the user guide sections. 