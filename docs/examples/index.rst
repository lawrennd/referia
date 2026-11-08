Package examples
================

Runnable demos live under ``examples/`` in the referia repository. The
canonical way to open a demo is ``referia serve`` from a poetry
environment at the package root:

.. code-block:: bash

   poetry install   # once
   poetry run referia serve --directory examples/<name>
   # Open the printed URL (default http://127.0.0.1:8000)

Use ``poetry run referia serve --root <path>`` when the point is a
multi-config host that discovers several ``_referia.yml`` trees.

Serveable demos
---------------

==================================== =========================================================== ================================================
Directory                            Purpose                                                     Launch
==================================== =========================================================== ================================================
``examples/overview_inline_list/``   Catalog / ``inline_list`` with Today and Year siblings       ``--directory examples/overview_inline_list``
``examples/topic_scatter_click/``    Plotly click ↔ review field sync                             ``--directory examples/topic_scatter_click``
``examples/subject_grain_uq/``       Soft MPPCA subject grain (bake scores first)                 ``--directory examples/subject_grain_uq``
==================================== =========================================================== ================================================

Each directory has a ``README.md`` with layout notes and what to verify.
The catalog schedule guide documents the overview demo in more depth:
:doc:`../usage/catalog_schedule`.

Numeric scoring
---------------

A miniature offline scoring demo (``examples/numeric_scoring/``) is
planned under CIP-0026 Phase B, once YAML numeric compute primitives
(``add`` / ``multiply`` / ``gte``, …) land. It will be linked from
:doc:`../usage/compute` when available.

LLM and thesis snippets
-----------------------

YAML and Python files under ``examples/`` (``llm_*.yml`` /
``llm_*.py``, ``thesis_llm_review_example.*``) illustrate declarative
LLM compute and the Python API. Prefer a serveable ``_referia.yml``
directory when learning the reviewer UI; treat the ``.py`` scripts as
optional API illustrations. Env setup: ``examples/env_template.txt``.
See also ``docs/llm_integration.md`` and ``docs/llm_pdf_review.md``.

Legacy notebooks
----------------

``docs/examples/test_referia.ipynb`` and ``test_compute.ipynb`` are
legacy Jupyter paths. Prefer the serveable demos above; notebook triage
is CIP-0026 Phase C.
