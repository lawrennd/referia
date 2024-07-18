# referia


![Tests](https://github.com/lawrennd/referia/actions/workflows/python-tests.yml/badge.svg)

[![codecov](https://codecov.io/gh/lawrennd/referia/branch/main/graph/badge.svg?token=YOUR_CODECOV_TOKEN)](https://codecov.io/gh/lawrennd/referia)


The referia library provides tools for assisting with assessment, originally written as an aide for 2021 REF Assessment, code has gone through many addtions and then a major restructuring for version 0.2.0

The library uses jupyter notebook as an interface. 

The library builds on functionality provided in the [`lynguine`](https://github.com/lawrennd/lynguine/) data oriented architecture library. The main difference between the two is that functionality that is general for the flow-based model the code follows sits in `lynguine`. The `referia` code is the place where functionality that is specific to interacting with the data (such as reviewing) is provided. 

To install use

```python
%pip install referia
```

Configuration is stored in a local file, `_referia.yml`.

This file provides the source and format of input data (for assessment), the location and format of annotations to store on the assessment as well of details of how to view files and urls associated with the assessment.

The configuration has the following fields

`allocation`

This contains the primary information of data to be assessed.

`additional`

This contains additional secondary information to be merged with the primary information. An array of entries can be include.

`viewer`

Provides information at the top of the score sheet that gives background (for example reviewing instructions).

`editpdf`

Lists pdfs to copy and allow the user to edit (for example to make notes on a submitted thesis).

Subfields are `field` which contains the filename, `sourcedirectory` and `storedirectory`. Also provides ability to specify `pages` from the source, so that we have something like

```yaml
field: ColumnName0
sourcedirectory: ./
pages:
  first: ColumnName1
  last: ColumnName2
storedirectory: ./pdfs
```

Functionality is provided in `system.Sys.edit_files`.

`urls` 

Lists urls that should be opened for providing additional information on the review.


`scores`

This specifies how the annotation information is to be stored.

`scored`

Specifies how the code should "count up" how many reviews are complete.

`series`

This specifies how to store annotation information which is available with a subindex (such as a time series).


`compute`

Specifies fields that should be filled in by computations. 

`documents`

Allows for the creation of documents (such as word docx or emails) that summarise the provided information.

`summary_documents`

Similar to documents, but this section provides documents that summarise all the data. Can be useful for summarising a sequence of reviews.

