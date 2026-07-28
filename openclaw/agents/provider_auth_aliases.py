from __future__ import annotations

from typing import Any


def resolve_auth_provider_aliases(provider: str) -> list[str]:
    aliases: dict[str, list[str]] = {
        "openai": ["openai", "gpt", "chatgpt"],
        "anthropic": ["anthropic", "claude", "claude-ai"],
        "google": ["google", "gemini", "google-cloud"],
        "deepseek": ["deepseek", "deepseek-ai"],
        "codex": ["codex", "openclaw-codex"],
        "chutes": ["chutes", "chutes-ai"],
        "xai": ["xai"],
        "moonshot": ["moonshot", "moonshot-ai"],
        "minimax": ["minimax", "minimaxi"],
    }
    return aliases.get(provider.lower(), [provider])


def resolve_provider_id_for_auth(provider: str) -> str:
    aliases = resolve_auth_provider_aliases(provider)
    return aliases[0] if aliases else provider.lower()


def normalize_provider_id(provider: str) -> str:
    return resolve_provider_id_for_auth(provider)
