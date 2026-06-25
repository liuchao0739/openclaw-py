"""Conversation binding record facade.

Routes binding CRUD helpers through the shared session binding service.
"""

from __future__ import annotations

from typing import Any


async def create_conversation_binding_record(input_data: dict[str, Any]) -> dict[str, Any]:
    """Create a conversation binding record via the session binding service."""
    try:
        from openclaw.infra.outbound.session_binding_service import get_session_binding_service

        service = get_session_binding_service()
        return await service.bind(input_data)
    except Exception:
        return {}


def get_conversation_binding_capabilities(params: dict[str, Any]) -> dict[str, Any]:
    """Get conversation binding capabilities for a channel/account."""
    try:
        from openclaw.infra.outbound.session_binding_service import get_session_binding_service

        service = get_session_binding_service()
        return service.get_capabilities(params)
    except Exception:
        return {"supported": False}


def list_session_binding_records(target_session_key: str) -> list[dict[str, Any]]:
    """List session binding records for a target session key."""
    try:
        from openclaw.infra.outbound.session_binding_service import get_session_binding_service

        service = get_session_binding_service()
        return service.list_by_session(target_session_key)
    except Exception:
        return []
