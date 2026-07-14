"""Tests for referia.util.llm import robustness.

Regression test for the TimeoutError that occurred when importing referia in
Jupyter while the working directory was on a network filesystem (e.g. OneDrive).

``load_dotenv()`` called with no arguments internally invokes ``find_dotenv()``,
which walks up the directory tree looking for a ``.env`` file.  On a network
mount that walk (or the subsequent file read) can raise ``TimeoutError``
(a subclass of ``OSError``).  The fix wraps the dotenv operations in an
``except OSError`` guard so that the import succeeds even when the filesystem
is unavailable.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


# Path to the module under test — loaded in isolation so this test file does
# not pull in the full referia package chain (which requires optional
# dependencies like wordcloud that may not be installed in the test env).
_LLM_PATH = Path(__file__).parent.parent / "referia" / "util" / "llm.py"
_MODULE_NAME = "_test_referia_util_llm"


def _load_llm_module():
    """Import referia/util/llm.py in isolation and return the module object.

    Using spec_from_file_location avoids triggering the full referia package
    import chain, which has optional dependencies (wordcloud etc.) that may
    not be installed in CI.
    """
    # Remove any stale copy so module-level code re-executes.
    sys.modules.pop(_MODULE_NAME, None)
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, _LLM_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = mod
    spec.loader.exec_module(mod)
    return mod


class TestLlmImportWithDotenvTimeout:
    def test_import_succeeds_when_find_dotenv_raises_timeout(self):
        """A TimeoutError from find_dotenv must not prevent the module from loading."""
        with patch("dotenv.find_dotenv", side_effect=TimeoutError("[Errno 60] Operation timed out")):
            mod = _load_llm_module()
        # dotenv package is importable; only the .env load failed.
        assert mod.DOTENV_AVAILABLE is True

    def test_import_succeeds_when_load_dotenv_raises_timeout(self):
        """A TimeoutError while reading the .env file must not prevent loading."""
        with patch("dotenv.find_dotenv", return_value="/some/network/path/.env"), \
             patch("dotenv.load_dotenv", side_effect=TimeoutError("[Errno 60] Operation timed out")):
            mod = _load_llm_module()
        assert mod.DOTENV_AVAILABLE is True

    def test_import_succeeds_when_find_dotenv_raises_oserror(self):
        """Any OSError subclass from find_dotenv is caught gracefully."""
        with patch("dotenv.find_dotenv", side_effect=OSError("network failure")):
            mod = _load_llm_module()
        assert mod.DOTENV_AVAILABLE is True

    def test_dotenv_loaded_normally_when_file_exists(self):
        """When find_dotenv returns a path and load_dotenv succeeds, it is called."""
        load_mock = MagicMock()
        with patch("dotenv.find_dotenv", return_value="/some/.env"), \
             patch("dotenv.load_dotenv", load_mock):
            _load_llm_module()
        load_mock.assert_called_once_with(dotenv_path="/some/.env", verbose=False)

    def test_load_dotenv_not_called_when_no_env_file_found(self):
        """When find_dotenv returns '' (not found), load_dotenv is not called."""
        load_mock = MagicMock()
        with patch("dotenv.find_dotenv", return_value=""), \
             patch("dotenv.load_dotenv", load_mock), \
             patch("os.path.isfile", return_value=False):
            _load_llm_module()
        load_mock.assert_not_called()

    def test_fallback_to_home_env_when_find_dotenv_times_out(self):
        """When find_dotenv times out, ~/.env is tried as a local fallback."""
        load_mock = MagicMock()
        home_env = str(Path.home() / ".env")
        with patch("dotenv.find_dotenv", side_effect=TimeoutError("[Errno 60] Operation timed out")), \
             patch("dotenv.load_dotenv", load_mock), \
             patch("os.path.isfile", return_value=True):
            _load_llm_module()
        load_mock.assert_called_once_with(dotenv_path=home_env, verbose=False)

    def test_fallback_to_home_env_when_find_dotenv_returns_empty(self):
        """When find_dotenv finds nothing, ~/.env is tried as a local fallback."""
        load_mock = MagicMock()
        home_env = str(Path.home() / ".env")
        with patch("dotenv.find_dotenv", return_value=""), \
             patch("dotenv.load_dotenv", load_mock), \
             patch("os.path.isfile", return_value=True):
            _load_llm_module()
        load_mock.assert_called_once_with(dotenv_path=home_env, verbose=False)

    def test_home_env_oserror_still_allows_import(self):
        """Even if reading ~/.env raises OSError, the module still loads."""
        def _raise_on_home(dotenv_path, verbose):
            if ".env" in dotenv_path:
                raise OSError("still unreachable")
        with patch("dotenv.find_dotenv", return_value=""), \
             patch("dotenv.load_dotenv", side_effect=_raise_on_home), \
             patch("os.path.isfile", return_value=True):
            mod = _load_llm_module()
        assert mod.DOTENV_AVAILABLE is True
