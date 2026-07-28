from __future__ import annotations

from typing import Any


class RuntimePlanAction:
    SEND_MESSAGE = "send_message"
    CALL_TOOL = "call_tool"
    GENERATE_RESPONSE = "generate_response"
    COMPLETE_TURN = "complete_turn"
    ERROR = "error"


class RuntimeStep:
    def __init__(
        self,
        action: str,
        payload: dict[str, Any] | None = None,
        status: str = "pending",
    ):
        self.action = action
        self.payload = payload or {}
        self.status = status

    def execute(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        self.status = "completed"
        return {
            "action": self.action,
            "status": self.status,
            "payload": self.payload,
        }


class RuntimePlan:
    def __init__(self, steps: list[RuntimeStep] | None = None):
        self.steps = steps or []
        self.current_index = 0

    def add_step(self, action: str, payload: dict[str, Any] | None = None) -> RuntimeStep:
        step = RuntimeStep(action, payload)
        self.steps.append(step)
        return step

    def next(self) -> RuntimeStep | None:
        if self.current_index >= len(self.steps):
            return None
        step = self.steps[self.current_index]
        self.current_index += 1
        return step

    def remaining(self) -> int:
        return max(0, len(self.steps) - self.current_index)
