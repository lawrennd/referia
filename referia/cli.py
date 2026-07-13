"""Command-line entry point for referia.

Usage::

    poetry run referia serve [--config _referia.yml] [--directory .] \\
                             [--host 127.0.0.1] [--port 8000]
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
            "Open the printed URL in any browser."
        ),
    )
    serve.add_argument(
        "--config",
        default="_referia.yml",
        metavar="FILE",
        help="Path to the referia configuration file (default: _referia.yml)",
    )
    serve.add_argument(
        "--directory",
        default=".",
        metavar="DIR",
        help="Review directory containing the config and data files (default: .)",
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

    from referia.web.app import create_app

    app = create_app(user_file=args.config, directory=args.directory)

    print(f"Starting referia review interface at http://{args.host}:{args.port}")
    print(f"  Config:    {args.config}")
    print(f"  Directory: {args.directory}")
    print("Press Ctrl+C to stop.")

    uvicorn.run(app, host=args.host, port=args.port)
