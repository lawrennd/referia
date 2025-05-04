Inheritance Relationships
=======================

Referia extends the lynguine framework through class inheritance. This page documents the key inheritance relationships to help developers understand which functionality is provided by lynguine vs. implemented specifically in referia.

Compute Class
------------

.. code-block:: text

    lynguine.assess.compute.Compute
        ↑
        └── referia.assess.compute.Compute

The ``referia.assess.compute.Compute`` class inherits from ``lynguine.assess.compute.Compute`` and extends it with:

- Additional computational functions specific to referia
- Extended preprocessing capabilities
- Screen capture functionality
- Custom document processing methods

Inherited methods include:

- ``prep`` - Prepares compute settings
- ``run`` - Executes computations
- ``run_all`` - Runs computations on all data
- Core computation infrastructure

**See also**: :py:class:`referia.assess.compute.Compute`, :py:class:`lynguine.assess.compute.Compute`

Data Classes
-----------

Referia uses the ``CustomDataFrame`` class from lynguine for data management:

.. code-block:: text

    lynguine.assess.data.CustomDataFrame
        ↑
        └── (used directly in referia)

The ``CustomDataFrame`` is not subclassed in referia, but is used directly with some referia-specific methods that operate on it.

**See also**: :py:class:`lynguine.assess.data.CustomDataFrame`

Configuration System
------------------

.. code-block:: text

    lynguine.config.interface.Interface
        ↑
        └── referia.config.interface.Interface

The configuration system in referia extends lynguine's approach, with referia-specific enhancements for handling review processes.

**See also**: :py:class:`referia.config.interface.Interface`, :py:class:`lynguine.config.interface.Interface`

Utility Functions
---------------

Referia uses many utility functions from lynguine directly, while adding its own domain-specific utilities:

- ``lynguine.util.*`` - Core utilities
- ``referia.util.*`` - Referia-specific utilities including text processing, file management, and visualization

Best Practices for Developers
---------------------------

When working with referia's codebase, keep these guidelines in mind:

1. **Check parent class first**: When using a method from a referia class that inherits from lynguine, check the parent class documentation to understand the base functionality.

2. **Docstring references**: Docstrings in referia should reference the parent class methods when extending functionality.

3. **Parameter consistency**: When overriding methods, maintain the same parameter names and types as the parent class to ensure compatibility.

4. **Method signatures**: Ensure that overridden methods match the signatures of the parent methods to prevent unexpected behavior.

5. **Clear documentation**: Always document when functionality is inherited vs. referia-specific to help other developers navigate the codebase. 