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

- Additional computation functions for text analysis
- Extended preprocessing capabilities
- Document handling functions
- Custom visualization tools

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

.. autoclass:: referia.assess.review.Review
   :members:
   :undoc-members:
   :show-inheritance:

Inheritance Diagram
-----------------

The following diagram illustrates the inheritance relationships between referia and lynguine classes:

.. code-block:: text

    lynguine.assess.compute.Compute
        ↑
        └── referia.assess.compute.Compute

    lynguine.assess.data.CustomDataFrame
        ↑
        └── (used directly in referia)

Module Functions
--------------

.. automodule:: referia.assess
   :members:
   :undoc-members:
   :show-inheritance: 