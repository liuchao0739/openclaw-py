"""Command tree mutation helpers used by lazy command replacement."""

from __future__ import annotations

from typing import Any


def remove_command(program: Any, command: Any) -> bool:
    """Remove an exact command instance from a parent program."""
    commands = getattr(program, "commands", [])
    try:
        index = commands.index(command)
    except (ValueError, AttributeError):
        return False
    commands.pop(index)
    return True


def remove_command_by_name(program: Any, name: str) -> bool:
    """Remove a command by primary name or alias."""
    commands = getattr(program, "commands", [])
    for cmd in commands:
        cmd_name = getattr(cmd, "name", None)
        if callable(cmd_name):
            cmd_name = cmd_name()
        if cmd_name == name:
            return remove_command(program, cmd)
        aliases = getattr(cmd, "aliases", None)
        if callable(aliases):
            aliases = aliases()
        if isinstance(aliases, list) and name in aliases:
            return remove_command(program, cmd)
    return False
