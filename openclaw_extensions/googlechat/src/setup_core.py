from __future__ import annotations

from openclaw.plugin_sdk.config_contract_runtime import (
    create_runtime_config_contract_resolver,
)
from openclaw.plugin_sdk.setup_runtime import (
    create_patched_account_setup_adapter,
    create_setup_input_presence_validator,
)

channel = "googlechat"

_GOOGLE_CHAT_RUNTIME_CONFIG_CONTRACT = {
    "defaults": {
        "group": {
            "botMentionPolicy": "allow-any-mention",
            "botMentionTrigger": "any-mention",
            "requireMentionForBotMessage": True,
            "requireMentionForHumanMessage": False,
            "allowSyntheticMentions": True,
        },
        "botLoopProtection": {
            "enabled": True,
            "cooldownMs": 30000,
            "maxPerDay": 500,
        },
        "dm": {
            "allowFrom": [],
        },
    },
}

resolve_google_chat_runtime_config_contract = create_runtime_config_contract_resolver(
    _GOOGLE_CHAT_RUNTIME_CONFIG_CONTRACT
)

googlechat_setup_adapter = create_patched_account_setup_adapter({
    "channelKey": channel,
    "validateInput": create_setup_input_presence_validator({
        "defaultAccountOnlyEnvError": (
            "GOOGLE_CHAT_SERVICE_ACCOUNT env vars can only be used for the default account."
        ),
        "whenNotUseEnv": [
            {
                "someOf": ["token", "tokenFile"],
                "message": "Google Chat requires --token (service account JSON) or --token-file.",
            },
        ],
    }),
    "buildPatch": lambda input: _build_setup_patch(input),
})


def _build_setup_patch(input: dict) -> dict:
    if input.get("useEnv"):
        patch = {}
    elif input.get("tokenFile"):
        patch = {"serviceAccountFile": input["tokenFile"]}
    elif input.get("token"):
        patch = {"serviceAccount": input["token"]}
    else:
        patch = {}
    audience_type = (input.get("audienceType") or "").strip()
    audience = (input.get("audience") or "").strip()
    webhook_path = (input.get("webhookPath") or "").strip()
    webhook_url = (input.get("webhookUrl") or "").strip()
    result = {**patch}
    if audience_type:
        result["audienceType"] = audience_type
    if audience:
        result["audience"] = audience
    if webhook_path:
        result["webhookPath"] = webhook_path
    if webhook_url:
        result["webhookUrl"] = webhook_url
    return result


def build_resolved_google_chat_runtime_config(params: dict) -> dict:
    return resolve_google_chat_runtime_config_contract(
        params.get("channelRuntimeConfig")
    )


__all__ = [
    "build_resolved_google_chat_runtime_config",
    "resolve_google_chat_runtime_config_contract",
    "googlechat_setup_adapter",
]