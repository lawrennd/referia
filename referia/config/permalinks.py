"""Permalink-tree identity for Jekyll study pages (CIP-0022).

Path mode (CIP-000C) maps a URL onto a directory that holds ``_referia.yml``.
Permalink mode maps a URL onto the markdown file whose frontmatter declares
that permalink. Page files are ordinary Jekyll names at the serve root
(``index.md``, ``01_turns.md``); they are not called ``referia.md``.
``layout: referia`` is the type marker.
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from referia.config.files import read_config_mapping
from referia.config.site import _read_mapping, find_site_config, referia_url_mode

log = logging.getLogger(__name__)

REFERIA_LAYOUT = "referia"
URL_MODE_PATH = "path"
URL_MODE_PERMALINK = "permalink"
URL_MODES = (URL_MODE_PATH, URL_MODE_PERMALINK)

_SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    ".venv-vibesafe",
    "__pycache__",
    "node_modules",
    "_layouts",
    "_includes",
    "_site",
    "_sass",
}

_MD_SUFFIXES = {".md", ".markdown", ".mmd"}


class PermalinkCollisionError(ValueError):
    """Two markdown pages declared the same permalink."""

    def __init__(self, permalink: str, first: Path, second: Path):
        self.permalink = permalink
        self.first = first
        self.second = second
        super().__init__(
            f"Duplicate permalink {permalink!r}: {first} and {second}"
        )


@dataclass(frozen=True)
class PermalinkEntry:
    permalink: str
    path: Path
    directory: Path


def normalize_permalink(value: Any) -> str:
    """Return a URL path with a leading and trailing slash (``/`` for root)."""
    text = str(value or "").strip().replace("\\", "/")
    if not text or text == "/":
        return "/"
    text = "/" + text.strip("/") + "/"
    return text


def site_exclude_patterns(data: Mapping[str, Any] | None) -> tuple[str, ...]:
    raw = (data or {}).get("exclude") or []
    if isinstance(raw, str):
        raw = [raw]
    out: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text:
            out.append(text)
    return tuple(out)


def is_permalink_config(mapping: Mapping[str, Any] | None) -> bool:
    """True when frontmatter is a Jekyll referia page with a permalink."""
    if not mapping:
        return False
    layout = str(mapping.get("layout") or "").strip()
    if layout != REFERIA_LAYOUT:
        return False
    if mapping.get("referia_config_version") is None:
        return False
    permalink = mapping.get("permalink")
    return permalink is not None and str(permalink).strip() != ""


def resolve_url_mode(root, override: str | None = None) -> str:
    """CLI override wins; else ``_config.yml``; else path."""
    if override:
        mode = str(override).strip().lower()
        if mode in URL_MODES:
            return mode
        log.warning("Unknown --urls %r; using path", override)
        return URL_MODE_PATH
    found = find_site_config(root, stop=root)
    if found is None:
        return URL_MODE_PATH
    return referia_url_mode(_read_mapping(found))


def _path_excluded(rel: str, patterns: Iterable[str]) -> bool:
    rel = rel.replace("\\", "/").lstrip("/")
    name = Path(rel).name
    for pat in patterns:
        pat = str(pat).strip().replace("\\", "/")
        if not pat:
            continue
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(name, pat):
            return True
        prefix = pat.rstrip("/")
        if prefix and (rel == prefix or rel.startswith(prefix + "/")):
            return True
    return False


def iter_markdown_under(root: Path, exclude: Iterable[str] = ()) -> Iterable[Path]:
    """Yield markdown files under *root*, skipping VCS/venv and ``exclude``."""
    root = Path(root).resolve()
    patterns = tuple(exclude)
    for dirpath, dirnames, filenames in root.walk() if hasattr(root, "walk") else _walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES and not d.startswith(".")]
        rel_dir = str(dirpath.relative_to(root)).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
        if rel_dir and _path_excluded(rel_dir, patterns):
            dirnames[:] = []
            continue
        for name in filenames:
            path = dirpath / name
            if path.suffix.lower() not in _MD_SUFFIXES:
                continue
            rel = str(path.relative_to(root)).replace("\\", "/")
            if _path_excluded(rel, patterns):
                continue
            yield path


def _walk(root: Path):
    """os.walk stand-in that yields ``(Path, dirnames, filenames)``."""
    import os

    for dirpath, dirnames, filenames in os.walk(root):
        yield Path(dirpath), dirnames, filenames


def build_permalink_tree(
    root,
    exclude: Iterable[str] | None = None,
) -> dict[str, PermalinkEntry]:
    """Map normalised permalink → entry. Raises on duplicates."""
    root_p = Path(root).expanduser().resolve()
    site_data: dict[str, Any] = {}
    found = find_site_config(root_p, stop=root_p)
    if found is not None:
        site_data = _read_mapping(found)
    patterns = tuple(exclude) if exclude is not None else site_exclude_patterns(site_data)
    tree: dict[str, PermalinkEntry] = {}
    for path in iter_markdown_under(root_p, patterns):
        try:
            mapping = read_config_mapping(path)
        except Exception as exc:
            log.warning("Skipping unreadable markdown %s: %s", path, exc)
            continue
        if not is_permalink_config(mapping):
            continue
        key = normalize_permalink(mapping.get("permalink"))
        entry = PermalinkEntry(permalink=key, path=path, directory=path.parent)
        prior = tree.get(key)
        if prior is not None:
            raise PermalinkCollisionError(key, prior.path, path)
        tree[key] = entry
    return tree


def lookup_permalink(
    tree: Mapping[str, PermalinkEntry], url_path: str
) -> PermalinkEntry | None:
    return tree.get(normalize_permalink(url_path or "/"))
