from typing import List

CODEX_PROVIDER_ID = "codex"
CODEX_BASE_URL = "https://chatgpt.com/backend-api"
CODEX_APP_SERVER_AUTH_MARKER = "codex-app-server"

DEFAULT_CONTEXT_WINDOW = 272_000
DEFAULT_MAX_TOKENS = 128_000

FALLBACK_CODEX_MODELS = [
    {
        "id": "gpt-5.5",
        "model": "gpt-5.5",
        "displayName": "gpt-5.5",
        "description": "Latest frontier agentic coding model.",
        "isDefault": True,
        "inputModalities": ["text", "image"],
        "supportedReasoningEfforts": ["low", "medium", "high", "xhigh"],
    },
    {
        "id": "gpt-5.4-mini",
        "model": "gpt-5.4-mini",
        "displayName": "GPT-5.4-Mini",
        "description": "Smaller frontier agentic coding model.",
        "inputModalities": ["text", "image"],
        "supportedReasoningEfforts": ["low", "medium", "high", "xhigh"],
    },
]


def _should_default_to_reasoning_model(model_id: str) -> bool:
    lower = model_id.lower()
    return (
        lower.startswith("gpt-5")
        or lower.startswith("o1")
        or lower.startswith("o3")
        or lower.startswith("o4")
    )


def build_codex_model_definition(model: dict) -> dict:
    model_id = (model.get("id") or "").strip() or (model.get("model") or "").strip()
    display_name = (model.get("displayName") or "").strip() or model_id
    input_modalities = model.get("inputModalities") or []
    supported_reasoning_efforts = model.get("supportedReasoningEfforts") or []
    return {
        "id": model_id,
        "name": display_name,
        "api": "openai-chatgpt-responses",
        "reasoning": len(supported_reasoning_efforts) > 0 or _should_default_to_reasoning_model(model_id),
        "input": ["text", "image"] if "image" in input_modalities else ["text"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": DEFAULT_CONTEXT_WINDOW,
        "maxTokens": DEFAULT_MAX_TOKENS,
        "compat": {
            "supportsReasoningEffort": len(supported_reasoning_efforts) > 0,
            "supportsUsageInStreaming": True,
        },
    }


def build_codex_provider_config(models: List[dict]) -> dict:
    return {
        "baseUrl": CODEX_BASE_URL,
        "apiKey": CODEX_APP_SERVER_AUTH_MARKER,
        "auth": "token",
        "api": "openai-chatgpt-responses",
        "models": [build_codex_model_definition(model) for model in models],
    }
