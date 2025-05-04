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
   :caption: Contents:

   introduction
   installation
   quickstart
   modules/assess
   modules/config
   modules/util
   inheritance
   examples/index
   contributing

Module Overview
--------------

Referia is organized into several core modules, each with a specific purpose:

* :doc:`modules/assess`: Assessment and computation framework
  
  * :class:`referia.assess.compute.Compute`: Main computation engine
  * :class:`referia.assess.review.Reviewer`: Interactive review interface

* :doc:`modules/config`: Configuration and interfaces
  
  * :class:`referia.config.interface.Interface`: Configuration interface

* :doc:`modules/util`: Utility functions
  
  * Text processing
  * File operations
  * Visualization

Inheritance Structure
--------------------

Referia extends the lynguine framework with specialized functionality. The main inheritance relationships are:

* ``referia.assess.compute.Compute`` inherits from ``lynguine.assess.compute.Compute``
* ``referia.assess.review.Reviewer`` inherits from ``lynguine.assess.display.DisplaySystem``

For a detailed view of these relationships, see the :doc:`inheritance` page.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search` 