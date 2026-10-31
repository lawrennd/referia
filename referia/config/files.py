"""Filenames referia recognises as a review config.

A directory may hold ``_referia.md`` (YAML frontmatter plus a markdown
body) or ``_referia.yml``. When both exist, the markdown file wins.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REFERIA_CONFIG_FILENAMES = ("_referia.md", "_referia.yml")
DEFAULT_REFERIA_CONFIG = "_referia.yml"

_EXPLICIT_SUFFIXES = (".yml", ".yaml", ".md")


def is_explicit_config_path(url_path: str) -> bool:
    """True when *url_path* names a config file rather than a directory."""
    name = str(url_path or "").rstrip("/").rsplit("/", 1)[-1].lower()
    return name.endswith(_EXPLICIT_SUFFIXES)


def config_in_directory(directory) -> Path | None:
    """Return the config file in *directory*, preferring ``_referia.md``."""
    d = Path(directory)
    for name in REFERIA_CONFIG_FILENAMES:
        path = d / name
        if path.is_file():
            return path
    return None


def config_filename(directory) -> str:
    """Return the config filename in *directory*, or the yml default."""
    found = config_in_directory(directory)
    return found.name if found is not None else DEFAULT_REFERIA_CONFIG


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Return ``(yaml_block, markdown_body)`` for a frontmatter file."""
    if text.startswith("---\r\n"):
        rest = text[5:]
    elif text.startswith("---\n"):
        rest = text[4:]
    else:
        return text, ""
    idx = rest.find("\n---")
    if idx < 0:
        return rest, ""
    yaml_block = rest[:idx]
    body = rest[idx + 4 :]
    if body.startswith("\r\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]
    return yaml_block, body


def read_config_mapping(path) -> dict:
    """Load a referia config mapping from yml or markdown frontmatter.

    The markdown body is not parsed as YAML: it can contain ``:`` and
    lists that would break ``yaml.safe_load_all``.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    if path.suffix.lower() in {".md", ".markdown", ".mmd"}:
        yaml_block, _body = _split_frontmatter(text)
        data = yaml.safe_load(yaml_block) if yaml_block.strip() else {}
    else:
        data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def iter_configs(search_base: Path):
    """Yield config files under *search_base*; markdown wins in a directory."""
    seen: set[Path] = set()
    found: list[Path] = []
    for name in REFERIA_CONFIG_FILENAMES:
        found.extend(search_base.rglob(name))

    def sort_key(path: Path):
        prefer = 0 if path.name == "_referia.md" else 1
        return (str(path.parent), prefer)

    for path in sorted(found, key=sort_key):
        parent = path.parent.resolve()
        if parent in seen:
            continue
        seen.add(parent)
        yield path
