---
id: "2026-07-15_cip000C-cli-root-option"
title: "Add --root option to referia serve CLI"
status: "Ready"
priority: "Medium"
created: "2026-07-15"
last_updated: "2026-07-15"
related_cips: ["000C"]
---

# Task: Add --root option to referia serve CLI

## Description

Extend the `referia serve` command with a `--root` option so users can start
a root-based multi-config server from the command line.

## Acceptance Criteria

- `referia serve --root ~/OneDrive/referia/ --port 8765` starts the server
  in root mode.
- `referia serve` (no `--root`) continues to look for `_referia.yml` in the
  current directory (unchanged behaviour).
- `referia serve --root .` is equivalent to using the current directory as root.
- `--help` output documents the `--root` option with a clear description.
- An error is raised if both a positional `user_file` argument and `--root`
  are supplied simultaneously.

## Implementation Notes

- The CLI entry point is likely in `referia/__main__.py` or a `cli.py` module.
  Confirm location before implementing.
- Pass `root` through to `create_app()`.

## Related

- CIP: 000C
- Task: 2026-07-15_cip000C-create-app-root-refactor
