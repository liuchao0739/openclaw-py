"""Shared option/result types for node CLI command modules."""

from __future__ import annotations

from typing import Any, TypedDict


class NodesRpcOpts(TypedDict, total=False):
    url: str
    token: str
    timeout: str
    json: bool
    node: str
    command: str
    params: str
    invokeTimeout: str
    idempotencyKey: str
    connected: bool
    lastConnected: str
    target: str
    cwd: str
    env: list[str]
    commandTimeout: str
    title: str
    body: str
    sound: str
    priority: str
    delivery: str
    name: str
    format: str
    deviceId: str
    duration: str
    screen: str
    fps: str
    audio: bool
