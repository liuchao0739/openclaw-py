import os
import re
from typing import Any, Optional, List, TypedDict

from .models import is_deepseek_v4_model_id, is_deepseek_v4_model_ref
from .onboard import apply_deepseek_config, DEEPSEEK_DEFAULT_MODEL_REF
from .provider_catalog import build_deepseek_provider
from .stream import create_deepseek_v4_thinking_wrapper, wrap_deepseek_provider_stream
from .thinking_policy import resolve_deepseek_v4_thinking_profile

PROVIDER_ID = "deepseek"

_CONTEXT_OVERFLOW_RE = re.compile(
    r"\bdeepseek\b.*(?:input.*too long|context.*exceed)", re.IGNORECASE
)


def _matches_context_overflow_error(params: dict) -> bool:
    error_message = params.get("errorMessage", "")
    if not isinstance(error_message, str):
        return False
    return bool(_CONTEXT_OVERFLOW_RE.search(error_message))


def _augment_model_catalog(params: dict) -> List[dict]:
    config = params.get("config", {})
    provider_id = params.get("providerId", PROVIDER_ID)
    if not isinstance(config, dict):
        return []
    configured = config.get("providers", {}).get(provider_id, {}).get("models", [])
    if isinstance(configured, list):
        return list(configured)
    return []


def _resolve_usage_auth(ctx: dict) -> Optional[dict]:
    env = ctx.get("env", {}) or {}
    env_direct = env.get("DEEPSEEK_API_KEY") if isinstance(env, dict) else None
    if not env_direct:
        env_direct = os.environ.get("DEEPSEEK_API_KEY")
    api_key = ctx.get("resolveApiKeyFromConfigAndStore", lambda **kw: env_direct)(
        envDirect=[env_direct]
    ) if env_direct else None
    token = api_key or env_direct
    if token:
        return {"token": token}
    return None


async def _fetch_usage_snapshot(ctx: dict) -> Any:
    token = ctx.get("token")
    timeout_ms = ctx.get("timeoutMs")
    fetch_fn = ctx.get("fetchFn")
    if not token or not fetch_fn:
        return None
    return await fetch_fn(token, timeout_ms)


OPENAI_COMPATIBLE_REPLAY_HOOKS: dict = {
    "replayModelRequest": None,
    "replayStreamChunk": None,
    "replayComplete": None,
}


class PluginEntry(TypedDict, total=False):
    id: str
    name: str
    description: str
    provider: dict


plugin_entry: PluginEntry = {
    "id": PROVIDER_ID,
    "name": "DeepSeek Provider",
    "description": "Bundled DeepSeek provider plugin",
    "provider": {
        "label": "DeepSeek",
        "docsPath": "/providers/deepseek",
        "auth": [
            {
                "methodId": "api-key",
                "label": "DeepSeek API key",
                "hint": "API key",
                "optionKey": "deepseekApiKey",
                "flagName": "--deepseek-api-key",
                "envVar": "DEEPSEEK_API_KEY",
                "promptMessage": "Enter DeepSeek API key",
                "defaultModel": DEEPSEEK_DEFAULT_MODEL_REF,
                "applyConfig": lambda cfg: apply_deepseek_config(cfg),
                "wizard": {
                    "choiceId": "deepseek-api-key",
                    "choiceLabel": "DeepSeek API key",
                    "groupId": "deepseek",
                    "groupLabel": "DeepSeek",
                    "groupHint": "API key",
                },
            },
        ],
        "catalog": {
            "buildProvider": build_deepseek_provider,
        },
        "augmentModelCatalog": _augment_model_catalog,
        "matchesContextOverflowError": _matches_context_overflow_error,
        **OPENAI_COMPATIBLE_REPLAY_HOOKS,
        "dropReasoningFromHistory": False,
        "wrapStreamFn": lambda ctx: create_deepseek_v4_thinking_wrapper(
            ctx.get("streamFn"), ctx.get("thinkingLevel")
        ),
        "resolveThinkingProfile": lambda params: resolve_deepseek_v4_thinking_profile(
            params.get("modelId", "")
        ),
        "isModernModelRef": lambda params: bool(
            resolve_deepseek_v4_thinking_profile(params.get("modelId", ""))
        ),
        "resolveUsageAuth": _resolve_usage_auth,
        "fetchUsageSnapshot": _fetch_usage_snapshot,
    },
}
