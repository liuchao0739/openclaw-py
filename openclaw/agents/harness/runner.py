from __future__ import annotations

from typing import Any


class AgentHarnessEventType:
    TURN_STARTED = "turn.started"
    TURN_COMPLETED = "turn.completed"
    MESSAGE_ADDED = "message.added"
    TOOL_EXECUTED = "tool.executed"
    ERROR_OCCURRED = "error.occurred"


class AgentHarnessResult:
    def __init__(self, success: bool, data: Any = None, error: str | None = None):
        self.success = success
        self.data = data
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }


def run_agent_turn(
    messages: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
    tools: list[Any] | None = None,
) -> AgentHarnessResult:
    return AgentHarnessResult(
        success=True,
        data={"messages": messages, "config": config or {}},
    )
