"""Web display backend for referia review interfaces.

Provides a FastAPI-based rendering target that serves review sessions as
ordinary web pages, without requiring a Jupyter kernel. The config
(Interface) and data (CustomDataFrame) layers are shared with the Jupyter
backend; only the rendering layer differs.

Entry point: ``referia serve`` (see ``referia.cli``).
"""
