Referia Documentation
=====================

**Referia** is a Python package for managing review processes, built on top of the **lynguine** framework.

.. note::
   Referia inherits significant functionality from the lynguine package. Throughout this documentation,
   we will clearly indicate which functionality is inherited vs. specific to referia, and provide
   cross-references to the lynguine documentation where appropriate.

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   introduction
   installation
   quickstart

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   usage/basic_concepts
   usage/compute
   usage/assessment

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   modules/assess
   modules/config
   modules/util

.. toctree::
   :maxdepth: 1
   :caption: Development

   contributing
   inheritance

Inheritance from Lynguine
------------------------

Referia is built on top of the lynguine framework and inherits significant functionality from it.
The inheritance relationship is particularly important in these areas:

- **Compute Framework**: Core computation methods are inherited from ``lynguine.assess.compute.Compute``
- **Data Management**: Data handling uses ``lynguine.assess.data.CustomDataFrame`` 
- **Configuration**: Interface and configuration system is based on lynguine's approach

For more details on the inheritance relationships, see the :doc:`inheritance` page.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search` 