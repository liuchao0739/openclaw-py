"""Routing package — session keys, binding scopes, route resolution."""

from .peer_kind_match import peer_kind_matches
from .default_account_warnings import (
    format_channel_accounts_default_path,
    format_set_explicit_default_instruction,
    format_set_explicit_default_to_configured_instruction,
)
from .account_id import (
    DEFAULT_ACCOUNT_ID,
    normalize_account_id,
    normalize_optional_account_id,
)
from .session_key import (
    DEFAULT_AGENT_ID,
    DEFAULT_MAIN_KEY,
    build_agent_main_session_key,
    build_agent_peer_session_key,
    build_agent_session_key,
    normalize_agent_id,
    normalize_main_key,
    sanitize_agent_id,
)
from .binding_scope import (
    normalize_route_binding_id,
    normalize_route_binding_roles,
    normalize_route_binding_channel_id,
    resolve_normalized_route_binding_match,
    route_binding_scope_matches,
)
from .bindings import (
    list_bindings,
    list_bound_account_ids,
    resolve_default_agent_bound_account_id,
    build_channel_account_bindings,
    resolve_preferred_account_id,
)
from .bound_account_read import resolve_first_bound_account_id
from .resolve_route import (
    derive_last_route_policy,
    resolve_inbound_last_route_session_key,
    pick_first_existing_agent_id,
    resolve_agent_route,
)
from .channel_route_targets import collect_channel_route_targets

__all__ = [
    "peer_kind_matches",
    "format_channel_accounts_default_path",
    "format_set_explicit_default_instruction",
    "format_set_explicit_default_to_configured_instruction",
    "DEFAULT_ACCOUNT_ID",
    "normalize_account_id",
    "normalize_optional_account_id",
    "DEFAULT_AGENT_ID",
    "DEFAULT_MAIN_KEY",
    "build_agent_main_session_key",
    "build_agent_peer_session_key",
    "build_agent_session_key",
    "normalize_agent_id",
    "normalize_main_key",
    "sanitize_agent_id",
    "normalize_route_binding_id",
    "normalize_route_binding_roles",
    "normalize_route_binding_channel_id",
    "resolve_normalized_route_binding_match",
    "route_binding_scope_matches",
    "list_bindings",
    "list_bound_account_ids",
    "resolve_default_agent_bound_account_id",
    "build_channel_account_bindings",
    "resolve_preferred_account_id",
    "resolve_first_bound_account_id",
    "derive_last_route_policy",
    "resolve_inbound_last_route_session_key",
    "pick_first_existing_agent_id",
    "resolve_agent_route",
    "collect_channel_route_targets",
]
