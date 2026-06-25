"""Auth guidance for session authentication flows.

Provides structured auth guidance messages for model providers that require
API keys or OAuth.
"""

from __future__ import annotations

from typing import TypedDict


class AuthGuidance(TypedDict, total=False):
    provider: str
    message: str
    url: str | None
    envVar: str | None


_PROVIDER_AUTH_GUIDANCE: dict[str, AuthGuidance] = {
    "openai": AuthGuidance(
        provider="openai",
        message="Set the OPENAI_API_KEY environment variable or run /login.",
        envVar="OPENAI_API_KEY",
        url="https://platform.openai.com/api-keys",
    ),
    "anthropic": AuthGuidance(
        provider="anthropic",
        message="Set the ANTHROPIC_API_KEY environment variable or run /login.",
        envVar="ANTHROPIC_API_KEY",
        url="https://console.anthropic.com/settings/keys",
    ),
    "google": AuthGuidance(
        provider="google",
        message="Set the GOOGLE_API_KEY environment variable.",
        envVar="GOOGLE_API_KEY",
        url="https://aistudio.google.com/apikey",
    ),
}


def get_auth_guidance(provider: str | None) -> AuthGuidance | None:
    """Get auth guidance for a provider."""
    if not provider:
        return None
    return _PROVIDER_AUTH_GUIDANCE.get(provider.lower())


def register_auth_guidance(provider: str, guidance: AuthGuidance) -> None:
    """Register or override auth guidance for a provider."""
    _PROVIDER_AUTH_GUIDANCE[provider.lower()] = guidance
