"""Tests for bindings — conversation binding record facade."""

from __future__ import annotations

from openclaw.bindings import (
    create_conversation_binding_record,
    get_conversation_binding_capabilities,
    list_session_binding_records,
)


class TestConversationBindings:
    async def test_create_returns_empty_when_unavailable(self):
        result = await create_conversation_binding_record({"channel": "telegram"})
        assert result == {}

    def test_get_capabilities_returns_default(self):
        result = get_conversation_binding_capabilities({"channel": "telegram", "accountId": "a1"})
        assert result["supported"] is False

    def test_list_returns_empty(self):
        result = list_session_binding_records("agent:main:session")
        assert result == []
