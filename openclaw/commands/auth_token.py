"""Auth token barrel — provider setup-token validation helpers."""

from __future__ import annotations

ANTHROPIC_SETUP_TOKEN_PREFIX = "sk-ant-setup"

def validate_anthropic_setup_token(token: str) -> bool:
    """Validate an Anthropic setup token. Deferred to provider-auth-token module."""
    try:
        from openclaw.plugins.provider_auth_token import validate_anthropic_setup_token as _validate

        return _validate(token)
    except Exception:
        return token.startswith(ANTHROPIC_SETUP_TOKEN_PREFIX) if token else False
