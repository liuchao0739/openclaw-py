from typing import Dict, List, Optional, Set

from .model_metadata import resolveCopilotModelCompat, resolveCopilotTransportApi, resolveStaticCopilotModelOverride

PROVIDER_ID = "github-copilot"
CODEX_FORWARD_COMPAT_TARGET_IDS = {"gpt-5.4", "gpt-5.3-codex"}
CODEX_TEMPLATE_MODEL_IDS = ["gpt-5.3-codex"]

DEFAULT_CONTEXT_WINDOW = 128_000
DEFAULT_MAX_TOKENS = 8192


def isCopilotCodexModelId(modelId: str) -> bool:
    return "codex" in modelId.lower()


def resolveCopilotForwardCompatModel(ctx: Dict) -> Optional[Dict]:
    trimmedModelId = ctx.get("modelId", "").strip()
    if not trimmedModelId:
        return None

    lowerModelId = trimmedModelId.lower()
    existing = ctx.get("modelRegistry", {}).get(lowerModelId)
    if existing:
        return None

    if lowerModelId in CODEX_FORWARD_COMPAT_TARGET_IDS:
        for templateId in CODEX_TEMPLATE_MODEL_IDS:
            template = ctx.get("modelRegistry", {}).get(templateId)
            if template:
                return {
                    **template,
                    "id": trimmedModelId,
                    "name": trimmedModelId,
                }

    staticOverride = resolveStaticCopilotModelOverride(lowerModelId)
    if staticOverride:
        compat = staticOverride.get("compat") or resolveCopilotModelCompat(trimmedModelId)
        return {
            "id": trimmedModelId,
            "name": staticOverride.get("name") or trimmedModelId,
            "provider": PROVIDER_ID,
            "api": staticOverride.get("api") or resolveCopilotTransportApi(trimmedModelId),
            "reasoning": staticOverride.get("reasoning") or False,
            "input": staticOverride.get("input") or ["text", "image"],
            "cost": staticOverride.get("cost") or {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            "contextWindow": staticOverride.get("contextWindow") or DEFAULT_CONTEXT_WINDOW,
            "maxTokens": staticOverride.get("maxTokens") or DEFAULT_MAX_TOKENS,
            **({"thinkingLevelMap": staticOverride.get("thinkingLevelMap")} if staticOverride.get("thinkingLevelMap") else {}),
            **({"compat": compat} if compat else {}),
        }

    reasoning = isCopilotCodexModelId(lowerModelId)
    compat = resolveCopilotModelCompat(trimmedModelId)
    return {
        "id": trimmedModelId,
        "name": trimmedModelId,
        "provider": PROVIDER_ID,
        "api": resolveCopilotTransportApi(trimmedModelId),
        "reasoning": reasoning,
        "input": ["text", "image"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": DEFAULT_CONTEXT_WINDOW,
        "maxTokens": DEFAULT_MAX_TOKENS,
        **({"compat": compat} if compat else {}),
    }


def resolveCopilotApiForVendor(vendor: Optional[str], modelId: str) -> str:
    if vendor and vendor.lower() == "anthropic":
        return "anthropic-messages"
    return resolveCopilotTransportApi(modelId)


def mergeCopilotCompat(base: Optional[Dict], reasoningEfforts: Optional[List[str]]) -> Optional[Dict]:
    if not reasoningEfforts:
        return base
    supported = list(set([e.lower() for e in reasoningEfforts if e]))
    if not supported:
        return base
    return {
        **(base or {}),
        "supportedReasoningEfforts": supported,
    }


def resolveCopilotThinkingLevelMap(api: str, modelId: str, compat: Optional[Dict]) -> Optional[Dict]:
    if api != "anthropic-messages" or not compat or not isinstance(compat.get("supportedReasoningEfforts"), list):
        return None
    return {
        "xhigh": "xhigh" if "xhigh" in compat["supportedReasoningEfforts"] else None,
        "max": "max" if "max" in compat["supportedReasoningEfforts"] else None,
    }


def mapCopilotApiModelToDefinition(entry: Dict) -> Optional[Dict]:
    entry_id = entry.get("id", "").strip()
    if not entry_id:
        return None
    if entry.get("object") and entry.get("object") != "model":
        return None
    if entry.get("capabilities", {}).get("type") and entry.get("capabilities", {}).get("type") != "chat":
        return None
    if entry_id.startswith("accounts/"):
        return None

    limits = entry.get("capabilities", {}).get("limits", {})
    supports = entry.get("capabilities", {}).get("supports", {})
    reasoning = isinstance(supports.get("reasoning_effort"), list) and len(supports.get("reasoning_effort")) > 0
    supportsVision = supports.get("vision") is True
    input_types = ["text", "image"] if supportsVision else ["text"]

    contextWindow = limits.get("max_context_window_tokens") or DEFAULT_CONTEXT_WINDOW
    maxTokens = limits.get("max_output_tokens") or DEFAULT_MAX_TOKENS
    compat = mergeCopilotCompat(resolveCopilotModelCompat(entry_id), supports.get("reasoning_effort"))
    api = resolveCopilotApiForVendor(entry.get("vendor"), entry_id)
    thinkingLevelMap = resolveCopilotThinkingLevelMap(api, entry_id, compat)

    definition = {
        "id": entry_id,
        "name": entry.get("name", "").strip() or entry_id,
        "api": api,
        "reasoning": reasoning,
        "input": input_types,
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": contextWindow,
        "maxTokens": maxTokens,
        **({"thinkingLevelMap": thinkingLevelMap} if thinkingLevelMap else {}),
        **({"compat": compat} if compat else {}),
    }
    return definition


async def fetchCopilotModelCatalog(params: Dict) -> List[Dict]:
    import requests

    copilotApiToken = params.get("copilotApiToken")
    baseUrl = params.get("baseUrl")
    if not copilotApiToken or not baseUrl:
        raise ValueError("copilotApiToken and baseUrl required")

    trimmedBase = baseUrl.rstrip("/")
    url = f"{trimmedBase}/models"

    response = requests.get(url, headers={
        "Accept": "application/json",
        "Authorization": f"Bearer {copilotApiToken}",
    })
    if not response.ok:
        raise ValueError(f"Copilot /models fetch failed: HTTP {response.status}")

    data = response.json()
    entries = data.get("data", [])

    seen = set()
    out = []
    for rawEntry in entries:
        if not isinstance(rawEntry, dict):
            continue
        definition = mapCopilotApiModelToDefinition(rawEntry)
        if not definition:
            continue
        if definition["id"] in seen:
            continue
        seen.add(definition["id"])
        out.append(definition)
    return out

__all__ = [
    "PROVIDER_ID",
    "resolveCopilotForwardCompatModel",
    "fetchCopilotModelCatalog",
]