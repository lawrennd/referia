Basic Concepts
=============

This page explains the key concepts in referia and how they relate to the underlying lynguine framework.

Inheritance from Lynguine
----------------------

Referia is built on top of lynguine and inherits many core concepts:

.. figure:: ../_static/inheritance_diagram.png
   :alt: Inheritance diagram
   :width: 600px
   :align: center

   *Inheritance relationships between referia and lynguine components*

Understanding this inheritance relationship is crucial for working with referia effectively.

Compute Framework
--------------

The compute framework in referia inherits from lynguine's compute system:

- **Compute Class**: ``referia.assess.compute.Compute`` inherits from ``lynguine.assess.compute.Compute``
- **Computation Process**: The basic computation flow is inherited from lynguine, with referia adding review-specific functions
- **Function Registry**: Referia extends lynguine's function registry with additional functions for review processing

.. code-block:: python

    # Example of the inheritance relationship
    compute = referia.assess.compute.Compute(interface)
    
    # This will call lynguine's implementation of run_all
    compute.run_all(data, interface)
    
    # This uses referia's extended function registry
    functions = compute._compute_functions_list()

Data Management
------------

Referia uses lynguine's data management system:

- **CustomDataFrame**: ``lynguine.assess.data.CustomDataFrame`` is used directly in referia
- **Data Processing**: Core data processing methods from lynguine are used and extended
- **Storage**: Data storage mechanisms are inherited from lynguine

.. code-block:: python

    # Using lynguine's CustomDataFrame in referia
    from lynguine.assess.data import CustomDataFrame
    
    # Load data
    data = CustomDataFrame.from_csv("reviews.csv")
    
    # Process data using referia's compute framework
    compute.run_all(data, interface)

Configuration System
----------------

The configuration system extends lynguine's approach:

- **Interface Class**: ``referia.config.interface.Interface`` inherits from ``lynguine.config.interface.Interface``
- **Configuration Files**: The format is extended to include review-specific settings
- **Context**: ``lynguine.config.context.Context`` is used directly in referia

.. code-block:: python

    # Using referia's extended interface class
    from referia.config.interface import Interface
    
    # Load configuration
    interface = Interface.from_file("review_config.yml")
    
    # Access configuration with lynguine's dictionary-like syntax
    input_config = interface["input"]
    review_config = interface["review"]

Review Process Concepts
-------------------

Referia adds review-specific concepts on top of lynguine's framework:

- **Review Management**: Tools for handling review processes
- **Assessment**: Evaluation and scoring of reviews
- **Document Processing**: Text extraction and analysis for review documents

.. code-block:: python

    # Using referia's review functionality
    from referia.assess.review import Review
    
    # Create a review object
    review = Review(interface)
    
    # Process reviews
    review.process_submissions()
    
    # Generate review summaries
    summaries = review.generate_summaries()

Common Workflow
------------

A typical workflow in referia combines concepts from both lynguine and referia:

1. **Configuration**: Define review process using referia's extended configuration system
2. **Data Loading**: Load review data using lynguine's CustomDataFrame
3. **Computation**: Process data using referia's extended compute framework
4. **Review Processing**: Apply review-specific functionality from referia
5. **Output Generation**: Generate outputs using a combination of lynguine and referia functionality

Understanding the layers of inheritance helps you know which parts of the documentation to consult:

- For core data and computation concepts: refer to lynguine documentation
- For review-specific functionality: refer to referia documentation 