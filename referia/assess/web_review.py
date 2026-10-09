"""Stateful review session for the referia web display backend.

``WebReviewer`` wraps ``Interface`` and ``CustomDataFrame`` to provide the same
core review semantics as ``Reviewer`` without any ipywidgets dependency.  It is
the data/logic layer consumed by the FastAPI routes in ``referia.web.app``.

Public API
----------
WebReviewer(user_file, directory)
    Construct from a ``_referia.yml`` configuration file.

web_reviewer.index_list() -> list
    All valid record indices.

web_reviewer.get_index() -> object
    The currently active record index.

web_reviewer.set_index(index)
    Switch to a different record.

web_reviewer.get_value(column) -> object
    Current data value for *column* in the active record.

web_reviewer.set_value(column, value)
    Update *column* for the active record and trigger on-change logic
    (timestamps, combinators).

web_reviewer.save_flows()
    Persist data to output files.

web_reviewer.load_flows(reload=False)
    Reload data from source files.

web_reviewer.get_widget_specs() -> list[dict]
    Flat, ordered list of widget spec dicts derived from ``interface["review"]``
    and ``interface["viewer"]``.

web_reviewer.affected_widgets(column) -> set[str]
    Column names whose displayed values may change after *column* is updated.
    The current implementation returns all field-bearing widget columns so the
    web layer simply re-renders the whole form; a dependency-tracking
    optimisation is deferred to a follow-on CIP.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from lynguine import log as _lynguine_log

log = logging.getLogger(__name__)

# Widget types that contain nested entries rather than being rendered directly.
_CLUSTER_TYPES = frozenset(
    {"group", "load", "composite", "loop", "precompute", "postcompute"}
)

# Widget types that don't carry a data field (no column to refresh).
_NON_FIELD_TYPES = frozenset(
    {"Label", "HTML", "HTMLMath", "Markdown",
     "SaveButton", "ReloadButton", "PopulateButton"}
)


class WebReviewer:
    """Stateful, widget-free review session for the web backend.

    :param user_file: Name of the YAML configuration file,
        defaults to ``"_referia.yml"``.
    :type user_file: str
    :param directory: Directory that contains the configuration file,
        defaults to ``"."``.  Callers that map a URL path to this directory
        (root-server mode) must validate it with
        ``referia.web.path_safety.safe_path_under_root`` first; this class
        does not re-check path traversal.
    :type directory: str

    Example::

        reviewer = WebReviewer("_referia.yml", "/path/to/review")
        reviewer.set_index(reviewer.index_list()[0])
        value = reviewer.get_value("score")
        reviewer.set_value("score", 5)
        reviewer.save_flows()
    """

    def __init__(
        self,
        user_file: str = "_referia.yml",
        directory: str = ".",
        *,
        allowed_roots: list | None = None,
    ) -> None:
        import os
        from pathlib import Path
        from referia.config.interface import Interface
        from referia.assess.data import CustomDataFrame

        self._directory = str(Path(directory).resolve())
        # WebReviewer is shared with the HTTP web app (routes.py). Keep the
        # CIP-000A path jail on by default. Trusted local Jupyter/CLI helpers
        # (referia.data.Data, referia.display.Scorer) may pass
        # unbounded_paths=True; this class must not.
        #
        # Default roots: review directory + its parent (sibling ``../info``,
        # ``../pdfpages`` layouts). Callers in root-server mode should also
        # pass the serve ``--root`` via *allowed_roots* so configs under that
        # tree (e.g. ``theses/criteria/``) remain readable.
        _config_dir = Path(self._directory)
        _roots: list[str] = [str(_config_dir), str(_config_dir.parent)]
        if allowed_roots:
            for root in allowed_roots:
                if root is None:
                    continue
                resolved = str(Path(root).expanduser().resolve())
                if resolved not in _roots:
                    _roots.append(resolved)
        self._interface = Interface.from_file(
            user_file, self._directory, allowed_roots=_roots
        )

        # Data loading resolves file paths relative to CWD, so temporarily
        # switch to the review directory for the duration of the load.
        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            self._data = CustomDataFrame.from_flow(self._interface)
        finally:
            os.chdir(_orig)

        indices = list(self._data.index)
        if indices:
            self._data.set_index(indices[0])

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def index_list(self) -> list:
        """Return all valid record indices as a plain list."""
        return list(self._data.index)

    def get_index(self) -> Any:
        """Return the currently active record index."""
        return self._data.get_index()

    def _resolve_index_label(self, index: Any) -> Any:
        """Map *index* onto a typed label present in ``index_list()``.

        HTTP/HTMX query parameters arrive as strings. Allocation indices may
        be integers (or other non-str types). Prefer exact membership in the
        data index; otherwise accept a unique match where
        ``str(label) == str(index)``. Does not treat integers as positional
        offsets (see backlog ``2026-10-06_web-index-query-string-type``).

        :param index: Label as provided by the caller (typed or string form).
        :return: The typed label to pass to lynguine ``set_index``.
        :raises KeyError: If no matching label exists (or the string match
            is ambiguous).
        """
        data_index = self._data.index
        try:
            if index in data_index:
                return index
        except TypeError:
            pass

        matches = [idx for idx in self.index_list() if str(idx) == str(index)]
        if len(matches) == 1:
            return matches[0]
        raise KeyError(f'Index "{index}" not found in data')

    def set_index(self, index: Any) -> None:
        """Switch the active record to *index*.

        Accepts typed index labels or their string forms (for example
        ``"2"`` when the allocation index uses integer ``2``).
        """
        self._data.set_index(self._resolve_index_label(index))

    # ------------------------------------------------------------------
    # Value access
    # ------------------------------------------------------------------

    def get_value(self, column: str) -> Any:
        """Return the current value of *column* for the active record.

        NaN values (pandas sentinel for missing data) are normalised to
        ``None`` so renderers and callers can use a simple ``is None`` check
        rather than having to handle every numpy/pandas NaN variant.  This
        mirrors what the Jupyter interface achieves via ``remove_nan()``
        before passing values to widgets.

        :param column: Name of the data column.
        :return: The stored value, with NaN replaced by ``None``.
        """
        import math
        import numpy as np
        import pandas as pd

        self._data.set_column(column)
        val = self._data.get_value()
        # Normalise all NaN-like sentinels to None.
        try:
            if val is None:
                return None
            if isinstance(val, float) and math.isnan(val):
                return None
            if isinstance(val, (np.floating,)) and np.isnan(val):
                return None
            if isinstance(val, np.datetime64) and np.isnat(val):
                return None
            if pd.api.types.is_scalar(val) and pd.isnull(val):
                return None
        except (TypeError, ValueError):
            pass
        return val

    def get_row_data(self) -> dict:
        """Return all column values for the current record as a plain dict.

        Unlike :meth:`get_value`, which requires knowing the column name in
        advance, this returns the entire row so that callers (e.g. the
        renderer) can look up any column—including those used in
        ``visible_if`` conditions that have no corresponding widget.

        Values are read with :meth:`get_value` rather than ``to_pandas()``.
        ``to_pandas()`` joins every flow into one frame and raises when
        allocation and scores share column names, which would blank Liquid
        substitutions (``{{q1Question}}`` and similar constants).
        ``get_value`` is the same path Jupyter Liquid uses, including
        parameter columns from ``global_consts``.

        Mapping aliases from ``_name_column_map`` and from the interface
        ``input`` / ``output`` mapping (for example ``Title`` → ``Project title``,
        or ``number`` → the index column) are copied into the dict as well.
        Jupyter Liquid uses :meth:`lynguine.assess.data.CustomDataFrame.mapping`;
        the web renderer looks up ``{{Title}}`` by key, so aliases must be
        present or those substitutions go empty.  Index fields are often
        absent from ``_name_column_map`` even when they appear in YAML.
        """
        try:
            columns = list(self._data.columns)
        except Exception:
            return {}

        result: dict = {}
        for col in columns:
            try:
                result[col] = self.get_value(col)
            except Exception:
                result[col] = None

        try:
            idx_name = getattr(self._data.index, "name", None)
            if idx_name and idx_name not in result:
                result[idx_name] = self.get_index()
        except Exception:
            idx_name = None

        for name, column in self._row_mapping_aliases().items():
            if name in result:
                continue
            if column in result:
                result[name] = result[column]
                continue
            try:
                result[name] = self.get_value(column)
            except Exception:
                if column == idx_name:
                    result[name] = self.get_index()
                else:
                    result[name] = None
        return result

    def _row_mapping_aliases(self) -> dict:
        """Name → column aliases for Liquid keys on the current row."""
        aliases: dict = {}
        name_map = getattr(self._data, "_name_column_map", None)
        if isinstance(name_map, dict):
            aliases.update(name_map)
        for key in ("input", "output", "allocation", "scores"):
            try:
                block = self._interface[key] if key in self._interface else None
            except Exception:
                block = None
            if isinstance(block, dict):
                mapping = block.get("mapping")
                if isinstance(mapping, dict):
                    aliases.update(mapping)
        return aliases

    def set_value(self, column: str, value: Any) -> None:
        """Update *column* for the active record and run on-change logic.

        If the new value is identical to the stored value the call is a no-op.

        :param column: Name of the data column.
        :param value: New value to store.
        """
        self._data.set_column(column)
        old_value = self._data.get_value()
        if value != old_value:
            self._data.set_value(value)
            self._value_updated(column)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_flows(self) -> None:
        """Persist current data to the configured output files.

        File paths in the interface may be relative; chdir to the review
        directory so they resolve to the same location used by ``from_flow``.
        """
        import os

        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            self._data.save_flows()
        finally:
            os.chdir(_orig)

    def load_flows(self, reload: bool = False) -> None:
        """Reload data from the configured source files.

        Re-creates ``self._data`` from the interface configuration, preserving
        the current index when *reload* is True.

        :param reload: If True, attempt to restore the active index after
            reloading.  Defaults to False.
        :type reload: bool
        """
        import os
        from referia.assess.data import CustomDataFrame

        current_index = self._data.get_index() if reload else None
        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            self._data = CustomDataFrame.from_flow(self._interface)
        finally:
            os.chdir(_orig)

        indices = list(self._data.index)
        if current_index is not None and current_index in indices:
            self._data.set_index(current_index)
        elif indices:
            self._data.set_index(indices[0])

    # ------------------------------------------------------------------
    # Widget spec extraction
    # ------------------------------------------------------------------

    def get_widget_specs(self) -> list[dict]:
        """Return a flat ordered list of widget spec dicts.

        Walks the ``review`` and ``viewer`` sections of the interface config
        and expands cluster entries recursively.  Each item in the returned
        list has at least a ``"type"`` key and, for field-bearing widgets, a
        ``"field"`` key.

        :return: Ordered list of widget spec dicts (viewer first, then review).
        """
        specs: list[dict] = []
        self._flatten_entries(self._viewer_raw(), specs)
        self._flatten_entries(self._review_raw(), specs)
        return specs

    def get_viewer_specs(self) -> list[dict]:
        """Return widget specs from the ``viewer`` section only.

        :return: Flat ordered list of viewer widget spec dicts.
        """
        specs: list[dict] = []
        self._flatten_entries(self._viewer_raw(), specs)
        return specs

    def get_review_specs(self) -> list[dict]:
        """Return widget specs from the ``review`` section only.

        :return: Flat ordered list of review widget spec dicts.
        """
        specs: list[dict] = []
        self._flatten_entries(self._review_raw(), specs)
        return specs

    def list_url_entries(self) -> list[dict]:
        """Resolve ``urls:`` entries for the current record.

        Jupyter opens these with ``webbrowser.open``.  The web panel renders
        them as ``<a target="_blank">`` links.

        :return: List of ``{"href": str, "label": str}`` dicts.
        """
        from unidecode import unidecode

        from referia.util.misc import renderable, tallyable

        entries: list[dict] = []
        for view in self._interface_section("urls"):
            if not isinstance(view, dict) or "url" not in view:
                continue
            try:
                urlterm = self._extract_url_term(view, renderable, tallyable)
                href = unidecode(str(view["url"]) + urlterm.replace(" ", "%20"))
            except Exception as exc:
                log.debug("Could not resolve url entry %r: %s", view, exc)
                continue
            if not href:
                continue
            entries.append({"href": href, "label": href})
        return entries

    def list_pdf_entries(self) -> list[dict]:
        """Describe ``localpdf`` / ``editpdf`` files for the current record.

        Paths are resolved on the server; the returned dicts are metadata for
        the document panel.  Serving goes through ``/record-document/{kind}/{n}``.

        :return: List of ``kind``, ``n``, ``label``, ``exists`` dicts.
        """
        entries: list[dict] = []
        for kind in ("localpdf", "editpdf"):
            for n, view in enumerate(self._interface_section(kind)):
                if not isinstance(view, dict):
                    continue
                path = self.get_record_document(kind, n)
                label = view.get("name") or (path.name if path is not None else kind)
                entries.append(
                    {
                        "kind": kind,
                        "n": n,
                        "label": str(label),
                        "exists": bool(path is not None and path.is_file()),
                    }
                )
        return entries

    def get_record_document(self, kind: str, n: int):
        """Return the resolved PDF path for ``localpdf``/``editpdf`` entry *n*.

        :return: A :class:`~pathlib.Path` or ``None`` if missing or unresolvable.
        """
        from pathlib import Path

        views = self._interface_section(kind)
        if n < 0 or n >= len(views):
            return None
        view = views[n]
        if not isinstance(view, dict):
            return None
        try:
            if kind == "localpdf":
                path = self._resolve_local_file(view)
            elif kind == "editpdf":
                path = self._resolve_editpdf_file(view)
            else:
                return None
        except Exception as exc:
            log.debug("Could not resolve %s[%s]: %s", kind, n, exc)
            return None
        return Path(path).expanduser() if path else None

    def allowed_roots_for_document(self, kind: str, n: int) -> list:
        """Directories that entry *n* of *kind* may legally serve from."""
        from pathlib import Path

        roots = [Path(self._directory).resolve()]
        views = self._interface_section(kind)
        if n < 0 or n >= len(views) or not isinstance(views[n], dict):
            return roots
        view = views[n]
        for key in ("directory", "sourcedirectory", "storedirectory"):
            raw = view.get(key)
            if not raw:
                continue
            try:
                roots.append(self._resolve_config_relative_dir(raw))
            except OSError:
                continue
        return roots

    def render_viewer_html(self, viewer_spec: dict) -> str:
        """Evaluate *viewer_spec* against the current record and return HTML.

        Uses ``CustomDataFrame.view_to_value()`` to resolve Liquid / display
        templates, then ``render_viewer()`` to produce the HTML string.

        :param viewer_spec: A viewer spec dict (``liquid``, ``display``, etc.).
        :return: Rendered HTML string (empty string on evaluation failure).
        """
        from referia.web.render import render_viewer as _render_viewer_html

        try:
            content = self._data.view_to_value(viewer_spec) or ""
        except Exception as exc:
            log.debug("Could not evaluate viewer spec %r: %s", viewer_spec, exc)
            content = ""
        return _render_viewer_html(viewer_spec, content)

    def _viewer_raw(self) -> list:
        viewer = self._interface.get("viewer", []) or []
        return viewer if isinstance(viewer, list) else [viewer]

    def _review_raw(self) -> list:
        review = self._interface.get("review", []) or []
        return review if isinstance(review, list) else [review]

    def _interface_section(self, key: str) -> list:
        try:
            section = self._interface[key] if key in self._interface else []
        except Exception:
            section = []
        if not section:
            return []
        return section if isinstance(section, list) else [section]

    def _extract_file_value(self, view: dict):
        from referia.util.misc import renderable, tallyable

        if renderable(view):
            return self._data.view_to_value(view)
        if tallyable(view):
            return self._data.tally_to_value(view)
        if "field" in view:
            return self.get_value(view["field"])
        if "file" in view:
            return view["file"]
        return None

    def _extract_url_term(self, view: dict, renderable, tallyable) -> str:
        if "field" in view:
            val = self.get_value(view["field"])
            if isinstance(val, str):
                return val
        if renderable(view):
            return str(self._data.view_to_value(view) or "")
        if tallyable(view):
            return str(self._data.tally_to_value(view) or "")
        return ""

    def _resolve_config_relative_dir(self, raw: str | None):
        """Resolve a YAML directory against the config directory, not process cwd.

        Relative values such as ``../files`` are joined to ``self._directory``.
        Absolute paths and ``$HOME`` / env-expanded paths are left as absolute.
        An empty value means the config directory itself.
        """
        import os
        from pathlib import Path

        base = Path(self._directory)
        text = os.path.expandvars(str(raw or "")).strip()
        if not text:
            return base.resolve()
        directory = Path(text).expanduser()
        if not directory.is_absolute():
            directory = base / directory
        return directory.resolve()

    def _resolve_local_file(self, view: dict):
        from pathlib import Path

        val = self._extract_file_value(view)
        if not isinstance(val, str) or not val:
            return None
        return self._resolve_config_relative_dir(view.get("directory")) / Path(val)

    def _resolve_editpdf_file(self, view: dict):
        """Prefer the annotated copy when it exists, otherwise the source PDF."""
        from pathlib import Path

        from referia.util.files import to_valid_file
        from referia.util.misc import renderable

        val = self._extract_file_value(view)
        if not isinstance(val, str) or not val:
            return None
        source_dir = self._resolve_config_relative_dir(view.get("sourcedirectory"))
        store_raw = view.get("storedirectory")
        store_dir = (
            self._resolve_config_relative_dir(store_raw) if store_raw else None
        )
        orig = source_dir / Path(val)
        if "name" in view:
            stub = str(view["name"]) + ".pdf"
        elif renderable(view):
            stub = self._data.view_to_tmpname(view) + ".pdf"
        else:
            stub = orig.name
        index = self.get_index()
        dest_name = to_valid_file(str(index)) + "_" + to_valid_file(stub)
        dest = (store_dir / dest_name) if store_dir is not None else None
        if dest is not None and dest.is_file():
            return dest
        return orig

    def _flatten_entries(self, entries: list, out: list) -> None:
        """Recursively flatten nested review/viewer cluster entries.

        :param entries: List of widget or cluster dicts.
        :param out: Accumulator list that receives leaf widget dicts.
        """
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            entry_type = entry.get("type", "")
            if entry_type in _CLUSTER_TYPES:
                sub = entry.get("entries", entry.get("specifications", []))
                if isinstance(sub, list):
                    self._flatten_entries(sub, out)
            else:
                out.append(entry)

    # ------------------------------------------------------------------
    # Widget dependency tracking
    # ------------------------------------------------------------------

    def affected_widgets(self, column: str) -> set[str]:
        """Return column names that may need refreshing after *column* changes.

        The current implementation conservatively returns **all** field-bearing
        widget columns so the web layer re-renders the complete form.  A
        finer-grained dependency graph is deferred to a follow-on CIP.

        :param column: The column that was just updated.
        :return: Set of column names to refresh.
        """
        return {
            spec["field"]
            for spec in self.get_widget_specs()
            if "field" in spec
        }

    # ------------------------------------------------------------------
    # Internal on-change logic (mirrors Reviewer.value_updated without widgets)
    # ------------------------------------------------------------------

    def run_populate(self, compute_interface: dict) -> None:
        """Run an on-demand compute as triggered by a PopulateButton.

        Mirrors the Jupyter PopulateButton.on_click behaviour::

            self._parent._data._compute.run(
                self._parent._data, {"compute": args["compute"]}
            )

        File paths in compute functions may be relative; chdir to the review
        directory so they resolve correctly.

        :param compute_interface: Dict of the form ``{"compute": <spec>}`` as
            constructed from the PopulateButton's ``args.compute`` entry.
        """
        import os

        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            self._data._compute.run(self._data, compute_interface)
        finally:
            os.chdir(_orig)

    # ------------------------------------------------------------------
    # Document generation (CIP-000B remaining work)
    # ------------------------------------------------------------------

    @property
    def _system(self):
        """Lazily construct a :class:`~referia.system.Sys` for document I/O."""
        if not hasattr(self, "_system_instance") or self._system_instance is None:
            from referia.system import Sys

            self._system_instance = Sys(self._interface)
        return self._system_instance

    def list_document_entries(self, section: str = "documents") -> list[dict]:
        """Describe ``documents:`` / ``summary_documents:`` action buttons.

        :param section: Interface key, ``\"documents\"`` or
            ``\"summary_documents\"``.
        :return: List of ``n``, ``type``, ``label``, ``summary``, ``section``.
        """
        summary = section == "summary_documents"
        entries: list[dict] = []
        for n, doc in enumerate(self._interface_section(section)):
            if not isinstance(doc, dict) or "type" not in doc:
                continue
            dtype = str(doc["type"])
            default = f"Create Summary {dtype}" if summary else f"Create {dtype}"
            label = doc.get("name") or default
            entries.append(
                {
                    "n": n,
                    "type": dtype,
                    "label": str(label),
                    "summary": summary,
                    "section": section,
                }
            )
        return entries

    def template_to_value(self, template: dict) -> str:
        """Render a document template field against the current record.

        Mirrors :meth:`referia.assess.review.Reviewer.template_to_value` without
        widgets.  ``use: review`` / ``use: scorer`` synthesise markdown from
        current review field values instead of ``WidgetCluster.to_markdown()``.
        """
        if not isinstance(template, dict):
            return str(template or "")
        if "use" in template:
            use = template["use"]
            if use == "viewer":
                viewer = self._interface.get("viewer", []) or []
                if not isinstance(viewer, list):
                    viewer = [viewer]
                parts = []
                for view in viewer:
                    try:
                        parts.append(str(self._data.view_to_value(view) or ""))
                    except Exception as exc:
                        log.debug("viewer template failed: %s", exc)
                return "\n\n".join(parts)
            if use in {"scorer", "review"}:
                return self._review_fields_markdown()
        return str(self._data.view_to_value(template) or "")

    def _review_fields_markdown(self) -> str:
        """Best-effort markdown of review fields when widgets are unavailable."""
        lines: list[str] = []
        for spec in self.get_review_specs():
            field = spec.get("field")
            if not field:
                continue
            label = (
                spec.get("args", {}).get("description")
                or spec.get("description")
                or field
            )
            val = self.get_value(field)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                val = ""
            lines.append(f"### {label}\n\n{val}\n")
        return "\n".join(lines)

    def generate_document(self, n: int, *, summary: bool = False) -> dict:
        """Generate ``documents[n]`` (or ``summary_documents[n]``) and return status.

        :return: Dict with ``type``, ``path`` (filesystem path or ``None``),
            ``href`` (``/document/...`` download when under the review dir),
            and ``status`` (``created`` / ``drafted``).
        """
        section = "summary_documents" if summary else "documents"
        docs = self._interface_section(section)
        if n < 0 or n >= len(docs) or not isinstance(docs[n], dict):
            raise IndexError(f"No document at {section}[{n}]")
        return self.create_document(docs[n], summary=summary)

    def create_document(self, document: dict, summary: bool = False) -> dict:
        """Generate one document spec without opening it in a desktop app.

        Ports :meth:`referia.assess.review.Reviewer.create_document` for the web
        backend: writes files via ``lynguine.access.io`` and returns a download
        path instead of calling :meth:`~referia.system.Sys.open_localfile`.
        """
        import os
        from pathlib import Path

        from lynguine import access

        if not isinstance(document, dict) or "type" not in document:
            raise ValueError("document must be a dict with a type key")

        args = self._document_template_args(document, summary=summary)
        doctype = document["type"]
        result: dict[str, Any] = {
            "type": doctype,
            "path": None,
            "href": None,
            "status": "created",
        }

        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            if doctype == "email":
                self._system.create_email(document, **args)
                result["status"] = "drafted"
                return result

            data, filename, content = self._system.create_document_content(
                document, **args
            )
            writers = {
                "docx": access.io.write_docx_file,
                "markdown": access.io.write_markdown_file,
                "letter": access.io.write_letter_file,
                "formlink": access.io.write_formlink,
            }
            writer = writers.get(doctype)
            if writer is None:
                # Unknown / excel etc.: use Sys but suppress desktop open.
                _open = self._system.open_localfile
                self._system.open_localfile = lambda *_a, **_k: None  # type: ignore[method-assign]
                try:
                    self._system.create_document(document, **args)
                finally:
                    self._system.open_localfile = _open  # type: ignore[method-assign]
                filename = args.get("filename") or filename
            else:
                writer(data=data, filename=filename, content=content)

            if filename:
                path = Path(filename).expanduser()
                if not path.is_absolute():
                    path = Path(self._directory) / path
                result["path"] = str(path.resolve())
                result["href"] = self.document_download_href(path)
            return result
        finally:
            os.chdir(_orig)

    def _document_template_args(self, document: dict, *, summary: bool) -> dict:
        """Resolve Liquid / view template fields on a document spec."""
        args: dict[str, Any] = {}
        template_keys = ("tally", "display", "list", "join", "liquid", "use")
        for field, value in document.items():
            if field == "type":
                continue
            args[field] = value
            if value is None or not isinstance(value, dict):
                continue
            if not any(k in value for k in template_keys):
                continue
            if summary and field in {"content", "body"}:
                current = self.get_index()
                parts: list[str] = []
                for idx in self.index_list():
                    self.set_index(idx)
                    parts.append(self.template_to_value(value))
                    parts.append("\n\n")
                args[field] = "".join(parts)
                if current is not None:
                    self.set_index(current)
            else:
                args[field] = self.template_to_value(value)

        if "body" in args:
            if "content" in args:
                log.warning("Contents field being overwritten by body in create_document")
            args["content"] = args["body"]
        if "header" in args:
            args["content"] = args["header"] + "\n\n" + args.get("content", "")
            del args["header"]
        if "footer" in args:
            args["content"] = args.get("content", "") + "\n\n" + args["footer"]
            del args["footer"]
        return args

    def document_download_href(self, path) -> str | None:
        """Return a ``/document/...`` href if *path* is under the review directory."""
        from pathlib import Path

        try:
            resolved = Path(path).expanduser().resolve()
            rel = resolved.relative_to(Path(self._directory).resolve())
        except (OSError, ValueError, TypeError):
            return None
        return f"/document/{rel.as_posix()}"

    def ensure_edit_pdf(self, n: int):
        """Copy/extract ``editpdf[n]`` into ``storedirectory`` and return its Path.

        Mirrors the non-open part of :meth:`referia.system.Sys.edit_files` so
        the web UI can offer a download instead of launching Preview.
        """
        import os
        from pathlib import Path

        from referia.util.files import to_valid_file
        from referia.util.misc import renderable

        views = self._interface_section("editpdf")
        if n < 0 or n >= len(views) or not isinstance(views[n], dict):
            raise IndexError(f"No editpdf entry at index {n}")
        view = views[n]
        val = self._extract_file_value(view)
        if not isinstance(val, str) or not val:
            raise FileNotFoundError(f"No file value for editpdf[{n}]")
        if "storedirectory" not in view or "sourcedirectory" not in view:
            raise ValueError("editpdf entry requires sourcedirectory and storedirectory")

        source_dir = self._resolve_config_relative_dir(view.get("sourcedirectory"))
        store_dir = self._resolve_config_relative_dir(view.get("storedirectory"))
        orig = source_dir / Path(val)
        if "name" in view:
            stub = str(view["name"]) + ".pdf"
        elif renderable(view):
            stub = self._data.view_to_tmpname(view) + ".pdf"
        else:
            stub = orig.name
        index = self.get_index()
        dest_name = to_valid_file(str(index)) + "_" + to_valid_file(stub)
        dest = store_dir / dest_name

        _orig = os.getcwd()
        try:
            os.chdir(self._directory)
            store_dir.mkdir(parents=True, exist_ok=True)
            if not dest.is_file():
                self._system.copy_file(str(orig), str(dest), view, self._data)
        finally:
            os.chdir(_orig)

        if not dest.is_file():
            raise FileNotFoundError(f"Could not create edit PDF at {dest}")
        return dest.resolve()

    def _value_updated(self, column: str) -> None:
        """Run on-change side-effects for *column* without touching widgets.

        Replicates the non-widget parts of ``Reviewer.value_updated()``:

        1. Updates the ``<column>_modified`` timestamp.
        2. Sets the ``<column>_created`` timestamp when absent.
        3. Re-evaluates any combinator fields defined in the interface.
        """
        today_val = pd.to_datetime("today")

        # Modified timestamp
        modified_suffix: str = self._interface["modified_suffix"]
        modified_field = f"{column}_{modified_suffix}"
        try:
            self._data.set_dtype(modified_field, "datetime64[ns]")
            self._data.set_column(modified_field)
            self._data.set_value(today_val)
        except Exception as exc:
            log.debug("Could not set modified field %r: %s", modified_field, exc)

        # Created timestamp (only when absent)
        created_suffix: str = self._interface["created_suffix"]
        created_field = f"{column}_{created_suffix}"
        try:
            self._data.set_dtype(created_field, "datetime64[ns]")
            created_col_val = self._data.get_value_column(created_field)
            current_created = self._data.at[self._data.get_index(), created_col_val] if created_col_val in self._data.columns else None
            if current_created is None or pd.isna(current_created):
                self._data.set_column(created_field)
                self._data.set_value(today_val)
        except Exception as exc:
            log.debug("Could not set created field %r: %s", created_field, exc)

        # Combinators
        if "combinator" in self._interface:
            for view in self._interface["combinator"]:
                if "field" not in view:
                    continue
                col = view["field"]
                combinator_view = {k: v for k, v in view.items() if k != "field"}
                try:
                    combinator_val = self._data.viewer_to_value(combinator_view)
                    self._data.set_column(col)
                    self._data.set_value(combinator_val)
                except Exception as exc:
                    log.debug("Could not update combinator %r: %s", col, exc)
