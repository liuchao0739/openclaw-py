from openclaw.agents.embedded_agent_helpers.errors import (
    GENERIC_ASSISTANT_ERROR_TEXT,
    format_assistant_error_text,
    is_compaction_failure_error,
    is_context_overflow_error,
    is_likely_context_overflow_error,
    is_reasoning_constraint_error_message,
)
from openclaw.agents.embedded_agent_helpers.turns import (
    merge_consecutive_user_turns,
    validate_anthropic_turns,
    validate_gemini_turns,
)
from openclaw.agents.embedded_agent_helpers.failover_matches import (
    is_auth_error_message,
    is_billing_error_message,
    is_overloaded_error_message,
    is_rate_limit_error_message,
    is_timeout_error_message,
    matches_format_error_pattern,
)
from openclaw.agents.embedded_agent_helpers.thinking import (
    drop_thinking_blocks,
    pick_fallback_thinking_level,
)
from openclaw.agents.embedded_agent_helpers.types import EmbeddedContextFile, FailoverReason
from openclaw.agents.embedded_agent_helpers.messaging_dedupe import (
    normalize_text_for_comparison,
    is_messaging_tool_duplicate_normalized,
    is_messaging_tool_duplicate,
)

__all__ = [
    "EmbeddedContextFile",
    "FailoverReason",
    "GENERIC_ASSISTANT_ERROR_TEXT",
    "format_assistant_error_text",
    "is_compaction_failure_error",
    "is_context_overflow_error",
    "is_likely_context_overflow_error",
    "merge_consecutive_user_turns",
    "validate_anthropic_turns",
    "validate_gemini_turns",
    "drop_thinking_blocks",
    "is_auth_error_message",
    "is_billing_error_message",
    "is_overloaded_error_message",
    "is_rate_limit_error_message",
    "is_reasoning_constraint_error_message",
    "is_timeout_error_message",
    "matches_format_error_pattern",
    "pick_fallback_thinking_level",
    "normalize_text_for_comparison",
    "is_messaging_tool_duplicate_normalized",
    "is_messaging_tool_duplicate",
]
