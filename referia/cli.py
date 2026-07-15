"""Command-line entry point for referia.

Usage::

    # Single-config mode (original):
    poetry run referia serve [--config _referia.yml] [--directory .] \\
                             [--host 127.0.0.1] [--port 8000]

    # Root-server mode (multi-config):
    poetry run referia serve --root ~/OneDrive/referia/ [--host 127.0.0.1] [--port 8000]
"""

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="referia",
        description="Referia review tools",
    )
    subparsers = parser.add_subparsers(dest="command")

    serve = subparsers.add_parser(
        "serve",
        help="Start the web review interface",
        description=(
            "Serve a referia review session as a local web application.  "
            "Open the printed URL in any browser.\n\n"
            "Single-config mode: serve one _referia.yml from a specific directory.\n"
            "Root-server mode (--root): serve any _referia.yml found under a root "
            "directory, each addressable by its path in the URL."
        ),
    )
    serve.add_argument(
        "--config",
        default="_referia.yml",
        metavar="FILE",
        help="Config filename for single-config mode (default: _referia.yml). "
             "Ignored when --root is supplied.",
    )
    serve.add_argument(
        "--directory",
        default=None,
        metavar="DIR",
        help="Review directory for single-config mode (default: current directory). "
             "Cannot be combined with --root.",
    )
    serve.add_argument(
        "--root",
        default=None,
        metavar="DIR",
        help="Root directory for multi-config (root-server) mode.  When given, "
             "all _referia.yml files found under this directory are served at "
             "their relative path (e.g. /theses/examined/introduction/).  "
             "Cannot be combined with --directory.",
    )
    serve.add_argument(
        "--host",
        default="127.0.0.1",
        help="Network interface to bind (default: 127.0.0.1)",
    )
    serve.add_argument(
        "--port",
        type=int,
        default=8000,
        help="TCP port to listen on (default: 8000)",
    )

    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        _serve(args)
    else:
        parser.print_help()
        sys.exit(1)


def _serve(args):
    try:
        import uvicorn
    except ImportError:
        print(
            "uvicorn is required to run the web interface.  "
            "Install it with:  poetry install",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate mutually exclusive options
    if args.root is not None and args.directory is not None:
        print(
            "error: --root and --directory cannot be used together.\n"
            "  Use --root for multi-config (root-server) mode.\n"
            "  Use --directory for single-config mode.",
            file=sys.stderr,
        )
        sys.exit(1)

    from referia.web.app import create_app

    if args.root is not None:
        app = create_app(root=args.root)
        print(f"Starting referia root-server at http://{args.host}:{args.port}")
        print(f"  Root:   {args.root}")
        print("  Any _referia.yml under the root is served at its relative path.")
    else:
        directory = args.directory if args.directory is not None else "."
        app = create_app(user_file=args.config, directory=directory)
        print(f"Starting referia review interface at http://{args.host}:{args.port}")
        print(f"  Config:    {args.config}")
        print(f"  Directory: {directory}")

    print("Press Ctrl+C to stop.")
    uvicorn.run(app, host=args.host, port=args.port)
