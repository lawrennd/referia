Configuration Module
===================

The ``config`` module provides configuration and interface functionality for referia.
It extends the configuration system from lynguine with referia-specific functionality.

.. contents:: Contents
   :local:
   :depth: 2

Interface
--------

.. autoclass:: referia.config.interface.Interface
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:

The ``Interface`` class extends lynguine's interface system with additional functionality for handling:

- Review-specific configuration
- Assessment settings
- Document management

For details on the base functionality, see :py:class:`lynguine.config.interface.Interface`.

Inheritance Relationship
---------------------

The configuration system in referia inherits from and extends lynguine's approach:

.. code-block:: text

    lynguine.config.interface.Interface
        ↑
        └── referia.config.interface.Interface

    lynguine.config.context.Context
        ↑
        └── (used directly in referia)

The configuration system uses the Context class from lynguine directly, while extending the
Interface class to add referia-specific functionality.

Configuration File Format
----------------------

Referia configuration files follow the same format as lynguine configurations, with additional
fields specific to review processes:

.. code-block:: yaml

    # Base configuration (inherited from lynguine)
    input:
      type: file
      file: data.csv
      
    # Referia-specific configuration
    review:
      criteria:
        - name: clarity
          weight: 0.3
        - name: methodology
          weight: 0.4
        - name: impact
          weight: 0.3

Usage Example
-----------

.. code-block:: python

    from referia.config.interface import Interface
    
    # Load a configuration file
    interface = Interface.from_file("config.yml")
    
    # Access configuration values
    input_config = interface["input"]
    review_config = interface["review"] 