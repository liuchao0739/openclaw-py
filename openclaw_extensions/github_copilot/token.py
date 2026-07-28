from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.provider_auth import (
    DEFAULT_COPILOT_API_BASE_URL,
    derive_copilot_api_base_url_from_token,
    resolve_copilot_api_token,
)

__all__ = [
    "DEFAULT_COPILOT_API_BASE_URL",
    "derive_copilot_api_base_url_from_token",
    "resolve_copilot_api_token",
]
