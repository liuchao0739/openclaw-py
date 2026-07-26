"""Public Amazon Bedrock Mantle API barrel for discovery and bearer-token helpers."""

from openclaw_extensions.amazon_bedrock_mantle.discovery import (
    MANTLE_IAM_TOKEN_MARKER,
    discover_mantle_models,
    generate_bearer_token_from_iam,
    get_cached_iam_token,
    merge_implicit_mantle_provider,
    reset_iam_token_cache_for_test,
    reset_mantle_discovery_cache_for_test,
    resolve_implicit_mantle_provider,
    resolve_mantle_bearer_token,
    resolve_mantle_runtime_bearer_token,
)

__all__ = [
    "MANTLE_IAM_TOKEN_MARKER",
    "discover_mantle_models",
    "generate_bearer_token_from_iam",
    "get_cached_iam_token",
    "merge_implicit_mantle_provider",
    "reset_iam_token_cache_for_test",
    "reset_mantle_discovery_cache_for_test",
    "resolve_implicit_mantle_provider",
    "resolve_mantle_bearer_token",
    "resolve_mantle_runtime_bearer_token",
]
