"""Shared Codex web search provider contract fields."""

from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.provider_web_search_contract import (
    create_web_search_provider_contract_fields,
)


def create_codex_web_search_provider_base() -> dict[str, Any]:
    return {
        "id": "codex",
        "label": "Codex Hosted Search",
        "hint": "Grounded answers through your Codex app-server account",
        "onboardingScopes": ["text-inference"],
        "requiresCredential": False,
        "envVars": [],
        "placeholder": "(uses Codex sign-in)",
        "signupUrl": "https://chatgpt.com/codex",
        "docsUrl": "https://docs.openclaw.ai/tools/web",
        "autoDetectOrder": 900,
        "credentialPath": "",
        **create_web_search_provider_contract_fields(
            {
                "credentialPath": "",
                "searchCredential": {"type": "none"},
                "selectionPluginId": "codex",
            }
        ),
        "runSetup": _run_setup,
    }


async def _run_setup(ctx: dict[str, Any]) -> Any:
    prompter = ctx["prompter"]
    await prompter.note(
        (
            "Codex Hosted Search uses the bundled Codex app-server and your Codex/OpenAI sign-in.\n"
            "If needed, sign in with: openclaw models auth login --provider openai\n"
            "Verify the app-server account with /codex status."
        ),
        "Codex Hosted Search",
    )
    return ctx["config"]
