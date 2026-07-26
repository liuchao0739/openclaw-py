"""Amazon Bedrock Mantle provider extension."""

from openclaw_extensions.amazon_bedrock_mantle.api import (
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
from openclaw_extensions.amazon_bedrock_mantle.mantle_anthropic_runtime import (
    create_mantle_anthropic_stream_fn,
    resolve_mantle_anthropic_base_url,
)
from openclaw_extensions.amazon_bedrock_mantle.register_sync_runtime import (
    register_bedrock_mantle_plugin,
)

__all__ = [
    "MANTLE_IAM_TOKEN_MARKER",
    "create_mantle_anthropic_stream_fn",
    "discover_mantle_models",
    "generate_bearer_token_from_iam",
    "get_cached_iam_token",
    "merge_implicit_mantle_provider",
    "register_bedrock_mantle_plugin",
    "reset_iam_token_cache_for_test",
    "reset_mantle_discovery_cache_for_test",
    "resolve_implicit_mantle_provider",
    "resolve_mantle_anthropic_base_url",
    "resolve_mantle_bearer_token",
    "resolve_mantle_runtime_bearer_token",
]
