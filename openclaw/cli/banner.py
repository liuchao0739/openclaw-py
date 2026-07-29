from __future__ import annotations

import os
import sys
from typing import Any

from openclaw.cli.tagline import pick_tagline, TaglineMode
from openclaw.cli.banner_config_lite import parse_tagline_mode, read_cli_banner_tagline_mode

_banner_emitted = False


def _has_json_flag(argv: list[str]) -> bool:
    return any(arg == "--json" or arg.startswith("--json=") for arg in argv)


def _has_version_flag(argv: list[str]) -> bool:
    return any(arg in ("--version", "-V") for arg in argv)


def _resolve_tagline_mode(options: dict) -> str | None:
    explicit = parse_tagline_mode(options.get("mode"))
    if explicit:
        return explicit
    return read_cli_banner_tagline_mode(options.get("env"))


def _visible_width(text: str) -> int:
    import re

    return len(re.sub(r"\x1b\[[0-9;]*m", "", text))


def format_cli_banner_line(version: str, options: dict | None = None) -> str:
    opts = options or {}
    commit = opts.get("commit") or "unknown"
    tagline = pick_tagline({**opts, "mode": _resolve_tagline_mode(opts)})
    title = "🦞 OpenClaw"
    indent = "  "
    columns = opts.get("columns") or 120
    plain_base_line = f"{title} {version} ({commit})"
    plain_full_line = f"{plain_base_line} — {tagline}" if tagline else plain_base_line
    fits = _visible_width(plain_full_line) <= columns
    if fits:
        return plain_full_line
    if not tagline:
        return plain_base_line
    return f"{plain_base_line}\n{indent}{tagline}"


def emit_cli_banner(version: str, options: dict | None = None) -> None:
    global _banner_emitted
    if _banner_emitted:
        return
    opts = options or {}
    argv = opts.get("argv") or sys.argv
    is_tty = opts.get("isTty")
    if is_tty is None:
        is_tty = sys.stdout.isatty()
    if not is_tty:
        return
    if _has_json_flag(argv):
        return
    if _has_version_flag(argv):
        return
    line = format_cli_banner_line(version, opts)
    print(f"\n{line}\n")
    _banner_emitted = True


def has_emitted_cli_banner() -> bool:
    return _banner_emitted


def reset_banner_emitted_for_tests() -> None:
    global _banner_emitted
    _banner_emitted = False


__testing = type("testing", (), {"reset_banner_emitted_for_tests": reset_banner_emitted_for_tests})
