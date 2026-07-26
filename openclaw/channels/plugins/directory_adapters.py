"""Channel directory adapter helpers.

Mirrors src/channels/plugins/directory-adapters.ts.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict


class ChannelDirectoryEntry(TypedDict):
    kind: str
    id: str


DirectoryListParams = dict[str, Any]
DirectorySelfParams = dict[str, Any]


async def null_channel_directory_self(_params: DirectorySelfParams) -> None:
    return None


async def empty_channel_directory_list(_params: DirectoryListParams) -> list[ChannelDirectoryEntry]:
    return []


def create_channel_directory_adapter(
    *,
    list_peers: Callable[[DirectoryListParams], Awaitable[list[ChannelDirectoryEntry]]]
    | None = None,
    list_groups: Callable[[DirectoryListParams], Awaitable[list[ChannelDirectoryEntry]]]
    | None = None,
    self: Callable[[DirectorySelfParams], Awaitable[ChannelDirectoryEntry | None]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    adapter: dict[str, Any] = {
        "self": self or null_channel_directory_self,
        **extra,
    }
    if list_peers is not None:
        adapter["listPeers"] = list_peers
    if list_groups is not None:
        adapter["listGroups"] = list_groups
    return adapter


def create_empty_channel_directory_adapter() -> dict[str, Any]:
    return create_channel_directory_adapter(
        list_peers=empty_channel_directory_list,
        list_groups=empty_channel_directory_list,
    )
