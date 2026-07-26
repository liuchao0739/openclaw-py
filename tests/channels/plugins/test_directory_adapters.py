"""Directory adapter tests.

Mirrors src/channels/plugins/directory-adapters.test.ts.
"""

from __future__ import annotations

import pytest

from openclaw.channels.plugins.directory_adapters import (
    create_channel_directory_adapter,
    create_empty_channel_directory_adapter,
    empty_channel_directory_list,
    null_channel_directory_self,
)


@pytest.mark.asyncio
async def test_defaults_self_to_null() -> None:
    adapter = create_channel_directory_adapter()
    assert await adapter["self"]({"cfg": {}, "runtime": {}}) is None


@pytest.mark.asyncio
async def test_preserves_provided_resolvers() -> None:
    async def list_peers(_params: dict) -> list[dict[str, str]]:
        return [{"kind": "user", "id": "u-1"}]

    adapter = create_channel_directory_adapter(list_peers=list_peers)
    assert await adapter["listPeers"]({"cfg": {}, "runtime": {}}) == [{"kind": "user", "id": "u-1"}]


@pytest.mark.asyncio
async def test_builds_empty_directory_adapters() -> None:
    adapter = create_empty_channel_directory_adapter()
    assert await adapter["self"]({"cfg": {}, "runtime": {}}) is None
    assert await adapter["listPeers"]({"cfg": {}, "runtime": {}}) == []
    assert await adapter["listGroups"]({"cfg": {}, "runtime": {}}) == []


@pytest.mark.asyncio
async def test_exports_standalone_null_empty_helpers() -> None:
    assert await null_channel_directory_self({"cfg": {}, "runtime": {}}) is None
    assert await empty_channel_directory_list({"cfg": {}, "runtime": {}}) == []
