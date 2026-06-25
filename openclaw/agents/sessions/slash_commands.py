"""Slash command info and resolution.

Tracks available slash commands and their sources for the session UI.
"""

from __future__ import annotations

from typing import Literal, TypedDict

SlashCommandSource = Literal["builtin", "extension", "skill", "custom"]


class SlashCommandInfo(TypedDict, total=False):
    name: str
    description: str
    source: SlashCommandSource
    sourceInfo: Any  # forward ref to SourceInfo


from typing import Any  # noqa: E402


def create_slash_command_info(
    name: str,
    description: str = "",
    source: SlashCommandSource = "builtin",
    source_info: Any = None,
) -> SlashCommandInfo:
    """Create a slash command info entry."""
    info: SlashCommandInfo = {
        "name": name,
        "description": description,
        "source": source,
    }
    if source_info is not None:
        info["sourceInfo"] = source_info
    return info


def is_builtin_command(info: SlashCommandInfo) -> bool:
    return info.get("source") == "builtin"


def is_extension_command(info: SlashCommandInfo) -> bool:
    return info.get("source") == "extension"
