"""Filesystem path helpers that keep URL segments inside a configured root.

The web layer treats every URL path as untrusted input (CIP-000E). Authentication,
if added later, identifies who may use the server; it does not make ``../``
safe. Callers in ``referia.web.routes`` must use these helpers before any
``Path`` operation or ``os.chdir`` that depends on a request path.

``WebReviewer`` receives only directories that the routes layer has already
validated.
"""

from __future__ import annotations

from pathlib import Path


class PathOutsideRootError(ValueError):
    """Raised when a URL path would resolve outside the configured root."""


def safe_path_under_root(root: Path | str, url_path: str = "") -> Path:
    """Resolve *url_path* under *root*, rejecting traversal.

    Empty *url_path* (after stripping slashes) returns the resolved root.
    Leading slashes are stripped so HTTP paths such as ``/etc/passwd`` are
    treated as *root*/``etc/passwd``, not the OS absolute path.

    Raises:
        PathOutsideRootError: if any segment is ``..``, a segment is an absolute
            path, or the resolved path is not inside *root* (including via
            symlinks).
    """
    root_p = Path(root).resolve()
    clean = (url_path or "").strip("/")
    if not clean:
        return root_p

    parts: list[str] = []
    for part in Path(clean).parts:
        if part in (".", ""):
            continue
        if part == ".." or Path(part).is_absolute():
            raise PathOutsideRootError("Path outside root rejected")
        parts.append(part)

    candidate = root_p.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root_p)
    except ValueError as exc:
        raise PathOutsideRootError("Path outside root rejected") from exc
    return candidate
