Installation
============

This guide covers how to install referia and its dependencies, including lynguine.

Prerequisites
-----------

Referia requires:

- Python 3.8 or higher
- The lynguine package
- Several other Python packages as listed in the dependencies

Installation from Source
---------------------

1. Clone the referia repository:

   .. code-block:: bash

       git clone https://github.com/lawrennd/referia.git
       cd referia

2. Install referia and its dependencies using Poetry:

   .. code-block:: bash

       poetry install

   This will install all the required dependencies, including lynguine.

Installation with pip
------------------

Alternatively, you can install referia using pip:

.. code-block:: bash

    pip install referia

This will automatically install lynguine and other dependencies.

Development Installation
---------------------

For development, you may want to install referia in development mode:

1. Clone both repositories:

   .. code-block:: bash

       git clone https://github.com/lawrennd/lynguine.git
       git clone https://github.com/lawrennd/referia.git

2. Install lynguine in development mode:

   .. code-block:: bash

       cd lynguine
       poetry install

3. Install referia in development mode:

   .. code-block:: bash

       cd ../referia
       poetry install

Verifying the Installation
-----------------------

You can verify that referia is installed correctly by running:

.. code-block:: python

    import referia
    import lynguine
    
    print(f"Referia version: {referia.__version__}")
    print(f"Lynguine version: {lynguine.__version__}")

Dependencies
----------

Referia depends on the following major packages:

- **lynguine**: Core framework for data handling and computation
- **pandas**: Data analysis and manipulation
- **numpy**: Numerical operations
- **matplotlib**: Plotting and visualisation
- **sphinx**: For building documentation

The complete list of dependencies can be found in the ``pyproject.toml`` file. 