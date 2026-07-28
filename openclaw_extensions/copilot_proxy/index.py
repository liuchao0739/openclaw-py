from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry

DEFAULT_BASE_URL = "http://localhost:3000/v1"
DEFAULT_API_KEY = "n/a"
DEFAULT_CONTEXT_WINDOW = 128_000
DEFAULT_MAX_TOKENS = 8192
DEFAULT_MODEL_IDS = [
    "gpt-5.2",
    "gpt-5.2-codex",
    "gpt-5.1",
    "gpt-5.1-codex",
    "gpt-5.1-codex-max",
    "gpt-5-mini",
    "claude-opus-4.6",
    "claude-opus-4.7",
    "claude-sonnet-4.6",
    "gemini-3-pro",
    "gemini-3-flash",
]


def normalize_base_url(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return DEFAULT_BASE_URL
    normalized = trimmed
    while normalized.endswith("/"):
        normalized = normalized[:-1]
    if not normalized.endswith("/v1"):
        normalized = f"{normalized}/v1"
    return normalized


def validate_base_url(value: str) -> str | None:
    normalized = normalize_base_url(value)
    try:
        from urllib.parse import urlparse
        urlparse(normalized)
        return None
    except Exception:
        return "Enter a valid URL"


def parse_model_ids(input_str: str) -> list[str]:
    import re
    parts = re.split(r"[\n,]", input_str)
    parsed = [p.strip() for p in parts if p.strip()]
    seen = set()
    result = []
    for item in parsed:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def build_model_definition(model_id: str) -> dict[str, Any]:
    return {
        "id": model_id,
        "name": model_id,
        "api": "openai-completions",
        "reasoning": False,
        "input": ["text", "image"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": DEFAULT_CONTEXT_WINDOW,
        "maxTokens": DEFAULT_MAX_TOKENS,
    }


def _register(api: OpenClawPluginApi) -> None:
    async def run_local_auth(ctx: dict[str, Any]) -> dict[str, Any]:
        base_url_input = await ctx["prompter"]["text"]({
            "message": "Copilot Proxy base URL",
            "initialValue": DEFAULT_BASE_URL,
            "validate": validate_base_url,
        })

        model_input = await ctx["prompter"]["text"]({
            "message": "Model IDs (comma-separated)",
            "initialValue": ", ".join(DEFAULT_MODEL_IDS),
            "validate": lambda v: None if parse_model_ids(v) else "Enter at least one model id",
        })

        base_url = normalize_base_url(base_url_input)
        model_ids = parse_model_ids(model_input)
        default_model_id = model_ids[0] if model_ids else DEFAULT_MODEL_IDS[0]
        default_model_ref = f"copilot-proxy/{default_model_id}"

        return {
            "profiles": [
                {
                    "profileId": "copilot-proxy:local",
                    "credential": {
                        "type": "token",
                        "provider": "copilot-proxy",
                        "token": DEFAULT_API_KEY,
                    },
                },
            ],
            "configPatch": {
                "models": {
                    "providers": {
                        "copilot-proxy": {
                            "baseUrl": base_url,
                            "apiKey": DEFAULT_API_KEY,
                            "api": "openai-completions",
                            "authHeader": False,
                            "models": [build_model_definition(mid) for mid in model_ids],
                        },
                    },
                },
                "agents": {
                    "defaults": {
                        "models": {
                            f"copilot-proxy/{mid}": {} for mid in model_ids
                        },
                    },
                },
            },
            "defaultModel": default_model_ref,
            "notes": [
                "Start the Copilot Proxy VS Code extension before using these models.",
                "Copilot Proxy serves /v1/chat/completions; base URL must include /v1.",
                "Model availability depends on your Copilot plan; edit models.providers.copilot-proxy if needed.",
            ],
        }

    api.register_provider(
        {
            "id": "copilot-proxy",
            "label": "Copilot Proxy",
            "docsPath": "/providers/models",
            "auth": [
                {
                    "id": "local",
                    "label": "Local proxy",
                    "hint": "Configure base URL + models for the Copilot Proxy server",
                    "kind": "custom",
                    "run": run_local_auth,
                },
            ],
            "wizard": {
                "setup": {
                    "choiceId": "copilot-proxy",
                    "choiceLabel": "Copilot Proxy",
                    "choiceHint": "Configure base URL + model ids",
                    "methodId": "local",
                },
            },
        }
    )


default = define_plugin_entry(
    id="copilot-proxy",
    name="Copilot Proxy",
    description="Local Copilot Proxy (VS Code LM) provider plugin",
    register=_register,
)
