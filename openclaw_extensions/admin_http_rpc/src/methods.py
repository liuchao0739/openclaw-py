from __future__ import annotations

from typing import Any

ADMIN_HTTP_RPC_ALLOWED_METHOD_GROUPS: dict[str, tuple[str, ...]] = {
    "gateway": (
        "health",
        "status",
        "logs.tail",
        "usage.status",
        "usage.cost",
        "gateway.restart.request",
    ),
    "discovery": ("commands.list",),
    "config": (
        "config.get",
        "config.schema",
        "config.schema.lookup",
        "config.set",
        "config.patch",
        "config.apply",
    ),
    "channels": ("channels.status", "channels.start", "channels.stop", "channels.logout"),
    "web": ("web.login.start", "web.login.wait"),
    "models": ("models.list", "models.authStatus"),
    "agents": ("agents.list", "agents.create", "agents.update", "agents.delete"),
    "approvals": (
        "exec.approvals.get",
        "exec.approvals.set",
        "exec.approvals.node.get",
        "exec.approvals.node.set",
    ),
    "cron": (
        "cron.status",
        "cron.list",
        "cron.get",
        "cron.runs",
        "cron.add",
        "cron.update",
        "cron.remove",
        "cron.run",
    ),
    "devices": (
        "device.pair.list",
        "device.pair.approve",
        "device.pair.reject",
        "device.pair.remove",
    ),
    "nodes": (
        "node.list",
        "node.describe",
        "node.pair.list",
        "node.pair.approve",
        "node.pair.reject",
        "node.pair.remove",
        "node.rename",
    ),
    "tasks": ("tasks.list", "tasks.get", "tasks.cancel"),
    "diagnostics": ("doctor.memory.status", "update.status"),
}

ADMIN_HTTP_RPC_ALLOWED_METHODS: set[str] = set()
for group in ADMIN_HTTP_RPC_ALLOWED_METHOD_GROUPS.values():
    ADMIN_HTTP_RPC_ALLOWED_METHODS.update(group)


def is_admin_http_rpc_allowed_method(method: str) -> bool:
    return method in ADMIN_HTTP_RPC_ALLOWED_METHODS


def list_admin_http_rpc_allowed_methods() -> list[str]:
    return sorted(ADMIN_HTTP_RPC_ALLOWED_METHODS)