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

    check = subparsers.add_parser(
        "check",
        help="Lint all _referia.yml files under a root directory",
        description=(
            "Scan every _referia.yml under --root and report any YAML parse "
            "errors.  Exits 0 when all configs are valid, non-zero otherwise.  "
            "Use --format json to get machine-readable output suitable for "
            "piping to an LLM for automated fixing."
        ),
    )
    check.add_argument(
        "--root",
        required=True,
        metavar="DIR",
        help="Root directory to scan recursively for _referia.yml files.",
    )
    check.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: 'text' (default, human-readable) or 'json' (LLM-friendly).",
    )
    check.add_argument(
        "--errors-only",
        action="store_true",
        help="In text mode, suppress the summary and show only failing files.",
    )

    migrate = subparsers.add_parser(
        "migrate",
        help="Stamp or rewrite _referia.yml dialect versions",
        description=(
            "Migrate referia config dialects under --root.  "
            "Default is dry-run full rewrite.  Use --stamp-only to insert "
            "referia_config_version without rewriting keys; "
            "add --write to apply changes.  Full rewrite may lose comments."
        ),
    )
    migrate.add_argument(
        "--root",
        required=True,
        metavar="DIR",
        help="Root directory to scan recursively for _referia.yml files.",
    )
    migrate.add_argument(
        "--stamp-only",
        action="store_true",
        help="Insert referia_config_version only (no key rewrites).",
    )
    migrate.add_argument(
        "--write",
        action="store_true",
        help="Apply changes. Without this flag, only report what would happen.",
    )
    migrate.add_argument(
        "--in-place",
        action="store_true",
        help=(
            "With full rewrite --write: overwrite originals (keeps .bak). "
            "Default write target is sibling _referia.migrated.yml. "
            "Ignored with --stamp-only."
        ),
    )
    migrate.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: 'text' (default) or 'json'.",
    )

    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        _serve(args)
    elif args.command == "check":
        _check(args)
    elif args.command == "migrate":
        _migrate(args)
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


def _check(args):
    """Implement ``referia check`` subcommand."""
    from referia.check import scan_configs, format_text, format_json

    results = scan_configs(args.root)
    errors = [r for r in results if not r["ok"]]

    if args.format == "json":
        print(format_json(results, args.root))
    else:
        if args.errors_only:
            for r in errors:
                loc = f":{r['line']}" if r["line"] is not None else ""
                err = (r["error"] or "").splitlines()[0]
                print(f"{r['path']}{loc}: [{r['category']}] {err}")
        else:
            print(format_text(results, args.root))

    sys.exit(1 if errors else 0)


def _migrate(args):
    """Implement ``referia migrate`` subcommand."""
    if args.stamp_only:
        from referia.migrate import (
            apply_stamp,
            format_stamp_json,
            format_stamp_text,
            scan_for_stamp,
        )

        if args.in_place:
            print(
                "note: --in-place is ignored with --stamp-only "
                "(stamp always edits the original file).",
                file=sys.stderr,
            )

        planned = scan_for_stamp(args.root)
        results = apply_stamp(planned, write=args.write)
        if args.format == "json":
            print(format_stamp_json(results, args.root, write=args.write))
        else:
            print(format_stamp_text(results, args.root, write=args.write))
    else:
        from referia.migrate import (
            apply_rewrite,
            format_rewrite_json,
            format_rewrite_text,
            scan_for_rewrite,
        )

        planned = scan_for_rewrite(args.root)
        results = apply_rewrite(
            planned, write=args.write, in_place=args.in_place
        )
        if args.format == "json":
            print(
                format_rewrite_json(
                    results,
                    args.root,
                    write=args.write,
                    in_place=args.in_place,
                )
            )
        else:
            print(
                format_rewrite_text(
                    results,
                    args.root,
                    write=args.write,
                    in_place=args.in_place,
                )
            )

    errors = [r for r in results if r.get("action") == "error"]
    sys.exit(1 if errors else 0)
