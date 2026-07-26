"""Copilot attempt runtime boundaries (partial port)."""

from __future__ import annotations

from typing import Any, TypedDict

from openclaw_extensions.copilot.harness_support import get_model_provider_request_transport
from openclaw_extensions.copilot.src.auth_bridge import (
    create_copilot_byok_auth,
    resolve_copilot_auth,
)
from openclaw_extensions.copilot.src.provider_bridge import resolve_copilot_provider


class CopilotSessionConfig(TypedDict, total=False):
    available_tools: list[Any]
    model: str
    tools: list[Any]
    working_directory: str
    provider: dict[str, Any]


def _read_string(value: object) -> str | None:
    return value if isinstance(value, str) and len(value) > 0 else None


def _read_param(params: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _read_string(params.get(key))
        if value:
            return value
    return None


def _normalize_auth_override(auth: object) -> dict[str, Any] | None:
    if not isinstance(auth, dict):
        return None
    return {
        "use_logged_in_user": auth.get("useLoggedInUser") is True or auth.get("use_logged_in_user") is True,
        "git_hub_token": _read_param(auth, "gitHubToken", "git_hub_token"),
        "profile_id": _read_param(auth, "profileId", "profile_id"),
        "profile_version": _read_param(auth, "profileVersion", "profile_version"),
    }


def resolve_model_ref(params: dict[str, Any]) -> dict[str, Any]:
    raw_model = params.get("runtimeModel") or params.get("runtime_model") or params.get("model")
    if isinstance(raw_model, dict):
        request_transport = get_model_provider_request_transport(raw_model)
        raw_request = raw_model.get("request") if isinstance(raw_model.get("request"), dict) else {}
        return {
            "api": _read_string(raw_model.get("api")),
            "id": _read_string(raw_model.get("id"))
            or _read_param(params, "modelId", "model_id")
            or "unknown-model",
            "provider": _read_string(raw_model.get("provider"))
            or _read_param(params, "provider")
            or "unknown-provider",
            "base_url": _read_string(raw_model.get("baseUrl") or raw_model.get("base_url")),
            "azure_api_version": _read_string(
                raw_model.get("azureApiVersion")
                or raw_model.get("azure_api_version")
                or (
                    raw_model.get("params", {}).get("azureApiVersion")
                    if isinstance(raw_model.get("params"), dict)
                    else None
                )
            ),
            "headers": raw_model.get("headers") if isinstance(raw_model.get("headers"), dict) else None,
            "auth_header": raw_model.get("authHeader")
            if "authHeader" in raw_model
            else raw_model.get("auth_header"),
            "request_auth_mode": _read_string(
                (request_transport or {}).get("auth", {}).get("mode")
                if isinstance((request_transport or {}).get("auth"), dict)
                else None
            )
            or _read_string(raw_request.get("auth", {}).get("mode") if isinstance(raw_request.get("auth"), dict) else None),
            "request_proxy": (request_transport or {}).get("proxy") or raw_request.get("proxy"),
            "request_tls": (request_transport or {}).get("tls") or raw_request.get("tls"),
            "request_allow_private_network": (request_transport or {}).get("allowPrivateNetwork")
            or raw_request.get("allowPrivateNetwork"),
            "context_tokens": raw_model.get("contextTokens") or raw_model.get("context_tokens"),
            "context_window": raw_model.get("contextWindow") or raw_model.get("context_window"),
            "max_tokens": raw_model.get("maxTokens") or raw_model.get("max_tokens"),
        }
    return {
        "id": _read_string(raw_model if isinstance(raw_model, str) else None)
        or _read_param(params, "modelId", "model_id")
        or "unknown-model",
        "provider": _read_param(params, "provider") or "unknown-provider",
    }


def resolve_pool_acquire(params: dict[str, Any]) -> dict[str, Any]:
    model = resolve_model_ref(params)
    provider = resolve_copilot_provider(
        model=model,  # type: ignore[arg-type]
        resolved_api_key=_read_param(params, "resolvedApiKey", "resolved_api_key"),
        auth_profile_id=_read_param(params, "authProfileId", "auth_profile_id"),
    )
    auth_override = _normalize_auth_override(params.get("auth"))
    auth = (
        create_copilot_byok_auth(
            agent_id=_read_param(params, "agentId", "agent_id"),
            agent_dir=_read_param(params, "agentDir", "agent_dir"),
            workspace_dir=_read_param(params, "workspaceDir", "workspace_dir"),
            copilot_home=_read_param(params, "copilotHome", "copilot_home"),
            auth_profile_id=provider.get("auth_profile_id"),
            auth_profile_version=provider.get("auth_profile_version"),
        )
        if provider.get("mode") == "byok"
        else resolve_copilot_auth(
            {
                "agent_id": _read_param(params, "agentId", "agent_id"),
                "agent_dir": _read_param(params, "agentDir", "agent_dir"),
                "workspace_dir": _read_param(params, "workspaceDir", "workspace_dir"),
                "copilot_home": _read_param(params, "copilotHome", "copilot_home"),
                "auth": auth_override,
                "resolved_api_key": _read_param(params, "resolvedApiKey", "resolved_api_key"),
                "auth_profile_id": _read_param(params, "authProfileId", "auth_profile_id"),
                "profile_version": _read_param(params, "profileVersion", "profile_version"),
            }
        )
    )
    auth_mode = auth["auth_mode"]
    key: dict[str, Any] = {
        "agentId": auth["agent_id"],
        "authMode": auth_mode,
        "copilotHome": auth["copilot_home"],
    }
    if auth_mode in ("gitHubToken", "byok"):
        key["authProfileId"] = auth.get("auth_profile_id")
        key["authProfileVersion"] = auth.get("auth_profile_version")
    options: dict[str, Any] = {
        "copilotHome": auth["copilot_home"],
        "useLoggedInUser": auth_mode == "useLoggedInUser",
    }
    if auth_mode == "gitHubToken" and auth.get("git_hub_token"):
        options["gitHubToken"] = auth["git_hub_token"]
    return {
        "key": key,
        "options": options,
        "auth": {
            "agentId": auth["agent_id"],
            "authMode": auth_mode,
            "copilotHome": auth["copilot_home"],
            **(
                {
                    "authProfileId": auth.get("auth_profile_id"),
                    "authProfileVersion": auth.get("auth_profile_version"),
                }
                if auth_mode in ("gitHubToken", "byok")
                else {}
            ),
            **({"gitHubToken": auth["git_hub_token"]} if auth_mode == "gitHubToken" else {}),
        },
        "provider": provider,
    }


async def run_copilot_attempt(_params: dict[str, Any], _deps: dict[str, Any] | None = None) -> Any:
    raise NotImplementedError(
        "run_copilot_attempt is not yet ported; the GitHub Copilot Python SDK integration is pending"
    )
