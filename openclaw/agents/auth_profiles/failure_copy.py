from __future__ import annotations

from typing import Any

from openclaw.agents.embedded_agent_helpers.types import FailoverReason


def _describe_reason(
    reason: FailoverReason,
    provider: str,
    all_in_cooldown: bool,
) -> str | None:
    if all_in_cooldown:
        if reason in ("auth", "session_expired"):
            return f"Couldn't sign in to {provider}. Your saved login looks expired or no longer works."
        if reason == "auth_permanent":
            return f"{provider} isn't accepting your saved login anymore."
        if reason == "billing":
            return f"{provider} rejected the request — looks like a billing issue on the account."
        if reason == "rate_limit":
            return f"{provider} is asking us to slow down. Please wait a moment before trying again."
        if reason == "overloaded":
            return f"{provider} is overloaded right now. Please wait a moment before trying again."
        if reason == "timeout":
            return f"{provider} hasn't been responding. Please wait a moment before trying again."
        if reason == "model_not_found":
            return f"{provider} can't find the model you're using right now."
        if reason == "server_error":
            return f"{provider} is having issues right now. Please wait a moment before trying again."
        return f"Couldn't reach {provider} with any of your saved logins right now."

    if reason in ("auth", "session_expired"):
        return f"Couldn't sign in to {provider}. Your saved login looks expired or no longer works."
    if reason == "auth_permanent":
        return f"{provider} isn't accepting your saved login."
    if reason == "billing":
        return f"{provider} rejected the request — looks like a billing issue on the account."
    return None


def _should_include_recovery_hint(reason: FailoverReason) -> bool:
    if reason in ("auth", "auth_permanent", "session_expired", "billing"):
        return True
    if reason in ("rate_limit", "overloaded", "timeout", "server_error", "model_not_found"):
        return False
    return True


def _diagnostic_suffix(cause: Any, primary: str) -> str | None:
    if cause is None:
        return None
    text = str(cause).strip()
    if not text or text in primary:
        return None
    return f" ({text})"


def format_auth_profile_failure_message(
    reason: FailoverReason,
    provider: str,
    all_in_cooldown: bool,
    cause: Any = None,
    config: Any = None,
    workspace_dir: str | None = None,
    env: Any = None,
) -> str:
    description = _describe_reason(reason, provider, all_in_cooldown)
    if not description:
        cause_text = str(cause).strip() if cause else ""
        if cause_text:
            return cause_text
        return f"Couldn't reach {provider} with any of your saved logins right now."

    hint = None
    if _should_include_recovery_hint(reason):
        try:
            from openclaw.agents.provider_auth_recovery_hint import (
                build_provider_auth_recovery_hint,
            )
            hint = build_provider_auth_recovery_hint(
                provider=provider,
                config=config,
                workspace_dir=workspace_dir,
                env=env,
            )
        except Exception:
            pass

    suffix = _diagnostic_suffix(cause, description)
    parts = [description]
    if hint:
        parts.append(hint)
    message = " ".join(parts)
    return f"{message}{suffix}" if suffix else message
