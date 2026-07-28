from __future__ import annotations

from typing import Any


def create_session_id() -> str:
    import uuid
    return str(uuid.uuid4())


def resolve_session_id(
    config: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> str:
    if session_id:
        return session_id
    if config and config.get("sessionId"):
        return config["sessionId"]
    return create_session_id()
