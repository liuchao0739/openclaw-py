from __future__ import annotations

import re
from typing import Any

from openclaw.plugin_sdk.provider_auth import build_copilot_ide_headers, COPILOT_INTEGRATION_ID
from openclaw.plugin_sdk.provider_model_shared import (
    ModelDefinitionConfig,
    normalize_model_compat,
    supports_claude_adaptive_thinking,
)
from openclaw.plugin_sdk.provider_http import read_provider_json_array_field_response
from openclaw.plugin_sdk.string_coerce_runtime import (
    as_positive_safe_integer,
    normalize_optional_lowercase_string,
)

from openclaw_extensions.github_copilot.model_metadata import (
    resolve_copilot_model_compat,
    resolve_copilot_transport_api,
    resolve_static_copilot_model_override,
)

PROVIDER_ID = "github-copilot"

CODEX_FORWARD_COMPAT_TARGET_IDS = {"gpt-5.4", "gpt-5.3-codex"}
CODEX_TEMPLATE_MODEL_IDS = ["gpt-5.3-codex"]

DEFAULT_CONTEXT_WINDOW = 128_000
DEFAULT_MAX_TOKENS = 8192

COPILOT_MODELS_LIST_DEFAULT_TIMEOUT_MS = 10_000
COPILOT_ROUTER_ID_PREFIX = "accounts/"


def _is_copilot_codex_model_id(model_id: str) -> bool:
    return bool(re.search(r"(?:^|[-_.])codex(?:$|[-_.])", model_id))


def resolve_copilot_forward_compat_model(
    ctx: dict[str, Any],
) -> dict[str, Any] | None:
    trimmed_model_id = str(ctx.get("modelId", "")).strip()
    if not trimmed_model_id:
        return None

    lower_model_id = normalize_optional_lowercase_string(trimmed_model_id) or ""
    existing = ctx.get("modelRegistry", {}).find(PROVIDER_ID, lower_model_id) if isinstance(ctx.get("modelRegistry"), dict) else None
    if existing:
        return None

    if lower_model_id in CODEX_FORWARD_COMPAT_TARGET_IDS:
        for template_id in CODEX_TEMPLATE_MODEL_IDS:
            template = None
            if isinstance(ctx.get("modelRegistry"), dict):
                template = ctx["modelRegistry"].find(PROVIDER_ID, template_id)
            if not template:
                continue
            return normalize_model_compat({
                **template,
                "id": trimmed_model_id,
                "name": trimmed_model_id,
            })

    static_override = resolve_static_copilot_model_override(lower_model_id)
    if static_override:
        compat = static_override.get("compat") or resolve_copilot_model_compat(trimmed_model_id)
        return normalize_model_compat({
            "id": trimmed_model_id,
            "name": static_override.get("name", trimmed_model_id),
            "provider": PROVIDER_ID,
            "api": static_override.get("api") or resolve_copilot_transport_api(trimmed_model_id),
            "reasoning": static_override.get("reasoning", False),
            "input": static_override.get("input", ["text", "image"]),
            "cost": static_override.get("cost", {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}),
            "contextWindow": static_override.get("contextWindow", DEFAULT_CONTEXT_WINDOW),
            "maxTokens": static_override.get("maxTokens", DEFAULT_MAX_TOKENS),
            **({"thinkingLevelMap": static_override["thinkingLevelMap"]} if static_override.get("thinkingLevelMap") else {}),
            **({"compat": compat} if compat else {}),
        })

    reasoning = bool(re.match(r"^o[13](\b|$)", lower_model_id)) or _is_copilot_codex_model_id(lower_model_id)
    compat = resolve_copilot_model_compat(trimmed_model_id)
    return normalize_model_compat({
        "id": trimmed_model_id,
        "name": trimmed_model_id,
        "provider": PROVIDER_ID,
        "api": resolve_copilot_transport_api(trimmed_model_id),
        "reasoning": reasoning,
        "input": ["text", "image"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": DEFAULT_CONTEXT_WINDOW,
        "maxTokens": DEFAULT_MAX_TOKENS,
        **({"compat": compat} if compat else {}),
    })


def _resolve_copilot_api_for_vendor(
    vendor: str | None,
    model_id: str,
) -> str:
    if vendor and vendor.lower() == "anthropic":
        return "anthropic-messages"
    return resolve_copilot_transport_api(model_id)


def _merge_copilot_compat(
    base: dict[str, Any] | None,
    reasoning_efforts: list[str] | None,
) -> dict[str, Any] | None:
    if not isinstance(reasoning_efforts, list):
        return base
    supported = list(set(
        filter(None, [normalize_optional_lowercase_string(e) for e in reasoning_efforts])
    ))
    if not supported:
        return base
    result = dict(base) if base else {}
    result["supportedReasoningEfforts"] = supported
    return result


def _resolve_copilot_thinking_level_map(
    api: str,
    model_id: str,
    compat: dict[str, Any] | None,
) -> dict[str, Any] | None:
    efforts = compat.get("supportedReasoningEfforts") if compat else None
    if api != "anthropic-messages" or not isinstance(efforts, list):
        return None
    supports_adaptive = supports_claude_adaptive_thinking({"id": model_id})
    return {
        "xhigh": "xhigh" if supports_adaptive and "xhigh" in efforts else None,
        "max": "max" if supports_adaptive and "max" in efforts else None,
    }


def _map_copilot_api_model_to_definition(
    entry: dict[str, Any],
) -> dict[str, Any] | None:
    entry_id = (entry.get("id") or "").strip()
    if not entry_id:
        return None
    if entry.get("object") and entry.get("object") != "model":
        return None
    caps = entry.get("capabilities")
    if caps and caps.get("type") and caps.get("type") != "chat":
        return None
    if entry_id.startswith(COPILOT_ROUTER_ID_PREFIX):
        return None

    limits = caps.get("limits") if caps else None
    supports = caps.get("supports") if caps else None
    reasoning = False
    if isinstance(supports, dict) and isinstance(supports.get("reasoning_effort"), list):
        reasoning = len(supports["reasoning_effort"]) > 0
    supports_vision = bool(supports.get("vision")) if isinstance(supports, dict) else False
    input_list = ["text", "image"] if supports_vision else ["text"]

    context_window = as_positive_safe_integer(limits.get("max_context_window_tokens")) if limits else None
    if context_window is None:
        context_window = DEFAULT_CONTEXT_WINDOW
    max_tokens = as_positive_safe_integer(limits.get("max_output_tokens")) if limits else None
    if max_tokens is None:
        max_tokens = DEFAULT_MAX_TOKENS

    compat = _merge_copilot_compat(
        resolve_copilot_model_compat(entry_id),
        supports.get("reasoning_effort") if isinstance(supports, dict) else None,
    )
    api = _resolve_copilot_api_for_vendor(entry.get("vendor"), entry_id)
    thinking_level_map = _resolve_copilot_thinking_level_map(api, entry_id, compat)

    definition: dict[str, Any] = {
        "id": entry_id,
        "name": (entry.get("name") or "").strip() or entry_id,
        "api": api,
        "reasoning": reasoning,
        "input": input_list,
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": context_window,
        "maxTokens": max_tokens,
    }
    if thinking_level_map:
        definition["thinkingLevelMap"] = thinking_level_map
    if compat:
        definition["compat"] = compat
    return definition


async def fetch_copilot_model_catalog(
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    fetch_impl = params.get("fetchImpl")
    import urllib.request
    import json

    trimmed_base = params.get("baseUrl", "").rstrip("/")
    if not trimmed_base:
        raise ValueError("fetchCopilotModelCatalog: baseUrl required")
    copilot_api_token = (params.get("copilotApiToken") or "").strip()
    if not copilot_api_token:
        raise ValueError("fetchCopilotModelCatalog: copilotApiToken required")

    url = f"{trimmed_base}/models"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {copilot_api_token}",
    }
    headers.update(build_copilot_ide_headers())
    headers["Copilot-Integration-Id"] = COPILOT_INTEGRATION_ID

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            if res.status != 200:
                raise RuntimeError(f"Copilot /models fetch failed: HTTP {res.status}")
            body = res.read().decode("utf-8")
            data = json.loads(body)
            if isinstance(data, dict) and "data" in data:
                data = data["data"]
            if not isinstance(data, list):
                raise RuntimeError("Copilot /models: malformed JSON response")
            seen = set()
            out = []
            for raw_entry in data:
                if not isinstance(raw_entry, dict):
                    continue
                definition = _map_copilot_api_model_to_definition(raw_entry)
                if not definition:
                    continue
                if definition["id"] in seen:
                    continue
                seen.add(definition["id"])
                out.append(definition)
            return out
    except Exception as e:
        if "HTTP" in str(e):
            raise
        raise RuntimeError(f"Copilot /models fetch failed: {e}")
