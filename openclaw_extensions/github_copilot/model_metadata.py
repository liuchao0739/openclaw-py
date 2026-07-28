from typing import Dict, List, Optional, Set


COPILOT_CHAT_COMPLETIONS_COMPAT = {
    "supportsStore": False,
    "supportsDeveloperRole": False,
    "supportsUsageInStreaming": False,
    "maxTokensField": "max_tokens",
}
COPILOT_XHIGH_MODEL_IDS = {"gpt-5.4", "gpt-5.3-codex"}

STATIC_MODEL_OVERRIDES = {
    "claude-opus-4.6-1m": {
        "name": "Claude Opus 4.6 (1M context)",
        "api": "anthropic-messages",
        "reasoning": True,
        "contextWindow": 1_000_000,
        "maxTokens": 64_000,
        "thinkingLevelMap": {"xhigh": None, "max": None},
        "compat": {"supportedReasoningEfforts": ["low", "medium", "high"]},
    },
    "claude-opus-4.7-1m-internal": {
        "name": "Claude Opus 4.7 (1M context)",
        "api": "anthropic-messages",
        "reasoning": True,
        "contextWindow": 1_000_000,
        "maxTokens": 64_000,
        "thinkingLevelMap": {"xhigh": "xhigh", "max": None},
        "compat": {"supportedReasoningEfforts": ["low", "medium", "high", "xhigh"]},
    },
    "gpt-5.5": {
        "name": "GPT-5.5",
        "reasoning": True,
        "contextWindow": 400_000,
        "maxTokens": 128_000,
    },
}


def normalize_optional_lowercase_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return value.strip().lower()


def isCopilotGeminiModelId(modelId: str) -> bool:
    return "gemini" in normalize_optional_lowercase_string(modelId)


def isCopilotClaude45ModelId(modelId: str) -> bool:
    normalized = normalize_optional_lowercase_string(modelId) or ""
    return normalized.startswith("claude-haiku-4.5") or normalized.startswith("claude-opus-4.5") or normalized.startswith("claude-sonnet-4.5")


def resolveCopilotTransportApi(modelId: str) -> str:
    normalized = normalize_optional_lowercase_string(modelId) or ""
    if "claude" in normalized:
        return "anthropic-messages"
    if isCopilotGeminiModelId(normalized):
        return "openai-completions"
    return "openai-responses"


def resolveCopilotModelCompat(modelId: str) -> Optional[Dict]:
    normalized = normalize_optional_lowercase_string(modelId) or ""
    if isCopilotGeminiModelId(normalized):
        return COPILOT_CHAT_COMPLETIONS_COMPAT.copy()
    if isCopilotClaude45ModelId(normalized):
        return {"supportsEagerToolInputStreaming": False}
    return None


def compatSupportsEffort(compat: Optional[Dict], effort: str) -> bool:
    efforts = compat.get("supportedReasoningEfforts") if compat else None
    return isinstance(efforts, list) and normalize_optional_lowercase_string(effort) in [normalize_optional_lowercase_string(e) for e in efforts]


def resolveCopilotExtendedThinkingLevels(modelId: str, compat: Optional[Dict] = None) -> List[str]:
    normalizedModelId = normalize_optional_lowercase_string(modelId) or ""
    staticCompat = resolveStaticCopilotModelOverride(normalizedModelId).get("compat") if resolveStaticCopilotModelOverride(normalizedModelId) else None
    isClaudeModel = "claude" in normalizedModelId
    supportsAdaptiveClaudeEffort = not isClaudeModel
    levels = []
    if (
        supportsAdaptiveClaudeEffort
        and (normalizedModelId in COPILOT_XHIGH_MODEL_IDS or compatSupportsEffort(compat, "xhigh") or compatSupportsEffort(staticCompat, "xhigh"))
    ):
        levels.append("xhigh")
    if (
        isClaudeModel
        and supportsAdaptiveClaudeEffort
        and (compatSupportsEffort(compat, "max") or compatSupportsEffort(staticCompat, "max"))
    ):
        levels.append("max")
    return levels


def resolveStaticCopilotModelOverride(modelId: str) -> Dict:
    return STATIC_MODEL_OVERRIDES.get(normalize_optional_lowercase_string(modelId) or "", {})

__all__ = [
    "COPILOT_CHAT_COMPLETIONS_COMPAT",
    "COPILOT_XHIGH_MODEL_IDS",
    "STATIC_MODEL_OVERRIDES",
    "resolveCopilotTransportApi",
    "resolveCopilotModelCompat",
    "resolveCopilotExtendedThinkingLevels",
    "resolveStaticCopilotModelOverride",
]