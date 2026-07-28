from __future__ import annotations

from typing import Any


class AgentHookEvent:
    SESSION_STARTED = "session.started"
    SESSION_COMPLETED = "session.completed"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"
    TOOL_CALLED = "tool.called"
    TOOL_COMPLETED = "tool.completed"
    AGENT_THINKING = "agent.thinking"
    AGENT_RESPONSE = "agent.response"
    AGENT_ERROR = "agent.error"


class AgentHookLifecycle:
    ON_SESSION_START = "onSessionStart"
    ON_SESSION_END = "onSessionEnd"
    ON_MESSAGE = "onMessage"
    ON_TOOL_CALL = "onToolCall"
    ON_TOOL_RESULT = "onToolResult"
    ON_AGENT_THOUGHT = "onAgentThought"
    ON_AGENT_RESPONSE = "onAgentResponse"
    ON_AGENT_ERROR = "onAgentError"
