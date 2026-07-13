"""FastAPI application factory for the referia web display system."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

log = logging.getLogger(__name__)

_WEB_DIR = Path(__file__).parent
_TEMPLATES_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"


def create_app(user_file: str = "_referia.yml", directory: str = ".") -> FastAPI:
    """Create and configure a FastAPI application for the given review directory.

    On startup the application instantiates a ``WebReviewer`` and stores it in
    ``app.state.reviewer``.  All HTMX routes are registered via
    ``referia.web.routes.router``.

    Args:
        user_file: Name of the referia configuration file (default: ``_referia.yml``).
        directory: Path to the review directory containing ``user_file`` and data
            files (default: current working directory).

    Returns:
        Configured FastAPI application instance ready to be served by uvicorn.
    """
    app = FastAPI(
        title="Referia Review Interface",
        description="Web-based review interface powered by referia.",
    )

    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    resolved_dir = str(Path(directory).resolve())
    app.state.user_file = user_file
    app.state.directory = resolved_dir
    app.state.templates = templates
    app.state.reviewer = None  # populated by _startup; guards against pre-startup requests

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

    # Register HTMX routes (all routes except health are in routes.py)
    from referia.web.routes import router
    app.include_router(router)

    @app.get("/health")
    async def health():
        reviewer_ok = app.state.reviewer is not None
        return {
            "status": "ok" if reviewer_ok else "degraded",
            "reviewer": "loaded" if reviewer_ok else "failed",
            "config": user_file,
            "directory": resolved_dir,
        }

    return app
