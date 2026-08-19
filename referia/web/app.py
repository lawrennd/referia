"""FastAPI application factory for the referia web display system."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

log = logging.getLogger(__name__)

_WEB_DIR = Path(__file__).parent
_TEMPLATES_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"


def create_app(
    user_file: str = "_referia.yml",
    directory: str = ".",
    root: str | None = None,
) -> FastAPI:
    """Create and configure a FastAPI application for the given review directory.

    Two modes are supported:

    **Single-config mode** (default)
        ``create_app(user_file="_referia.yml", directory="/path/to/review")``

        Loads exactly one ``_referia.yml`` at startup.  All existing behaviour
        is unchanged.

    **Root-server mode**
        ``create_app(root="/path/to/referia/root")``

        Serves any ``_referia.yml`` found under *root*, each addressable by its
        directory path in the URL (e.g. ``/theses/examined/introduction/``).
        Config loading is deferred to the first request for each path and cached
        thereafter.  ``user_file`` and ``directory`` are ignored when *root* is
        provided.

    Args:
        user_file: Config filename for single-config mode (default: ``_referia.yml``).
        directory: Review directory for single-config mode (default: ``"."``).
        root: Root directory for multi-config mode.  When supplied, ``user_file``
            and ``directory`` are ignored.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Referia Review Interface",
        description="Web-based review interface powered by referia.",
    )

    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    app.state.templates = templates
    app.state.start_time = int(time.time())  # cache-buster for static assets

    # reviewer_cache stores (mtime, WebReviewer) pairs keyed by resolved config path.
    # Used in root-server mode; populated lazily on first request for each path.
    app.state.reviewer_cache: dict[str, tuple[float, Any]] = {}

    if root is not None:
        # ── Root-server mode ──────────────────────────────────────────────────
        resolved_root = str(Path(root).resolve())
        app.state.root = resolved_root
        app.state.reviewer = None   # no single pre-loaded reviewer
        app.state.user_file = None
        app.state.directory = resolved_root
        # load_errors accumulates {path, type, time} dicts for the /errors page.
        # Exception text stays in the server log (CIP-000E).
        app.state.load_errors: list[dict] = []

        # Write WARNING+ messages from all referia/lynguine loggers to a
        # single file at the root so errors are easy to find.
        _log_path = Path(resolved_root) / "referia-server.log"
        _file_handler = logging.FileHandler(str(_log_path), encoding="utf-8")
        _file_handler.setLevel(logging.WARNING)
        _file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
        )
        for _logger_name in ("referia", "lynguine", ""):
            logging.getLogger(_logger_name).addHandler(_file_handler)

        @app.on_event("startup")
        async def _startup_root() -> None:
            log.info(
                "Referia root-server mode active.  "
                "Configs loaded on demand from: %r  "
                "Log: %s",
                resolved_root,
                _log_path,
            )

    else:
        # ── Single-config mode (original behaviour) ───────────────────────────
        resolved_dir = str(Path(directory).resolve())
        app.state.root = None
        app.state.user_file = user_file
        app.state.directory = resolved_dir
        app.state.reviewer = None   # populated by _startup below

        @app.on_event("startup")
        async def _startup() -> None:
            """Instantiate WebReviewer once at startup so all routes share state."""
            try:
                from referia.assess.web_review import WebReviewer
                app.state.reviewer = WebReviewer(user_file, resolved_dir)
                log.info(
                    "WebReviewer initialised: %d records loaded from %r/%r",
                    len(app.state.reviewer.index_list()),
                    resolved_dir,
                    user_file,
                )
            except Exception as exc:
                log.warning(
                    "Could not initialise WebReviewer (%s: %s); "
                    "review routes will return 503 until fixed.",
                    type(exc).__name__,
                    exc,
                )
                app.state.reviewer = None

    # Register HTMX routes.
    # /health is registered first, then the single-config router, then the
    # root_router (if in root-server mode).  Order matters because Starlette
    # uses first-match routing and root_router's catch-all
    # ``GET /{config_path:path}`` would otherwise swallow /health.
    @app.get("/health")
    async def health():
        if app.state.root is not None:
            return {
                "status": "ok",
                "mode": "root-server",
                "root": app.state.root,
                "configs_cached": len(app.state.reviewer_cache),
            }
        reviewer_ok = app.state.reviewer is not None
        return {
            "status": "ok" if reviewer_ok else "degraded",
            "mode": "single-config",
            "reviewer": "loaded" if reviewer_ok else "failed",
            "config": app.state.user_file,
            "directory": app.state.directory,
        }

    from referia.web.routes import router
    app.include_router(router)

    if root is not None:
        from referia.web.routes import root_router
        app.include_router(root_router)

    return app
