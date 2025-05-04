Utility Modules
==============

The ``util`` package contains various utility functions and classes used throughout referia.
Some of these utilities extend functionality from lynguine, while others are specific to referia.

.. contents:: Contents
   :local:
   :depth: 2

Text Utilities
-------------

.. automodule:: referia.util.text
   :members:
   :undoc-members:
   :show-inheritance:

Text utilities in referia extend the base functionality provided by ``lynguine.util.text``. 
Key referia-specific text processing functions include:

- Word counting and text analysis
- Document summarization
- Paragraph and sentence splitting
- Named entity recognition

For lynguine text utilities, see: :py:mod:`lynguine.util.text`.

File Utilities
------------

.. automodule:: referia.util.files
   :members:
   :undoc-members:
   :show-inheritance:

The file utilities specific to referia provide functions for:

- Finding files by regex pattern
- File management operations specific to reviews
- Document extraction

Plotting Utilities
---------------

.. automodule:: referia.util.plot
   :members:
   :undoc-members:
   :show-inheritance:

Referia-specific visualization functions include:

- Bar plots for review metrics
- Histograms for data visualization
- Custom plots for assessment metrics

Miscellaneous Utilities
--------------------

.. automodule:: referia.util.misc
   :members:
   :undoc-members:
   :show-inheritance:

Referia extends lynguine's base utilities with additional functions for:

- Working with numeric data
- String operations specific to review processes
- Helper functions for common operations

For lynguine misc utilities, see: :py:mod:`lynguine.util.misc`.

System Utilities
--------------

.. automodule:: referia.util.system
   :members:
   :undoc-members:
   :show-inheritance:

System utilities specific to referia include:

- Screen capture functionality
- System integration functions

Widget Utilities
-------------

.. automodule:: referia.util.widgets
   :members:
   :undoc-members:
   :show-inheritance:

Widget utilities are specific to referia and include:

- Custom widgets for user interfaces
- Interactive components for applications

Relationship with Lynguine Utilities
---------------------------------

Referia often extends lynguine's utilities or adds domain-specific functionality:

.. code-block:: text

    lynguine.util.text
        ↑
        ├── (used by) referia.util.text

    lynguine.util.misc
        ↑
        ├── (used by) referia.util.misc

In general, referia uses lynguine's utility functions where available and implements additional
functionality specific to review processes when needed. 