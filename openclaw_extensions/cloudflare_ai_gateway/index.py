"""Bundled provider plugin entry for Cloudflare AI Gateway."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from openclaw.packages.normalization_core import is_record, normalize_optional_string
from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw.plugin_sdk.provider_auth_api_key import create_provider_api_key_auth_method
from openclaw_extensions.cloudflare_ai_gateway.catalog_provider import (
    build_cloudflare_ai_gateway_catalog_provider,
)
from openclaw_extensions.cloudflare_ai_gateway.models import CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF
from openclaw_extensions.cloudflare_ai_gateway.onboard import (
    apply_cloudflare_ai_gateway_config,
    build_cloudflare_ai_gateway_config_patch,
)
from openclaw_extensions.cloudflare_ai_gateway.stream_wrappers import (
    wrap_cloudflare_ai_gateway_provider_stream,
)

PROVIDER_ID = "cloudflare-ai-gateway"
PROVIDER_ENV_VAR = "CLOUDFLARE_AI_GATEWAY_API_KEY"
_PROFILE_ID = "cloudflare-ai-gateway:default"
_FAILOVER_PATTERN = re.compile(r"\bworkers?_ai\b.*\b(?:rate|limit|quota)\b", re.IGNORECASE)


def _load_auth_store(agent_dir: str) -> dict[str, Any]:
    auth_store_path = Path(agent_dir) / "auth-profiles.json"
    if not auth_store_path.is_file():
        return {"profiles": {}}
    try:
        payload = json.loads(auth_store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"profiles": {}}
    if not is_record(payload):
        return {"profiles": {}}
    profiles = payload.get("profiles")
    if not is_record(profiles):
        return {"profiles": {}}
    return {"profiles": profiles}


def _list_profiles_for_provider(auth_store: dict[str, Any], provider: str) -> list[str]:
    profiles = auth_store.get("profiles")
    if not is_record(profiles):
        return []
    return [
        profile_id
        for profile_id, profile in profiles.items()
        if is_record(profile) and profile.get("provider") == provider
    ]


async def _catalog_run(ctx: dict[str, Any]) -> dict[str, Any] | None:
    agent_dir = ctx.get("agentDir")
    if not isinstance(agent_dir, str) or not agent_dir.strip():
        return None
    auth_store = _load_auth_store(agent_dir.strip())
    env = ctx.get("env") if is_record(ctx.get("env")) else {}
    env_managed_api_key = (
        PROVIDER_ENV_VAR if normalize_optional_string(env.get(PROVIDER_ENV_VAR)) else None
    )
    for profile_id in _list_profiles_for_provider(auth_store, PROVIDER_ID):
        profiles = auth_store.get("profiles")
        credential = profiles.get(profile_id) if is_record(profiles) else None
        provider = build_cloudflare_ai_gateway_catalog_provider(
            {
                "credential": credential,
                "envApiKey": env_managed_api_key,
            }
        )
        if provider:
            return {"provider": provider}
    return None


def _register(api: OpenClawPluginApi) -> None:
    api.register_provider(
        {
            "id": PROVIDER_ID,
            "label": "Cloudflare AI Gateway",
            "docsPath": "/providers/cloudflare-ai-gateway",
            "envVars": [PROVIDER_ENV_VAR],
            "auth": [
                create_provider_api_key_auth_method(
                    {
                        "providerId": PROVIDER_ID,
                        "methodId": "api-key",
                        "label": "Cloudflare AI Gateway",
                        "hint": "Account ID + Gateway ID + API key",
                        "optionKey": "cloudflareAiGatewayApiKey",
                        "flagName": "--cloudflare-ai-gateway-api-key",
                        "envVar": PROVIDER_ENV_VAR,
                        "promptMessage": "Enter Cloudflare AI Gateway API key",
                        "defaultModel": CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF,
                        "wizard": {
                            "choiceId": "cloudflare-ai-gateway-api-key",
                            "choiceLabel": "Cloudflare AI Gateway",
                            "choiceHint": "Account ID + Gateway ID + API key",
                            "groupId": "cloudflare-ai-gateway",
                            "groupLabel": "Cloudflare AI Gateway",
                            "groupHint": "Account ID + Gateway ID + API key",
                        },
                    }
                ),
            ],
            "catalog": {
                "order": "late",
                "run": _catalog_run,
            },
            "classifyFailoverReason": lambda ctx: (
                "rate_limit"
                if _FAILOVER_PATTERN.search(str(ctx.get("errorMessage", "")))
                else None
            ),
            "wrapStreamFn": wrap_cloudflare_ai_gateway_provider_stream,
            "applyConfig": apply_cloudflare_ai_gateway_config,
            "buildConfigPatch": build_cloudflare_ai_gateway_config_patch,
        }
    )


default = define_plugin_entry(
    id=PROVIDER_ID,
    name="Cloudflare AI Gateway Provider",
    description="Bundled Cloudflare AI Gateway provider plugin",
    register=_register,
)
