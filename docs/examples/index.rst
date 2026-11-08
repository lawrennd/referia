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

The inventory and triage notes also live in ``examples/README.md``.

Serveable demos
---------------

==================================== =========================================================== ================================================
Directory                            Purpose                                                     Launch
==================================== =========================================================== ================================================
``examples/overview_inline_list/``   Catalog / ``inline_list`` with Today and Year siblings       ``--directory examples/overview_inline_list``
``examples/topic_scatter_click/``    Plotly click ↔ review field sync                             ``--directory examples/topic_scatter_click``
``examples/subject_grain_uq/``       Soft MPPCA subject grain (bake scores first)                 ``--directory examples/subject_grain_uq``
``examples/numeric_scoring/``        Offline ``multiply`` / ``add`` / ``gte`` scoring             ``--directory examples/numeric_scoring``
==================================== =========================================================== ================================================

Each directory has a ``README.md`` with layout notes and what to verify.
The catalog schedule guide documents the overview demo in more depth:
:doc:`../usage/catalog_schedule`. Numeric primitives are documented in
:doc:`../usage/compute`.

LLM and thesis snippets
-----------------------

These files are **snippets**, not drop-in ``--directory`` demos. Copy
patterns into a real review tree, then serve that directory.

* ``examples/llm_integration_example.yml`` — declarative LLM compute
* ``examples/thesis_llm_review_example.yml`` — ``llm_pdf_review`` PopulateButtons
* ``examples/llm_usage_example.py`` / ``thesis_llm_review_example.py`` —
  optional Python API illustrations
* ``examples/env_template.txt`` — copy to package-root ``.env`` for keys

Guides: ``docs/llm_integration.md``, ``docs/llm_pdf_review.md``.

Retired artefacts
-----------------

``docs/examples/test_referia.ipynb`` and ``test_compute.ipynb`` (plus
``.ipynb_checkpoints/``) were local pytest scratchpads with hardcoded
developer paths. They were removed in CIP-0026 Phase C. Use the
serveable demos above; unit tests live under ``tests/``.
