# -- Path setup --------------------------------------------------------------

import os
import sys
import tomllib
from pathlib import Path

# Assuming your docs are in a 'docs' folder at the root of your project
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Load the project metadata from the pyproject.toml file (PEP 621)
with (root_dir / "pyproject.toml").open("rb") as f:
    project_metadata = tomllib.load(f)["project"]

# -- Project information -----------------------------------------------------

project = project_metadata["name"]
_authors = project_metadata.get("authors") or []
if _authors and isinstance(_authors[0], dict):
    author = _authors[0].get("name") or _authors[0].get("email") or "Unknown"
else:
    author = str(_authors[0]) if _authors else "Unknown"
copyright = f"2023, {author}"

release = project_metadata["version"]
version = ".".join(release.split(".")[:2])  # Major.Minor version

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.coverage',
    'sphinx.ext.intersphinx',
    'sphinx.ext.graphviz',
    'sphinx.ext.inheritance_diagram',
    'myst_parser',  # For Markdown support
]

# Extension settings
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pandas': ('https://pandas.pydata.org/pandas-docs/stable', None),
    'numpy': ('https://numpy.org/doc/stable', None),
}

autodoc_member_order = 'bysource'  # Keep the same order as in the source file
autodoc_typehints = 'description'  # Put type hints in the description
autoclass_content = 'both'  # Include both class and __init__ docstrings
autodoc_inherit_docstrings = True  # Show docstrings of inherited methods

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '.ipynb_checkpoints']

# MyST settings for Markdown support
myst_enable_extensions = [
    'colon_fence',
    'deflist',
]
source_suffix = ['.rst', '.md']

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'  # Use the Read the Docs theme
html_static_path = ['_static']
html_title = f"{project} {version} Documentation"

# Theme options
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
}

# -- Extension configuration -------------------------------------------------
# This tells Sphinx to show the full module names on the API docs
add_module_names = True

# -- Additional referia-specific settings ----------------------------------------
# This section is for settings specific to referia documentation

# Show inheritance diagram for classes
inheritance_graph_attrs = {
    'rankdir': 'TB',  # Top to bottom layout
    'size': '"6.0, 8.0"',
}
inheritance_node_attrs = {
    'shape': 'box',
    'fontsize': 10,
    'height': 0.50,
    'margin': '"0.1,0.1"',
}

# Add the 'show-inheritance' flag to autodoc directives by default
autodoc_default_options = {
    'show-inheritance': True,
    'members': True,
    'inherited-members': True,
    'undoc-members': True,
}
