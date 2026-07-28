from __future__ import annotations

from typing import Any


class AgentCommand:
    def __init__(self, name: str, handler: Any = None, **metadata: Any):
        self.name = name
        self.handler = handler
        self.metadata = metadata

    def execute(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.handler:
            return {"status": "error", "message": f"No handler for command: {self.name}"}
        try:
            result = self.handler(context or {})
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}


class AgentCommandRegistry:
    def __init__(self):
        self._commands: dict[str, AgentCommand] = {}

    def register(self, name: str, handler: Any = None, **metadata: Any) -> AgentCommand:
        cmd = AgentCommand(name, handler, **metadata)
        self._commands[name] = cmd
        return cmd

    def get(self, name: str) -> AgentCommand | None:
        return self._commands.get(name)

    def list(self) -> list[str]:
        return sorted(self._commands.keys())

    def execute(self, name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        cmd = self._commands.get(name)
        if not cmd:
            return {"status": "error", "message": f"Unknown command: {name}"}
        return cmd.execute(context)
