"""Shared option types for Gateway service CLI commands."""

from __future__ import annotations

from typing import Any, TypedDict


class GatewayRpcOpts(TypedDict, total=False):
    url: str
    token: str
    password: str
    timeout: str
    json: bool


class DaemonStatusOptions(TypedDict, total=False):
    rpc: GatewayRpcOpts
    probe: bool
    requireRpc: bool
    json: bool
    deep: bool


class DaemonInstallOptions(TypedDict, total=False):
    port: str | int
    runtime: str
    token: str
    wrapper: str
    force: bool
    json: bool


class DaemonLifecycleOptions(TypedDict, total=False):
    json: bool
    force: bool
    safe: bool
    skipDeferral: bool
    wait: str
    disable: bool
