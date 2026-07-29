import os
import re
from typing import Any, Optional, TypedDict

from .._sdk import normalize_secret_input
from .models import CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF
from .onboard import (
    apply_cloudflare_ai_gateway_config,
    build_cloudflare_ai_gateway_config_patch,
)
from .catalog_provider import build_cloudflare_ai_gateway_catalog_provider
from .stream_wrappers import wrap_cloudflare_ai_gateway_provider_stream

PROVIDER_ID = "cloudflare-ai-gateway"
PROVIDER_ENV_VAR = "CLOUDFLARE_AI_GATEWAY_API_KEY"
PROFILE_ID = "cloudflare-ai-gateway:default"

_FAILOVER_RE = re.compile(
    r"\bworkers?_ai\b.*\b(?:rate|limit|quota)\b", re.IGNORECASE
)


def _read_required_text_input(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _trim_to_undefined(value: Any) -> Optional[str]:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return None


def _resolve_gateway_metadata_interactive(ctx: dict) -> dict:
    account_id = _trim_to_undefined(ctx.get("accountId")) or ""
    gateway_id = _trim_to_undefined(ctx.get("gatewayId")) or ""
    if not account_id:
        value = ctx["prompter"].text(
            message="Enter Cloudflare Account ID",
            validate=lambda val: None if _read_required_text_input(val) else "Account ID is required",
        )
        account_id = _read_required_text_input(value)
    if not gateway_id:
        value = ctx["prompter"].text(
            message="Enter Cloudflare AI Gateway ID",
            validate=lambda val: None if _read_required_text_input(val) else "Gateway ID is required",
        )
        gateway_id = _read_required_text_input(value)
    return {"accountId": account_id, "gatewayId": gateway_id}


def _classify_failover_reason(params: dict) -> Optional[str]:
    error_message = params.get("errorMessage", "")
    if not isinstance(error_message, str):
        return None
    if _FAILOVER_RE.search(error_message):
        return "rate_limit"
    return None


class PluginEntry(TypedDict, total=False):
    id: str
    name: str
    description: str
    provider: dict


plugin_entry: PluginEntry = {
    "id": PROVIDER_ID,
    "name": "Cloudflare AI Gateway Provider",
    "description": "Bundled Cloudflare AI Gateway provider plugin",
    "provider": {
        "label": "Cloudflare AI Gateway",
        "docsPath": "/providers/cloudflare-ai-gateway",
        "envVars": [PROVIDER_ENV_VAR],
        "auth": [
            {
                "id": "api-key",
                "label": "Cloudflare AI Gateway",
                "hint": "Account ID + Gateway ID + API key",
                "kind": "api_key",
                "wizard": {
                    "choiceId": "cloudflare-ai-gateway-api-key",
                    "choiceLabel": "Cloudflare AI Gateway",
                    "choiceHint": "Account ID + Gateway ID + API key",
                    "groupId": "cloudflare-ai-gateway",
                    "groupLabel": "Cloudflare AI Gateway",
                    "groupHint": "Account ID + Gateway ID + API key",
                },
                "run": lambda ctx: {
                    "profiles": [
                        {
                            "profileId": PROFILE_ID,
                            "credential": {
                                "type": "api_key",
                                "provider": PROVIDER_ID,
                                "key": normalize_secret_input(
                                    ctx.get("opts", {}).get("cloudflareAiGatewayApiKey")
                                ),
                                "metadata": _resolve_gateway_metadata_interactive({
                                    "accountId": normalize_secret_input(
                                        ctx.get("opts", {}).get("cloudflareAiGatewayAccountId")
                                    ),
                                    "gatewayId": normalize_secret_input(
                                        ctx.get("opts", {}).get("cloudflareAiGatewayGatewayId")
                                    ),
                                    "prompter": ctx.get("prompter"),
                                }),
                            },
                        },
                    ],
                    "configPatch": build_cloudflare_ai_gateway_config_patch(
                        _resolve_gateway_metadata_interactive({
                            "accountId": normalize_secret_input(
                                ctx.get("opts", {}).get("cloudflareAiGatewayAccountId")
                            ),
                            "gatewayId": normalize_secret_input(
                                ctx.get("opts", {}).get("cloudflareAiGatewayGatewayId")
                            ),
                            "prompter": ctx.get("prompter"),
                        })
                    ),
                    "defaultModel": CLOUDFLARE_AI_GATEWAY_DEFAULT_MODEL_REF,
                },
                "runNonInteractive": lambda ctx: apply_cloudflare_ai_gateway_config(
                    ctx.get("config", {}),
                    {
                        "accountId": normalize_secret_input(
                            ctx.get("opts", {}).get("cloudflareAiGatewayAccountId")
                        ),
                        "gatewayId": normalize_secret_input(
                            ctx.get("opts", {}).get("cloudflareAiGatewayGatewayId")
                        ),
                    },
                ),
            },
        ],
        "catalog": {
            "order": "late",
            "run": lambda ctx: build_cloudflare_ai_gateway_catalog_provider({
                "credential": ctx.get("credential"),
                "envApiKey": os.environ.get(PROVIDER_ENV_VAR),
            }),
        },
        "classifyFailoverReason": _classify_failover_reason,
        "wrapStreamFn": wrap_cloudflare_ai_gateway_provider_stream,
    },
}
