"""FastAPI application factory for the referia web display system."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

_WEB_DIR = Path(__file__).parent
_TEMPLATES_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"


def create_app(user_file: str = "_referia.yml", directory: str = ".") -> FastAPI:
    """Create and configure a FastAPI application for the given review directory.

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

    app.state.user_file = user_file
    app.state.directory = str(Path(directory).resolve())
    app.state.templates = templates

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(
            request,
            "base.html",
            {
                "title": "Referia Review Interface",
                "config": user_file,
                "directory": app.state.directory,
            },
        )

    @app.get("/health")
    async def health():
        return {"status": "ok", "config": user_file, "directory": app.state.directory}

    return app
