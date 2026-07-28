from __future__ import annotations

from typing import Any


def build_provider_auth_recovery_hint(
    provider: str,
    config: dict[str, Any] | None = None,
    workspace_dir: str | None = None,
    env: dict[str, Any] | None = None,
) -> str | None:
    hints: dict[str, str] = {
        "openai": "Try running `/login` to re-authenticate with your OpenAI account.",
        "anthropic": "Try running `/login` to re-authenticate with your Anthropic account.",
        "google": "Try running `/login` to re-authenticate with your Google account.",
        "deepseek": "Check your API key validity in the config.",
        "codex": "Try running `/login` to re-authenticate with your Codex account.",
    }
    return hints.get(provider.lower())
