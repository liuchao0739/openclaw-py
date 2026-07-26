"""Config parsing for Codex Supervisor endpoints and safety gates."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, TypedDict

from openclaw.packages.normalization_core import is_record
from openclaw_extensions.codex_supervisor.src.types import CodexSupervisorEndpoint

ENDPOINTS_ENV = "OPENCLAW_CODEX_SUPERVISOR_ENDPOINTS"
_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "openclaw.plugin.json"


def _load_manifest_config_schema() -> dict[str, Any]:
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    schema = manifest.get("configSchema")
    if not is_record(schema):
        raise ValueError("codex-supervisor plugin manifest is missing configSchema")
    return schema


def _safe_parse(value: Any) -> dict[str, Any]:
    if value is None:
        return {"success": True, "data": None}
    if not is_record(value):
        return {
            "success": False,
            "error": {"issues": [{"path": [], "message": "expected config object"}]},
        }
    return {"success": True, "data": value}


codex_supervisor_plugin_config_schema: dict[str, Any] = {
    "safeParse": _safe_parse,
    "jsonSchema": _load_manifest_config_schema(),
}


class ResolvedCodexSupervisorPluginConfig(TypedDict):
    endpoints: list[CodexSupervisorEndpoint]
    allowRawTranscripts: bool
    allowWriteControls: bool


def normalize_endpoint_id(value: str, index: int) -> str:
    trimmed = value.strip()
    if trimmed:
        return re.sub(r"[^a-zA-Z0-9_.:-]", "-", trimmed)
    return f"endpoint-{index + 1}"


def parse_endpoint_record(value: Any, index: int) -> CodexSupervisorEndpoint | None:
    if not is_record(value):
        return None
    transport = value.get("transport")
    transport_str = transport if isinstance(transport, str) else None
    raw_id = value.get("id")
    raw_label = value.get("label")
    endpoint_id = (
        normalize_endpoint_id(str(raw_id), index)
        if isinstance(raw_id, str)
        else normalize_endpoint_id(str(raw_label) if isinstance(raw_label, str) else "", index)
    )
    label = raw_label if isinstance(raw_label, str) else None
    if transport_str == "websocket" and isinstance(value.get("url"), str):
        endpoint: CodexSupervisorEndpoint = {
            "id": endpoint_id,
            "transport": "websocket",
            "url": value["url"],
        }
        if label:
            endpoint["label"] = label
        auth_token_env = value.get("authTokenEnv")
        if isinstance(auth_token_env, str):
            endpoint["authTokenEnv"] = auth_token_env
        return endpoint
    if transport_str == "stdio-proxy" or transport_str is None:
        endpoint = {"id": endpoint_id, "transport": "stdio-proxy"}
        if label:
            endpoint["label"] = label
        command = value.get("command")
        if isinstance(command, str):
            endpoint["command"] = command
        args = value.get("args")
        if isinstance(args, list):
            string_args = [entry for entry in args if isinstance(entry, str)]
            if string_args:
                endpoint["args"] = string_args
        cwd = value.get("cwd")
        if isinstance(cwd, str):
            endpoint["cwd"] = cwd
        return endpoint
    return None


def require_unique_endpoint_ids(
    endpoints: list[CodexSupervisorEndpoint],
) -> list[CodexSupervisorEndpoint]:
    seen: set[str] = set()
    for endpoint in endpoints:
        endpoint_id = endpoint["id"]
        if endpoint_id in seen:
            raise ValueError(f"duplicate Codex supervisor endpoint id: {endpoint_id}")
        seen.add(endpoint_id)
    return endpoints


def endpoint_from_token(token: str, index: int) -> CodexSupervisorEndpoint | None:
    trimmed = token.strip()
    if not trimmed:
        return None
    if trimmed.startswith(("ws://", "wss://", "unix://")):
        return {
            "id": normalize_endpoint_id("", index),
            "transport": "websocket",
            "url": trimmed,
        }
    if trimmed in ("local", "proxy", "stdio"):
        return {
            "id": "local",
            "label": "local Codex app-server daemon",
            "transport": "websocket",
            "url": "unix://",
        }
    separator_index = trimmed.find("=")
    endpoint_id = trimmed[:separator_index] if separator_index >= 0 else trimmed
    url = trimmed[separator_index + 1 :] if separator_index >= 0 else None
    if url and url.startswith(("ws://", "wss://", "unix://")):
        return {
            "id": normalize_endpoint_id(endpoint_id, index),
            "transport": "websocket",
            "url": url,
        }
    return None


def load_codex_supervisor_endpoints(
    env: dict[str, str] | None = None,
) -> list[CodexSupervisorEndpoint]:
    """Load endpoint definitions from environment, defaulting to the local unix socket."""
    env_map = env if env is not None else os.environ
    raw = (env_map.get(ENDPOINTS_ENV) or "").strip()
    if not raw:
        return require_unique_endpoint_ids(
            [
                {
                    "id": "local",
                    "label": "local Codex app-server daemon",
                    "transport": "websocket",
                    "url": "unix://",
                }
            ]
        )
    if raw.startswith("["):
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError(f"{ENDPOINTS_ENV} must be a JSON array")
        normalized = [
            entry
            for index, item in enumerate(parsed)
            if (entry := parse_endpoint_record(item, index)) is not None
        ]
        return require_unique_endpoint_ids(normalized)
    tokens = [endpoint_from_token(token, index) for index, token in enumerate(raw.split(","))]
    return require_unique_endpoint_ids([entry for entry in tokens if entry is not None])


def normalize_configured_endpoints(
    endpoints: list[Any] | None,
) -> list[CodexSupervisorEndpoint] | None:
    if not endpoints:
        return None
    normalized = [
        entry
        for index, item in enumerate(endpoints)
        if (entry := parse_endpoint_record(item, index)) is not None
    ]
    return require_unique_endpoint_ids(normalized) if normalized else None


def resolve_codex_supervisor_plugin_config(
    raw_config: Any,
    env: dict[str, str] | None = None,
) -> ResolvedCodexSupervisorPluginConfig:
    """Resolve raw plugin config and env endpoints into validated runtime config."""
    config = raw_config if is_record(raw_config) else {}
    configured = config.get("endpoints")
    endpoint_list = configured if isinstance(configured, list) else None
    return {
        "endpoints": normalize_configured_endpoints(endpoint_list)
        or load_codex_supervisor_endpoints(env),
        "allowRawTranscripts": config.get("allowRawTranscripts") is True,
        "allowWriteControls": config.get("allowWriteControls") is True,
    }
