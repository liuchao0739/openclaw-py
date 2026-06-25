"""Auth choice barrel — re-exports for onboarding and agent setup commands."""

from __future__ import annotations

from typing import Any


def apply_auth_choice(*args: Any, **kwargs: Any) -> Any:
    """Apply auth choice. Deferred to auth-choice.apply module."""
    try:
        from openclaw.commands.auth_choice_apply import apply_auth_choice as _apply

        return _apply(*args, **kwargs)
    except Exception:
        return None


def warn_if_model_config_looks_off(*args: Any, **kwargs: Any) -> Any:
    """Warn if model config looks off. Deferred to auth-choice.model-check module."""
    try:
        from openclaw.commands.auth_choice_model_check import warn_if_model_config_looks_off as _warn

        return _warn(*args, **kwargs)
    except Exception:
        return None
