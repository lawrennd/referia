Contributing to Referia
====================

This guide provides information for developers who want to contribute to referia.

Development Setup
--------------

1. Clone both repositories:

   .. code-block:: bash

       git clone https://github.com/lawrennd/lynguine.git
       git clone https://github.com/lawrennd/referia.git

2. Install both packages in development mode:

   .. code-block:: bash

       cd lynguine
       poetry install
       
       cd ../referia
       poetry install

3. Run tests to ensure everything is working:

   .. code-block:: bash

       pytest

Code Structure
------------

Referia extends lynguine through inheritance:

- ``referia/assess/compute.py`` inherits from ``lynguine/assess/compute.py``
- ``referia/config/interface.py`` inherits from ``lynguine/config/interface.py``
- Many utility functions in referia build on lynguine's utilities

Documentation Standards
--------------------

When contributing to referia, follow these documentation standards:

1. **Class Documentation**:

   .. code-block:: python

       class MyClass(lynguine.SomeClass):
           """
           MyClass extends lynguine.SomeClass with additional functionality.
           
           This class inherits core methods X, Y, Z from the parent class
           and adds/overrides methods A, B, C.
           
           See :py:class:`lynguine.SomeClass` for inherited functionality.
           """

2. **Method Documentation**:

   .. code-block:: python

       def some_method(self, param1, param2):
           """
           Short description of method.
           
           This method extends the parent class method with additional functionality.
           
           :param param1: Description of parameter 1
           :type param1: type of parameter 1
           :param param2: Description of parameter 2
           :type param2: type of parameter 2
           :return: Description of return value
           :rtype: return type
           
           See :py:meth:`lynguine.SomeClass.some_method` for base implementation.
           """

3. **Overridden Methods**:

   .. code-block:: python

       def overridden_method(self, param1, param2):
           """
           Short description of overridden method.
           
           This method overrides the parent class implementation to [explain why].
           
           :param param1: Description of parameter 1
           :type param1: type of parameter 1
           :param param2: Description of parameter 2
           :type param2: type of parameter 2
           :return: Description of return value
           :rtype: return type
           
           Overrides: :py:meth:`lynguine.SomeClass.overridden_method`
           """

Inheritance Guidelines
-------------------

When extending classes from lynguine:

1. **Maintain Parameter Compatibility**: Keep the same parameter names and order as the parent class

2. **Document Inheritance**: Clearly document which functionality is inherited vs. extended

3. **Use super() Properly**: Call the parent class methods when appropriate:

   .. code-block:: python
   
       def extended_method(self, param1, param2):
           # Call parent implementation first
           result = super().extended_method(param1, param2)
           
           # Add referia-specific functionality
           enhanced_result = self._enhance_result(result)
           
           return enhanced_result

4. **Match Return Types**: Keep return values compatible with parent class methods

5. **Test Inheritance**: Test both the inherited functionality and your extensions

Working with Both Codebases
-------------------------

When developing features that span both referia and lynguine:

1. **Understand the Division**: Decide whether functionality belongs in lynguine (core) or referia (review-specific)

2. **Coordinate Changes**: If you need to modify lynguine, make those changes first

3. **Test Integration**: Test that referia properly inherits and extends lynguine's changes

Pull Request Process
-----------------

1. Create a feature branch for your changes
2. Ensure all tests pass
3. Update documentation following the standards above
4. Submit a pull request with a clear description of changes
5. Respond to code review feedback

Building Documentation
------------------

To build the documentation:

.. code-block:: bash

    cd docs
    make html

The documentation system uses Sphinx with:

- Autodoc for API documentation
- Intersphinx for linking to lynguine documentation
- napoleon for parsing Google/NumPy style docstrings 