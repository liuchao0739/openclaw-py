"""Shared command argument shapes for auto-reply command parsing."""

from __future__ import annotations

from typing import Any, TypedDict, Union

CommandArgValue = Union[str, int, float, bool]
CommandArgValues = dict[str, CommandArgValue]


class CommandArgs(TypedDict, total=False):
    raw: str
    values: CommandArgValues
