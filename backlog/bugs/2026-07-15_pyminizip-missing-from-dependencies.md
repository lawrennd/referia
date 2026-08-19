---
id: "2026-07-15_pyminizip-missing-from-dependencies"
title: "Orphaned pyminizip import in system.py causes CI test collection failure"
status: "Completed"
priority: "High"
created: "2026-07-15"
last_updated: "2026-07-15"
related_cips: []
tags: ["ci", "dependencies", "pyminizip", "poetry", "test-collection"]
---

# Bug: Orphaned pyminizip import in system.py causes CI test collection failure

## Status

- [x] Identified
- [x] Root-cause confirmed
- [x] Fixed
- [ ] Regression tests added
- [ ] Closed

## Summary

All 10 test modules fail to collect during CI because `referia/system.py` still contains
an unconditional top-level import of `pyminizip`, which was **deliberately removed from
`pyproject.toml` in commit `e0c274b` ("Add some documentation", 2024-01-01)**.
The import in `system.py` was never cleaned up when the dependency was dropped.

The import chain is:

```
referia/__init__.py → referia/display.py → referia/system.py:13 → import pyminizip as pz
```

Since `referia/__init__.py` triggers the import on package load, every test module that
imports anything from `referia` immediately raises `ModuleNotFoundError: No module named 'pyminizip'`.

## Symptoms

- `pytest` collection exits with 10 errors and exit code 2.
- No tests run at all; coverage report is empty.
- Error appears in every test file regardless of which sub-module it imports.

## Affected Tests

All 10 collected test modules failed:

- `referia/tests/test_assess_compute.py`
- `referia/tests/test_assess_data.py`
- `referia/tests/test_assess_data_compute.py`
- `referia/tests/test_util_text.py`
- `referia/tests/test_util_widgets.py`
- `tests/test_conditional_visibility.py`
- `tests/test_from_flow_mapping_timing.py`
- `tests/test_implicit_mapping_behavior.py`
- `tests/test_web_render.py`
- `tests/test_web_routes.py`

## Root Cause

`pyminizip` was **intentionally removed from `pyproject.toml`** in commit `e0c274b`
("Add some documentation", 2024-01-01), along with several other dependencies
(`python-frontmatter`, `google-api-python-client`, `google-auth-httplib2`, `gspread`,
`mimesis`, `wget`). The removal was part of a dependency cleanup during the `ndlpy` →
`lynguine` migration era.

However, the import was never removed from `referia/system.py`. The only usage of
`pyminizip` in the codebase is `write_zip()` at line 296–298:

```python
def write_zip(self, filename=None, password=None, filelist=None, directorylist=[], compress=4):
    """Write a zip file using pyminizip"""
    pz.compress_multiple(filelist, directorylist, filename, password, compress)
```

Because the top-level `import pyminizip as pz` at line 13 runs unconditionally on
package import, the entire package becomes un-importable in any environment where
`pyminizip` is not installed — including all CI runners.

## Traceback (representative example)

```
referia/tests/test_assess_compute.py:2: in <module>
    from referia.assess.compute import Compute
referia/__init__.py:2: in <module>
    from . import display
referia/display.py:7: in <module>
    from . import system
referia/system.py:13: in <module>
    import pyminizip as pz
E   ModuleNotFoundError: No module named 'pyminizip'
```

## Fix Options

Since `pyminizip` was deliberately dropped, **do not simply add it back**.  The correct
fix is to remove the orphaned import and replace the one call site with stdlib `zipfile`
(which supports password-protected zips since Python 3.9 via `zipfile.ZipFile` with
`pwd=`).

### Preferred fix — replace with stdlib `zipfile`

1. Remove `import pyminizip as pz` from `referia/system.py` line 13.
2. Rewrite `write_zip()` to use `zipfile.ZipFile`:

   ```python
   import zipfile

   def write_zip(self, filename=None, password=None, filelist=None, directorylist=[], compress=4):
       """Write a zip file."""
       with zipfile.ZipFile(filename, "w", compression=zipfile.ZIP_DEFLATED,
                            compresslevel=compress) as zf:
           if password:
               zf.setpassword(password.encode())
           for src, arcdir in zip(filelist, directorylist or [""] * len(filelist)):
               arcname = os.path.join(arcdir, os.path.basename(src)) if arcdir else os.path.basename(src)
               zf.write(src, arcname)
   ```

   Note: `zipfile` encryption is read-only in Python's stdlib — it can _read_
   password-protected zips but cannot _write_ them.  If write-encryption is genuinely
   required, the alternative is `pyzipper` (actively maintained, pure-Python AES).

### Alternative — lazy import with clear error

If removing `pyminizip` is not immediately feasible, guard the import:

```python
try:
    import pyminizip as pz
    _PYMINIZIP_AVAILABLE = True
except ImportError:
    pz = None
    _PYMINIZIP_AVAILABLE = False
```

And raise `ImportError` with a clear message inside `write_zip()` when
`_PYMINIZIP_AVAILABLE is False`.  This unblocks all tests that do not exercise
`write_zip()`.

## Acceptance Criteria

- [ ] `import pyminizip` no longer appears as a top-level unconditional import.
- [ ] `poetry run pytest` collects all 10 test modules without `ModuleNotFoundError`.
- [ ] CI passes on the next push.
- [ ] `write_zip()` still works correctly (or raises a clear error if pyminizip is absent).

## CI Context

- **Runner**: `macos-26-arm64` (GitHub Actions, 2026-07-14)
- **Python**: 3.11.9
- **Poetry**: 2.4.1
- **Commit**: `4b5004e67384dba97c881856ef3d7f2c9e955a1e`
- **Failure timestamp**: `2026-07-14T21:55:09`

## Progress Updates

### 2026-07-15
Bug identified from CI log. `pyminizip` is imported unconditionally in `referia/system.py`
but is absent from `pyproject.toml`. Created this backlog entry.

Updated after checking git history: `pyminizip` was deliberately removed from
`pyproject.toml` in commit `e0c274b` (2024-01-01) as part of a dependency cleanup, but
the import in `system.py` was never removed. Fix should remove/replace the import, not
re-add the dependency.

### 2026-07-16
Implemented fix option 1. Replaced `import pyminizip as pz` with `import zipfile` in
`referia/system.py`. Rewrote `write_zip()` to use `zipfile.ZipFile` (stdlib). Password
encryption is not supported by the stdlib module — a `NotImplementedError` is raised if
`password` is supplied, with a clear message pointing to `pyzipper` as the alternative.
No uses of password-protected zips were found in the active codebase.
