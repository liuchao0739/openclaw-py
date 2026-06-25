"""Shared RPC option shape for gateway CLI commands."""

from __future__ import annotations

from typing import TypedDict


class GatewayRpcOpts(TypedDict, total=False):
    url: str
    token: str
    timeout: str
    expectFinal: bool
    json: bool
