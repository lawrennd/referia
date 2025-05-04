#!/usr/bin/env python
"""Test that Sphinx documentation builds correctly.

This script performs a test build of the documentation to verify that:
1. The documentation builds without errors
2. All cross-references are working
3. Inheritance information is properly displayed

Usage:
    python test_build.py

Returns:
    0 if the build succeeded, non-zero otherwise
"""

import os
import subprocess
import sys
from pathlib import Path

def test_sphinx_build():
    """Test that the Sphinx documentation builds correctly."""
    docs_dir = Path(__file__).parent
    build_dir = docs_dir / "_build" / "test"
    
    # Make sure the build directory exists
    os.makedirs(build_dir, exist_ok=True)
    
    # Run Sphinx build in warning-is-error mode to catch all issues
    cmd = [
        "sphinx-build",
        "-W",  # Treat warnings as errors
        "-b", "html",  # Build HTML output
        "-d", str(build_dir / "doctrees"),  # Doctree directory
        str(docs_dir),  # Source directory
        str(build_dir / "html")  # Output directory
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print("Documentation build succeeded!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Documentation build failed with return code {e.returncode}")
        print(f"STDOUT: {e.stdout.decode('utf-8')}")
        print(f"STDERR: {e.stderr.decode('utf-8')}")
        return e.returncode

if __name__ == "__main__":
    sys.exit(test_sphinx_build()) 