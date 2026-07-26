"""Tests for Google Chat directory contract plugin."""

from __future__ import annotations

import pytest

from openclaw_extensions.googlechat.directory_contract_api import (
    googlechat_directory_contract_plugin,
)
from openclaw_extensions.googlechat.src.channel_adapters import googlechat_directory_adapter


def _expect_directory_surface(adapter: dict) -> dict:
    assert callable(adapter.get("listPeers"))
    assert callable(adapter.get("listGroups"))
    return adapter


@pytest.mark.asyncio
async def test_googlechat_directory_contract_plugin_shape() -> None:
    plugin = googlechat_directory_contract_plugin
    assert plugin["id"] == "googlechat"
    directory = _expect_directory_surface(plugin["directory"])
    assert directory is googlechat_directory_adapter


@pytest.mark.asyncio
async def test_lists_peers_and_groups_from_config() -> None:
    cfg = {
        "channels": {
            "googlechat": {
                "serviceAccount": {"client_email": "bot@example.com"},
                "dm": {"allowFrom": ["users/alice", "googlechat:bob"]},
                "groups": {
                    "spaces/AAA": {},
                    "spaces/BBB": {},
                },
            }
        }
    }
    directory = _expect_directory_surface(googlechat_directory_adapter)
    runtime: dict = {}

    peers = await directory["listPeers"](
        {
            "cfg": cfg,
            "accountId": None,
            "query": None,
            "limit": None,
            "runtime": runtime,
        }
    )
    assert peers == [
        {"kind": "user", "id": "users/alice"},
        {"kind": "user", "id": "bob"},
    ]

    groups = await directory["listGroups"](
        {
            "cfg": cfg,
            "accountId": None,
            "query": None,
            "limit": None,
            "runtime": runtime,
        }
    )
    assert groups == [
        {"kind": "group", "id": "spaces/AAA"},
        {"kind": "group", "id": "spaces/BBB"},
    ]


@pytest.mark.asyncio
async def test_normalizes_spaced_provider_prefixed_dm_allowlist_entries() -> None:
    cfg = {
        "channels": {
            "googlechat": {
                "serviceAccount": {"client_email": "bot@example.com"},
                "dm": {"allowFrom": [" users/alice ", " googlechat:user:Bob@Example.com "]},
            }
        }
    }
    directory = _expect_directory_surface(googlechat_directory_adapter)

    peers = await directory["listPeers"](
        {
            "cfg": cfg,
            "accountId": None,
            "query": None,
            "limit": None,
            "runtime": {},
        }
    )
    assert peers == [
        {"kind": "user", "id": "users/alice"},
        {"kind": "user", "id": "users/bob@example.com"},
    ]
