"""Codex app-server config helpers."""

from __future__ import annotations

import os
from typing import Any

from openclaw.packages.normalization_core import is_record


def read_codex_plugin_config(value: Any) -> dict[str, Any]:
    if not is_record(value):
        return {}
    config = dict(value)
    codex_plugins = config.pop("codexPlugins", None)
    if codex_plugins is not None and is_record(codex_plugins):
        config["codexPlugins"] = dict(codex_plugins)
    return config


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.split() if part.strip()]
    return []


def resolve_codex_app_server_runtime_options(params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = params or {}
    env = params.get("env") if isinstance(params.get("env"), dict) else dict(os.environ)
    plugin_config = read_codex_plugin_config(params.get("pluginConfig"))
    config = plugin_config.get("appServer") if is_record(plugin_config.get("appServer")) else {}

    transport = config.get("transport") if config.get("transport") in {"stdio", "websocket"} else "stdio"
    config_command = config.get("command").strip() if isinstance(config.get("command"), str) else None
    env_command = env.get("OPENCLAW_CODEX_APP_SERVER_BIN", "").strip()
    command = config_command or env_command or "codex"
    if config_command:
        command_source = "config"
    elif env_command:
        command_source = "env"
    else:
        command_source = "managed"

    args = _normalize_string_list(config.get("args") or env.get("OPENCLAW_CODEX_APP_SERVER_ARGS"))
    url = config.get("url").strip() if isinstance(config.get("url"), str) and config.get("url").strip() else None

    start: dict[str, Any] = {
        "transport": transport,
        "command": command,
        "commandSource": command_source,
        "args": args or ["app-server", "--listen", "stdio://"],
        "headers": {},
    }
    if url:
        start["url"] = url

    clear_env = _normalize_string_list(config.get("clearEnv"))
    if transport == "stdio" and clear_env:
        start["clearEnv"] = clear_env

    approval_policy = config.get("approvalPolicy")
    if approval_policy not in {"never", "on-request", "on-failure", "untrusted"}:
        approval_policy = "on-request"
    sandbox = config.get("sandbox")
    if sandbox not in {"read-only", "workspace-write", "danger-full-access"}:
        sandbox = "workspace-write"
    approvals_reviewer = config.get("approvalsReviewer")
    if approvals_reviewer not in {"user", "auto_review", "guardian_subagent"}:
        approvals_reviewer = "user"

    request_timeout_ms = config.get("requestTimeoutMs")
    if not isinstance(request_timeout_ms, (int, float)) or request_timeout_ms <= 0:
        request_timeout_ms = 60_000

    return {
        "start": start,
        "connectionClass": "local-loopback",
        "remoteAppsSubstrate": "preconfigured",
        "codeModeOnly": config.get("codeModeOnly") is True,
        "requestTimeoutMs": int(request_timeout_ms),
        "approvalPolicy": approval_policy,
        "sandbox": sandbox,
        "approvalsReviewer": approvals_reviewer,
        "serviceTier": config.get("serviceTier"),
    }
