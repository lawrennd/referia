Catalog schedule, Today, and Year
=================================

A catalog root (``display.layout: inline_list`` over a
``yaml_directory`` of descendant ``_referia.yml`` files) can own
**when work is due or happens**, independently of each leaf file's
identity ``date``.

This is the user guide distilled from CIP-001C. Discovery bind and
path ``exclude`` live in lynguine (CIP-0018); referia adds
``inherit.reuse``, grouping, and the ``when`` / ``on_today`` view.

Store vs view
-------------

The writable store is the root tall score file (typically
``info/catalog-scores.yml``), keyed by ``configPath``. Extra columns
beside ``complete``:

========== ========================================================
Column     Meaning
========== ========================================================
``due``    Complete-by (DatePicker stores ``YYYYMMDD``)
``event``  Happens-on (interview day, meeting day)
``notes``  Short progress line
========== ========================================================

Leaf ``date`` stays identity (opened / cohort). Leftover leaf ``due:``
is a seed, not authority, once the score row has a value.

Two **view** columns are derived in ``WebReviewer.get_value`` (and
injected into ``get_row_data``). They are **not** ``input.compute``
fields: that compute runs on the yaml_directory partition *before*
scores join, so ``event`` / ``due`` are not yet there.

======= ===========================================================
Column  Rule
======= ===========================================================
``when``     ``event`` if set, else ``due``
``on_today`` ``true`` when ``event`` **or** ``due`` equals ``today``
======= ===========================================================

DatePicker cells and ISO ``today`` are normalised to eight digits
before comparison. Seasonal windows and Year sort use ``when``. Today
filters on ``on_today`` so a row due today still shows if its event is
later.

Sibling Today and Year
----------------------

``GET /today/`` and ``GET /year/`` are ordinary directory configs
(CIP-000C). They share discovery, scores, widgets, filters, and sort
with the parent, and only change chrome.

Referia still force-appends ``compute`` and ``review`` to
``inherit.ignore`` (candidate reviews rely on that). Catalog views
opt in with ``inherit.reuse`` after those defaults:

.. code-block:: yaml

   writable: true
   inherit:
     directory: ../
     filename: _referia.yml
     writable: true
     reuse: [input, output, compute, review, filters, sort]
     ignore: [viewer]

``reuse`` removes listed keys from ignore. ``ignore: [viewer]`` keeps
child chrome and skips the parent-assessor link. Omit ``reuse`` and
inherit behaves as before.

Both top-level ``writable: true`` and ``inherit.writable: true`` are
required so Save writes the parent's score file.

Typical chrome:

* **Today** — ``on_today: true``, ``complete: false``, ``_group: none``
* **Year** — academic-year window on ``when`` (Cambridge 1 Oct–30 Sep
  as ISO dates in the year config), ``_group: month``
* **Seasonal root** — ``when: today-30d … today+30d``, ``_group: directory``

Do not list the views as work. On the catalog source, set
``exclude: [today/**, year/**]`` (lynguine CIP-0018) together with
``include_start_directory: false``. Inherited ``directory: .`` /
``glob`` specs bind to the parent catalog directory, so Today still
discovers from the root.

Grouping
--------

``_group`` on an ``inline_list`` accepts ``directory`` (default),
``version``, ``month`` (from ``when``, ``YYYY-MM``), and ``none``
(flat). Unknown values still fall back to ``directory``.

Example
-------

``examples/overview_inline_list/`` is a miniature catalog with
``today/`` and ``year/`` siblings and tall scores in
``info/overview-scores.yml``.

.. code-block:: bash

   referia serve --directory examples/overview_inline_list

Talks and other git roots remain a **separate** ``referia serve --root``.
This guide does not federate them into the catalog tree.
