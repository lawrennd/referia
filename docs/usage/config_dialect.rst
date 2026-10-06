Config dialects and versioning
==============================

Every ``_referia.yml`` belongs to a **config dialect** generation. Referia
detects the dialect, converts convenience keys in memory on load, and can
stamp or rewrite files on disk when you ask.

This is independent of the referia *package* version. Dialect ``2`` can run
under package ``0.x``.

Version field
-------------

Declare the dialect at the top of the file:

.. code-block:: yaml

   referia_config_version: 2

   input:
     type: excel
     filename: candidates.xlsx
     index: Name

   review:
     - field: Score
       type: IntSlider

Rules:

* Integer generations only (not semver).
* Current supported generation: **2**.
* Loading never writes the field back; use ``referia migrate`` to stamp or
  rewrite on disk.
* After the living corpus is stamped, missing versions warn on load / check,
  and later raise unless ``--allow-unversioned`` is used.

Dialect generations
-------------------

======= ============================================================ =============================
Version On-disk markers                                              Load behaviour
======= ============================================================ =============================
**v0**  Proto ``_config.yml`` (e.g. ``allocation:`` as a filename)   Reported only; not normalised
**v1**  ``allocation``, ``scores``, ``scorer``, ``globals``, …       Normalised in memory to v2 keys
**v2**  ``input``, ``output``, ``review``, ``constants``, …          Canonical; no key rewrite
======= ============================================================ =============================

Mixing the same slot in both dialects (``allocation`` with ``input``,
``scores`` with ``output``, ``scorer`` with ``review``) is an error.

In-memory key mapping (v1 → v2)
-------------------------------

On every load of a v1 file, ``Interface`` applies:

* ``allocation`` (+ ``additional``) → ``input``
* ``scores`` → ``output``
* ``scorer`` → ``review``
* ``global_consts`` → ``constants``
* ``globals`` → ``parameters``
* ``converters`` → ``dtypes`` on data specs

Widget composites stay unexpanded on disk; expansion remains a runtime
convenience.

``strict_columns`` defaults
---------------------------

When ``strict_columns`` is omitted:

* **v1** → permissive (``false``) — legacy Excel sheets often have extra or
  duplicate headers
* **v2** → strict (``true``) — opt out with ``strict_columns: false``

An explicit ``strict_columns`` value in YAML always wins.

.. note::

   End-to-end enforcement on the main ``from_flow`` input path also depends
   on lynguine not forcing ``strict_columns=False``. Referia's dialect
   helpers and ``_finalize_df`` already honour the table above.

CLI: check and migrate
----------------------

Lint YAML and report dialect (no Excel / path access required)::

   referia check --root PATH
   referia check --root PATH --format json

Migrate is **dry-run by default**. Add ``--write`` to change files::

   # Insert referia_config_version only (keeps comments and key order)
   referia migrate --root PATH --stamp-only
   referia migrate --root PATH --stamp-only --write

   # Rewrite v1 keys to v2 (may lose comments; prefer sibling .migrated.yml)
   referia migrate --root PATH
   referia migrate --root PATH --write
   referia migrate --root PATH --write --in-place   # .bak backup

Stamp-only skips files that already declare a version and reports v0 proto
files without rewriting them.

Runtime vs disk
---------------

==================== ============================ =============
Action               When                         Writes files?
==================== ============================ =============
Detect               ``check``, ``migrate``, load No
Normalise in memory  Every v1 ``Interface`` load  No
Stamp-only           ``migrate --stamp-only --write`` Yes, opt-in
Full key rewrite     ``migrate --write``          Yes, opt-in
==================== ============================ =============

Library API
-----------

.. code-block:: python

   from referia.config.dialect import (
       detect_config_dialect,
       normalise_referia_config,
       SUPPORTED_CONFIG_VERSION,
   )

   report = detect_config_dialect(raw_dict)
   # report.version_declared, report.version_inferred, report.markers, …

See also :doc:`../modules/config` for ``Interface`` and the dialect module
API reference.
