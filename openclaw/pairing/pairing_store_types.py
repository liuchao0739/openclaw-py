"""Shared type contracts for pairing challenge and channel binding records.

Mirrors src/pairing/pairing-store.types.ts.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Mapping, TypedDict

# PairingChannel is a channel id alias.
PairingChannel = str


class UpsertPairingResult(TypedDict):
    code: str
    created: bool


# Callable type aliases (kept as plain types for simplicity).
ReadChannelAllowFromStoreForAccount = Callable[..., Awaitable[list[str]]]
UpsertChannelPairingRequestForAccount = Callable[..., Awaitable[UpsertPairingResult]]
