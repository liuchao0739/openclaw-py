from __future__ import annotations

import sys
from typing import Any

FLAG_TERMINATOR = "--"
HELP_FLAGS = {"-h", "--help"}
VERSION_FLAGS = {"-V", "--version"}
ROOT_VERSION_ALIAS_FLAG = "-v"

try:
    from openclaw.infra.cli_root_options import consume_root_option_token, is_value_token
except ImportError:
    def consume_root_option_token(args: list[str], index: int) -> int:
        return 0

    def is_value_token(value: str | None) -> bool:
        return bool(value) and not value.startswith("-")


def _parse_positive_int(value: str) -> int | None:
    try:
        parsed = int(value)
    except (ValueError, TypeError):
        return None
    return parsed if parsed > 0 else None


def has_help_or_version(argv: list[str]) -> bool:
    return any(arg in HELP_FLAGS or arg in VERSION_FLAGS for arg in argv) or has_root_version_alias(argv)


def has_flag(argv: list[str], name: str) -> bool:
    args = argv[2:]
    for arg in args:
        if arg == FLAG_TERMINATOR:
            break
        if arg == name:
            return True
    return False


def has_root_version_alias(argv: list[str]) -> bool:
    args = argv[2:]
    has_alias = False
    for i in range(len(args)):
        arg = args[i]
        if not arg:
            continue
        if arg == FLAG_TERMINATOR:
            break
        if arg == ROOT_VERSION_ALIAS_FLAG:
            has_alias = True
            continue
        consumed = consume_root_option_token(args, i)
        if consumed > 0:
            i += consumed - 1
            continue
        if arg.startswith("-"):
            return False
        return False
    return has_alias


def is_root_version_invocation(argv: list[str]) -> bool:
    return _is_root_invocation_for_flags(argv, VERSION_FLAGS, include_version_alias=True)


def is_root_help_invocation(argv: list[str]) -> bool:
    return _is_root_invocation_for_flags(argv, HELP_FLAGS)


def _is_root_invocation_for_flags(
    argv: list[str], target_flags: set[str], include_version_alias: bool = False
) -> bool:
    args = argv[2:]
    has_target = False
    for i in range(len(args)):
        arg = args[i]
        if not arg:
            continue
        if arg == FLAG_TERMINATOR:
            break
        if arg in target_flags or (include_version_alias and arg == ROOT_VERSION_ALIAS_FLAG):
            has_target = True
            continue
        consumed = consume_root_option_token(args, i)
        if consumed > 0:
            i += consumed - 1
            continue
        return False
    return has_target


def is_help_or_version_invocation(argv: list[str]) -> bool:
    if has_root_version_alias(argv):
        return True
    args = argv[2:]
    saw_command_option = False
    positionals: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if not arg or arg == FLAG_TERMINATOR:
            break
        root_consumed = consume_root_option_token(args, i)
        if root_consumed > 0:
            i += root_consumed
            continue
        if arg in HELP_FLAGS or arg in VERSION_FLAGS:
            return True
        if arg.startswith("-"):
            saw_command_option = True
            i += 1
            continue
        positionals.append(arg)
        if arg == "help":
            if saw_command_option:
                return False
            if len(positionals) == 1:
                return True
        i += 1
    return False


def get_flag_value(argv: list[str], name: str) -> str | None:
    args = argv[2:]
    value: str | None = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == FLAG_TERMINATOR:
            break
        if arg == name:
            next_val = args[i + 1] if i + 1 < len(args) else None
            if not is_value_token(next_val):
                return None
            value = next_val
            i += 2
            continue
        if arg.startswith(f"{name}="):
            assigned = arg[len(name) + 1 :]
            if not assigned:
                return None
            value = assigned
        i += 1
    return value


def get_verbose_flag(argv: list[str], options: dict | None = None) -> bool:
    if has_flag(argv, "--verbose"):
        return True
    opts = options or {}
    if opts.get("includeDebug") and has_flag(argv, "--debug"):
        return True
    return False


def get_positive_int_flag_value(argv: list[str], name: str) -> int | None:
    raw = get_flag_value(argv, name)
    if raw is None:
        return None
    return _parse_positive_int(raw)


def get_command_path_with_root_options(argv: list[str], depth: int = 2) -> list[str]:
    args = argv[2:]
    path: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if not arg:
            i += 1
            continue
        if arg == "--":
            break
        consumed = consume_root_option_token(args, i)
        if consumed > 0:
            i += consumed
            continue
        if arg.startswith("-"):
            i += 1
            continue
        path.append(arg)
        if len(path) >= depth:
            break
        i += 1
    return path


def get_primary_command(argv: list[str]) -> str | None:
    path = get_command_path_with_root_options(argv, 1)
    return path[0] if path else None


def should_migrate_state_from_path(path: list[str]) -> bool:
    if not path:
        return True
    primary = path[0]
    secondary = path[1] if len(path) > 1 else None
    if primary in ("health", "sessions"):
        return False
    if primary == "update" and secondary == "status":
        return False
    if primary == "config" and secondary in ("get", "unset"):
        return False
    return True
