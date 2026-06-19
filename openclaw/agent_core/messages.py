"""Agent core message aliases."""

from __future__ import annotations

from openclaw.llm.core import (
    AssistantMessage,
    Message,
    Tool,
    ToolCall,
    ToolResultMessage,
    UserMessage,
)

ToolExecutionMode = str  # "sequential" | "parallel"
QueueMode = str  # "all" | "one-at-a-time"

AgentToolCall = ToolCall

__all__ = [
    "AgentToolCall",
    "AssistantMessage",
    "Message",
    "QueueMode",
    "Tool",
    "ToolCall",
    "ToolExecutionMode",
    "ToolResultMessage",
    "UserMessage",
]
