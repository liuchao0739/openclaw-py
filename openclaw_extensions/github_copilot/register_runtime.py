from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.provider_auth import (
    coerce_secret_ref,
    ensure_auth_profile_store,
    list_profiles_for_provider,
)

from openclaw_extensions.github_copilot.login import github_copilot_login_command
from openclaw_extensions.github_copilot.models import (
    PROVIDER_ID,
    resolve_copilot_forward_compat_model,
)
from openclaw_extensions.github_copilot.stream import (
    wrap_copilot_anthropic_stream,
    wrap_copilot_provider_stream,
)
from openclaw_extensions.github_copilot.token import (
    DEFAULT_COPILOT_API_BASE_URL,
    resolve_copilot_api_token,
)
from openclaw_extensions.github_copilot.usage import fetch_copilot_usage

__all__ = [
    "DEFAULT_COPILOT_API_BASE_URL",
    "PROVIDER_ID",
    "coerce_secret_ref",
    "ensure_auth_profile_store",
    "fetch_copilot_usage",
    "github_copilot_login_command",
    "list_profiles_for_provider",
    "resolve_copilot_api_token",
    "resolve_copilot_forward_compat_model",
    "wrap_copilot_anthropic_stream",
    "wrap_copilot_provider_stream",
]
