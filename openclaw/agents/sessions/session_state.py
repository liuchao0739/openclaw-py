from __future__ import annotations

from typing import Any


class SessionState:
    def __init__(self, session_id: str | None = None):
        self.session_id = session_id
        self.messages: list[dict[str, Any]] = []
        self.metadata: dict[str, Any] = {}

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        self.messages.append({
            "role": role,
            "content": content,
            **kwargs,
        })

    def get_history(self) -> list[dict[str, Any]]:
        return list(self.messages)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sessionId": self.session_id,
            "messages": self.messages,
            "metadata": self.metadata,
        }
