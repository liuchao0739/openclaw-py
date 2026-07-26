"""Copilot Proxy plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from openclaw.packages.normalization_core import normalize_optional_string
from openclaw.plugins.contracts.shared import unique_strings
from openclaw_extensions.copilot_proxy.runtime_api import OpenClawPluginApi, define_plugin_entry

DEFAULT_BASE_URL = "http://localhost:3000/v1"
DEFAULT_API_KEY = "n/a"
DEFAULT_CONTEXT_WINDOW = 128_000
DEFAULT_MAX_TOKENS = 8192
DEFAULT_MODEL_IDS = (
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
)


def _normalize_string_entries(values: list[Any] | None) -> list[str]:
    return [
        entry
        for entry in (normalize_optional_string(str(value)) for value in (values or []))
        if entry
    ]


def _normalize_base_url(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return DEFAULT_BASE_URL
    normalized = trimmed
    while normalized.endswith("/"):
        normalized = normalized[:-1]
    if not normalized.endswith("/v1"):
        normalized = f"{normalized}/v1"
    return normalized


def _validate_base_url(value: str) -> str | None:
    normalized = _normalize_base_url(value)
    parsed = urlparse(normalized)
    return None if parsed.scheme and parsed.netloc else "Enter a valid URL"


def _parse_model_ids(input_value: str) -> list[str]:
    parsed = _normalize_string_entries(re.split(r"[\n,]", input_value))
    return unique_strings(parsed)


def _build_model_definition(model_id: str) -> dict[str, Any]:
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


async def _run_local_auth(ctx: dict[str, Any]) -> dict[str, Any]:
    prompter = ctx["prompter"]

    base_url_input = await prompter.text(
        {
            "message": "Copilot Proxy base URL",
            "initialValue": DEFAULT_BASE_URL,
            "validate": _validate_base_url,
        }
    )

    model_input = await prompter.text(
        {
            "message": "Model IDs (comma-separated)",
            "initialValue": ", ".join(DEFAULT_MODEL_IDS),
            "validate": lambda value: (
                None if _parse_model_ids(value) else "Enter at least one model id"
            ),
        }
    )

    base_url = _normalize_base_url(base_url_input)
    model_ids = _parse_model_ids(model_input)
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
                        "models": [_build_model_definition(model_id) for model_id in model_ids],
                    },
                },
            },
            "agents": {
                "defaults": {
                    "models": {f"copilot-proxy/{model_id}": {} for model_id in model_ids},
                },
            },
        },
        "defaultModel": default_model_ref,
        "notes": [
            "Start the Copilot Proxy VS Code extension before using these models.",
            "Copilot Proxy serves /v1/chat/completions; base URL must include /v1.",
            (
                "Model availability depends on your Copilot plan; "
                "edit models.providers.copilot-proxy if needed."
            ),
        ],
    }


def _register(api: OpenClawPluginApi) -> None:
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
                    "run": _run_local_auth,
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
