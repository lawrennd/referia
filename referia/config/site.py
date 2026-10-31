"""Jekyll-style ``_config.yml`` at the serve / repo root.

Giki pages take ``ghub`` from ``_config.yml`` and build an edit-on-GitHub
URL for the source file. Referia does the same for ``_referia.md``:
walk up from the review directory, flatten ``ghub`` into site constants,
and compute ``github_edit_url`` for the current config file.

Analysis knobs stay in each stage's ``parameters.yml`` /
``info/constants.yml``. This file is site chrome only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

SITE_CONFIG_NAME = "_config.yml"
_MAX_WALK = 8


def find_site_config(start, stop=None, *, max_up: int = _MAX_WALK) -> Path | None:
    """Return the nearest ancestor ``_config.yml``, not walking past *stop*."""
    cur = Path(start).expanduser().resolve()
    if cur.is_file():
        cur = cur.parent
    stop_res = Path(stop).expanduser().resolve() if stop else None
    for _ in range(max(1, int(max_up))):
        candidate = cur / SITE_CONFIG_NAME
        if candidate.is_file():
            return candidate
        if stop_res is not None and cur == stop_res:
            break
        if (cur / ".git").exists():
            break
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _ghub_entry(data: Mapping[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    raw = data.get("ghub")
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    if not isinstance(raw, Mapping):
        return {}
    return dict(raw)


def _split_repository(value: Any) -> tuple[str, str]:
    text = str(value or "").strip().strip("/")
    if "/" in text:
        org, repo = text.split("/", 1)
        return org.strip(), repo.strip()
    return "", text


def referia_url_mode(data: Mapping[str, Any] | None) -> str:
    """Read ``referia.urls`` from a site ``_config.yml`` mapping. Default path."""
    raw = (data or {}).get("referia")
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    if not isinstance(raw, Mapping):
        return "path"
    mode = str(raw.get("urls") or "path").strip().lower()
    if mode not in {"path", "permalink"}:
        return "path"
    return mode


def flatten_site_config(data: Mapping[str, Any] | None) -> dict[str, Any]:
    """Map Jekyll ``_config.yml`` keys onto Liquid-friendly constants."""
    data = dict(data or {})
    ghub = _ghub_entry(data)
    org = str(ghub.get("organization") or "").strip()
    repo = str(ghub.get("repository") or "").strip()
    if "/" in repo and not org:
        org, repo = _split_repository(repo)
    if not org:
        org = str(data.get("github_username") or "").strip()
    branch = str(ghub.get("branch") or "main").strip() or "main"
    directory = str(ghub.get("directory") or "").strip().strip("/")
    edit = ghub.get("edit", True)
    out: dict[str, Any] = {
        "ghub_edit": bool(edit),
        "ghub_organization": org,
        "ghub_repository": repo,
        "ghub_branch": branch,
        "ghub_directory": directory,
    }
    title = data.get("title")
    if title:
        out["site_title"] = str(title)
    out["referia_urls"] = referia_url_mode(data)
    return out


def github_edit_url(site: Mapping[str, Any] | None, relpath: str) -> str | None:
    """``https://github.com/{org}/{repo}/edit/{branch}/{path}`` or ``None``."""
    site = dict(site or {})
    if not site.get("ghub_edit"):
        return None
    org = str(site.get("ghub_organization") or "").strip()
    repo = str(site.get("ghub_repository") or "").strip()
    branch = str(site.get("ghub_branch") or "").strip()
    if not org or not repo or not branch:
        return None
    path = str(relpath or "").replace("\\", "/").lstrip("/")
    if not path:
        return None
    directory = str(site.get("ghub_directory") or "").strip().strip("/")
    if directory:
        path = f"{directory}/{path}"
    return f"https://github.com/{org}/{repo}/edit/{branch}/{path}"


def _read_mapping(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError:
        return {}
    return dict(loaded) if isinstance(loaded, Mapping) else {}


def load_site_constants(
    start,
    config_path=None,
    stop=None,
) -> dict[str, Any]:
    """Flatten site ``_config.yml`` and attach ``github_edit_url``.

    *start* is the review directory (or any path under the study).
    *config_path* is this review's markdown / ``_referia.yml``.
    *stop* is the serve root when known, so a parent directory's
    ``_config.yml`` is not picked up by accident.
    """
    found = find_site_config(start, stop=stop)
    if found is None:
        return {}
    site = flatten_site_config(_read_mapping(found))
    root = found.parent
    relpath = ""
    if config_path is not None:
        try:
            relpath = str(Path(config_path).resolve().relative_to(root)).replace(
                "\\", "/"
            )
        except ValueError:
            relpath = Path(config_path).name
    url = github_edit_url(site, relpath)
    if url:
        site["github_edit_url"] = url
    return site
