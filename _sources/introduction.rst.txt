Introduction to Referia
===================

What is Referia?
--------------

Referia is a Python package designed for managing review processes. It provides tools for:

- Document assessment and evaluation
- Computational processing of review data
- Review management workflows
- Document extraction and analysis

Referia is built on top of the lynguine framework, which provides core functionality for data handling,
computation, and configuration. Referia extends this functionality with specific features for review processes.

Relationship with Lynguine
----------------------

Referia extensively inherits from and extends the lynguine package:

.. figure:: _static/inheritance_diagram.png
   :alt: Inheritance diagram showing relationship between referia and lynguine
   :align: center

   *Inheritance relationships between referia and lynguine*

Key areas of inheritance include:

1. **Compute Framework**: The ``referia.assess.compute.Compute`` class inherits from ``lynguine.assess.compute.Compute`` 
   and extends it with review-specific functionality.

2. **Data Handling**: Referia uses lynguine's ``CustomDataFrame`` class for data management.

3. **Configuration**: The configuration system in referia extends lynguine's approach.

Throughout this documentation, we clearly indicate which functionality is inherited from lynguine 
and which is specific to referia, with appropriate cross-references.

Key Features
-----------

Referia adds the following key features to lynguine's core functionality:

- **Review Management**: Tools for handling review processes, including reviewer assignment, review collection, and summary generation.

- **Document Processing**: Functions for extracting text from documents, performing text analysis, and generating summaries.

- **Assessment Framework**: Tools for evaluating and scoring reviews according to defined criteria.

- **Visualization**: Custom visualization tools for review metrics and assessment results.

Documentation Organization
------------------------

This documentation is organized into several sections:

- **Getting Started**: Introduction, installation, and quick start guides.
- **User Guide**: More detailed information on using referia for review processes.
- **API Reference**: Detailed documentation of referia's modules, classes, and functions.
- **Development**: Guidelines for contributing to referia and understanding its design.

The API reference includes information on inheritance relationships with lynguine, 
helping you understand which functionality comes from which package. 