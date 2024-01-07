# referia


![Tests](https://github.com/lawrennd/referia/actions/workflows/python-tests.yml/badge.svg)

[![codecov](https://codecov.io/gh/lawrennd/referia/branch/main/graph/badge.svg?token=YOUR_CODECOV_TOKEN)](https://codecov.io/gh/lawrennd/referia)


The referia library provides tools for assisting with assessment, originally written as an aide for 2021 REF Assessment, code has gone through many addtions and then a major restructuring for version 0.2.0

The library uses jupyter notebook as an interface. 

To install use

%pip install referia

Configuration is stored in a local file, _referia.yml

This file provides the source and format of input data (for assessment), the location and format of annotations to store on the assessment as well of details of how to view files and urls associated with the assessment.

The configuration has the following fields

allocation

This contains the primary information of data to be assessed.

additional

This contains additional secondary information to be merged with the primary information. An array of entries can be include.

scores

This specifies how the annotation information is to be stored.

series

This specifies how to store annotation information which is available with a subindex (such as a time series).


