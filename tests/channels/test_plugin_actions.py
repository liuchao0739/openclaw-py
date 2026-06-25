"""Tests for channels/plugins/actions — reaction message id, shared."""

from __future__ import annotations

from openclaw.channels.plugins.actions import (
    create_union_action_gate,
    list_token_sourced_accounts,
    resolve_reaction_message_id,
)


class TestReactionMessageId:
    def test_explicit_message_id(self):
        result = resolve_reaction_message_id(
            {"messageId": "456"},
            {"currentMessageId": "123"},
        )
        assert result == "456"

    def test_snake_case_alias(self):
        result = resolve_reaction_message_id({"message_id": "789"})
        assert result == "789"

    def test_fallback_to_context(self):
        result = resolve_reaction_message_id(
            {},
            {"currentMessageId": "9001"},
        )
        assert result == "9001"

    def test_no_args_no_context(self):
        assert resolve_reaction_message_id({}) is None
        assert resolve_reaction_message_id({}, None) is None

    def test_numeric_message_id(self):
        result = resolve_reaction_message_id({"messageId": 42})
        assert result == 42


class TestShared:
    def test_list_token_sourced_accounts(self):
        accounts = [
            {"tokenSource": "oauth"},
            {"tokenSource": "none"},
            {"tokenSource": "bot"},
            {},
        ]
        result = list_token_sourced_accounts(accounts)
        assert len(result) == 3
        assert all(acc.get("tokenSource") != "none" for acc in result)

    def test_create_union_action_gate(self):
        accounts = [
            {"actions": {"read": True, "write": False}},
            {"actions": {"read": False, "write": True}},
        ]

        def make_gate(acc: dict) -> callable:
            actions = acc.get("actions", {})

            def gate(key: str, default: bool = True) -> bool:
                val = actions.get(key)
                return val if val is not None else default

            return gate

        gate = create_union_action_gate(accounts, make_gate)
        assert gate("read") is True   # first account has read=True
        assert gate("write") is True  # second account has write=True
        assert gate("execute") is True  # default

    def test_create_union_action_gate_all_false(self):
        accounts = [{"actions": {"read": False}}]

        def make_gate(acc: dict) -> callable:
            actions = acc.get("actions", {})

            def gate(key: str, default: bool = True) -> bool:
                return actions.get(key, default)

            return gate

        gate = create_union_action_gate(accounts, make_gate)
        assert gate("read") is False
