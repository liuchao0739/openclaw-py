"""Public LLM core contracts shared by providers, plugin SDK wrappers, and tests.

Mirrors packages/llm-core/src/index.ts.
"""

from __future__ import annotations

from .model_contracts.anthropic import (
    CLAUDE_FABLE_5_THINKING_PROFILE,
    ClaudeEffortModelRef,
    ClaudeModelRef,
    resolve_claude_fable5_model_identity,
    resolve_claude_model_identity,
    resolve_claude_native_thinking_level_map,
    supports_claude_adaptive_thinking,
    supports_claude_native_max_effort,
    supports_claude_native_xhigh_effort,
)
from .utils.diagnostics import (
    AssistantMessageDiagnostic,
    DiagnosticErrorInfo,
    append_assistant_message_diagnostic,
    create_assistant_message_diagnostic,
    extract_diagnostic_error,
    format_thrown_value,
)
from .utils.event_stream import (
    AssistantMessageEvent,
    AssistantMessageEventStream,
    EventStream,
    create_assistant_message_event_stream,
)
from .validation import validate_tool_arguments, validate_tool_call

__all__ = [
    "CLAUDE_FABLE_5_THINKING_PROFILE",
    "AssistantMessageDiagnostic",
    "AssistantMessageEvent",
    "AssistantMessageEventStream",
    "ClaudeEffortModelRef",
    "ClaudeModelRef",
    "DiagnosticErrorInfo",
    "EventStream",
    "append_assistant_message_diagnostic",
    "create_assistant_message_diagnostic",
    "create_assistant_message_event_stream",
    "extract_diagnostic_error",
    "format_thrown_value",
    "resolve_claude_fable5_model_identity",
    "resolve_claude_model_identity",
    "resolve_claude_native_thinking_level_map",
    "supports_claude_adaptive_thinking",
    "supports_claude_native_max_effort",
    "supports_claude_native_xhigh_effort",
    "validate_tool_arguments",
    "validate_tool_call",
]
