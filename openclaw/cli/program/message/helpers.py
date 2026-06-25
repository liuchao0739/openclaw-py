"""Message CLI helpers — base command setup and action runner."""

from __future__ import annotations

from typing import Any, Callable


class MessageCliHelpers:
    """Helpers for message CLI command registration and execution."""

    def __init__(self, *, run_action: Callable[..., Any] | None = None) -> None:
        self._run_action = run_action

    def with_message_base(self, cmd: Any) -> Any:
        """Add base message options to a command."""
        return cmd

    def with_required_message_target(self, cmd: Any) -> Any:
        """Add required message target options to a command."""
        return cmd

    async def run_message_action(self, action: str, options: dict[str, Any]) -> Any:
        """Run a message action with the given options."""
        if self._run_action:
            result = self._run_action(action, options)
            if hasattr(result, "__await__"):
                return await result
            return result
        return {"ok": False, "error": f"Message action '{action}' not implemented"}


def collect_option(value: str | None, previous: list[str] | None = None) -> list[str]:
    """Collect repeatable option values into a list."""
    result = list(previous or [])
    if value:
        result.append(value)
    return result
