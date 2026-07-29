from __future__ import annotations

import os
import re
import sys

DEFAULT_CLI_NAME = "openclaw"
KNOWN_CLI_NAMES = {DEFAULT_CLI_NAME}
_CLI_PREFIX_RE = re.compile(r"^(?:((?:pnpm|npm|bunx|npx)\s+))?(openclaw)\b")


def resolve_cli_name(argv: list[str] | None = None) -> str:
    argv = argv if argv is not None else sys.argv
    if len(argv) < 2 or not argv[1]:
        return DEFAULT_CLI_NAME
    base = os.path.basename(argv[1]).strip()
    if base in KNOWN_CLI_NAMES:
        return base
    return DEFAULT_CLI_NAME


def replace_cli_name(command: str, cli_name: str | None = None) -> str:
    name = cli_name if cli_name is not None else resolve_cli_name()
    if not command.strip():
        return command
    if not _CLI_PREFIX_RE.search(command):
        return command
    return _CLI_PREFIX_RE.sub(lambda m: f"{m.group(1) or ''}{name}", command)
