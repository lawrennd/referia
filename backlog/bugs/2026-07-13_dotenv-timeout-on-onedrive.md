---
id: "2026-07-13_dotenv-timeout-on-onedrive"
title: "Fix TimeoutError when loading .env file on OneDrive filesystem"
status: "Completed"
priority: "High"
created: "2026-07-13"
last_updated: "2026-07-13"
category: "bugs"
related_cips: []
owner: "neil"
dependencies: []
tags:
- backlog
- llm
- dotenv
- onedrive
- import
---

# Task: Fix TimeoutError when loading .env file on OneDrive filesystem

## Description

`import referia` raised a `TimeoutError: [Errno 60] Operation timed out` in
Jupyter when the working directory was inside an OneDrive-synced folder.

The call chain was:

```
import referia
  → referia/assess/compute.py
    → referia/util/llm.py
      → load_dotenv()          ← no path given
        → find_dotenv()        ← walks directory tree
          → stream.read()      ← [Errno 60] ETIMEDOUT
```

**Root cause**: On macOS, OneDrive exposes files via Apple's FileProvider kernel
extension. Every `open()` call under `~/Library/CloudStorage/OneDrive-*` passes
through the FileProvider daemon, which makes a network round-trip to validate the
file state before returning data. Even files marked "downloaded locally" (green
tick in Finder) are affected. If that round-trip times out, Python raises
`TimeoutError` (a subclass of `OSError`).

The original `except ImportError` around `load_dotenv` only guarded against
python-dotenv not being installed — it did not catch filesystem errors.

## Acceptance Criteria

- [x] `import referia` succeeds without raising an exception when the CWD is on
  OneDrive and the `.env` file cannot be read
- [x] API keys are still loaded when a `.env` file exists at a genuinely local
  path (not on a network-backed filesystem)
- [x] `~/.env` is tried as a local fallback when `find_dotenv()` times out or
  finds nothing
- [x] Test coverage for all four scenarios: timeout in find_dotenv, timeout in
  load_dotenv, normal success, and ~/.env fallback

## Implementation Notes

Changes in `referia/util/llm.py`:

1. Separated `find_dotenv()` from `load_dotenv()` so both can be individually
   guarded.
2. Wrapped both calls in `except OSError` (`TimeoutError` is a subclass).
3. Added a fallback: if `find_dotenv` fails or returns nothing, try `~/.env`
   (always on a local APFS filesystem, never routed through OneDrive).

**User action required**: copy API keys into `~/.env` so they are on a local
filesystem:

```bash
echo 'OPENAI_API_KEY=sk-...' >> ~/.env
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> ~/.env
chmod 600 ~/.env
```

Test file added: `tests/test_llm_import.py`

## Related

- PRs: n/a (direct commit)
- Documentation: `referia/util/llm.py` module docstring

## Progress Updates

### 2026-07-13

Bug reported: `TimeoutError` on `import referia` in Jupyter (OneDrive CWD).

Fix implemented in `referia/util/llm.py`:
- Catch `OSError` around `find_dotenv()` and `load_dotenv()`
- Add `~/.env` fallback for local API key storage
- Add 8 regression tests in `tests/test_llm_import.py`

Status set to Completed.
