"""Agent tools — shared contracts, web utilities, session helpers, and tool implementations.

This package provides the building blocks for built-in agent tools. The full
tool factory set (bash, edit, read, write, web-fetch, web-search, etc.) is
deferred until the runtime layer is ported.
"""

from openclaw.agents.tools.chat_history_text import (
    extract_text_from_content,
    format_chat_history,
    format_chat_history_entry,
)
from openclaw.agents.tools.common import (
    ToolAuthorizationError,
    ToolInputError,
    as_tool_params_record,
    create_action_gate,
    json_error_result,
    json_text_result,
    read_array_param,
    read_boolean_param,
    read_number_param,
    read_optional_string_param,
    read_string_param,
)
from openclaw.agents.tools.manifest_capability_availability import (
    filter_available_tools,
    get_available_capabilities,
    has_capability,
    is_tool_available,
)
from openclaw.agents.tools.model_config_helpers import (
    get_api_key_env_var,
    resolve_api_key,
    resolve_model_config,
)
from openclaw.agents.tools.nodes_utils import (
    filter_nodes_by_platform,
    format_node_display_name,
    is_valid_node_id,
    resolve_node_by_id,
)
from openclaw.agents.tools.session_message_text import (
    extract_session_message_text,
    get_message_tool_calls,
    is_assistant_message,
    is_tool_result_message,
    is_user_message,
)
from openclaw.agents.tools.sessions_helpers import (
    format_session_display_name,
    is_valid_session_key,
    parse_session_key,
    resolve_session_target,
)
from openclaw.agents.tools.sessions_send_tokens import (
    MAX_SESSION_SEND_TOKENS,
    estimate_message_tokens,
    estimate_messages_tokens,
    estimate_tokens,
    is_within_send_limit,
    truncate_messages_to_limit,
)
from openclaw.agents.tools.web_search_provider_config import (
    WebSearchProviderConfig,
    get_web_search_provider_config,
    list_web_search_providers,
    register_web_search_provider,
    resolve_web_search_api_key,
)
from openclaw.agents.tools.web_shared import (
    MAX_WEB_FETCH_CONTENT_CHARS,
    MAX_WEB_SEARCH_RESULTS,
    format_web_fetch_result,
    format_web_search_result,
    is_valid_url,
    normalize_url,
    truncate_web_content,
)

__all__ = [
    "MAX_SESSION_SEND_TOKENS",
    "MAX_WEB_FETCH_CONTENT_CHARS",
    "MAX_WEB_SEARCH_RESULTS",
    "ToolAuthorizationError",
    "ToolInputError",
    "WebSearchProviderConfig",
    "as_tool_params_record",
    "create_action_gate",
    "estimate_message_tokens",
    "estimate_messages_tokens",
    "estimate_tokens",
    "extract_session_message_text",
    "extract_text_from_content",
    "filter_available_tools",
    "filter_nodes_by_platform",
    "format_chat_history",
    "format_chat_history_entry",
    "format_node_display_name",
    "format_session_display_name",
    "format_web_fetch_result",
    "format_web_search_result",
    "get_api_key_env_var",
    "get_available_capabilities",
    "get_message_tool_calls",
    "get_web_search_provider_config",
    "has_capability",
    "is_assistant_message",
    "is_tool_available",
    "is_tool_result_message",
    "is_user_message",
    "is_valid_node_id",
    "is_valid_session_key",
    "is_valid_url",
    "is_within_send_limit",
    "json_error_result",
    "json_text_result",
    "list_web_search_providers",
    "normalize_url",
    "parse_session_key",
    "read_array_param",
    "read_boolean_param",
    "read_number_param",
    "read_optional_string_param",
    "read_string_param",
    "register_web_search_provider",
    "resolve_api_key",
    "resolve_model_config",
    "resolve_node_by_id",
    "resolve_session_target",
    "resolve_web_search_api_key",
    "truncate_messages_to_limit",
    "truncate_web_content",
]
