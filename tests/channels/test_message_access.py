"""Tests for channels/message_access — store, effective, dm-allow-state."""

from __future__ import annotations

from openclaw.channels.message_access import (
    read_channel_ingress_store_allow_from_for_dm_policy,
    resolve_channel_ingress_effective_allow_from_lists,
    resolve_dm_allow_audit_state,
)


class TestStoreAllowFrom:
    async def test_open_policy_returns_empty(self):
        result = await read_channel_ingress_store_allow_from_for_dm_policy(
            "telegram", "acc1", dm_policy="open"
        )
        assert result == []

    async def test_allowlist_policy_returns_empty(self):
        result = await read_channel_ingress_store_allow_from_for_dm_policy(
            "telegram", "acc1", dm_policy="allowlist"
        )
        assert result == []

    async def test_should_read_false_returns_empty(self):
        result = await read_channel_ingress_store_allow_from_for_dm_policy(
            "telegram", "acc1", should_read=False
        )
        assert result == []

    async def test_custom_read_store(self):
        async def read_store(provider: str, account_id: str):
            return ["user1", "user2"]

        result = await read_channel_ingress_store_allow_from_for_dm_policy(
            "telegram", "acc1", read_store=read_store
        )
        assert result == ["user1", "user2"]

    async def test_read_store_failure_returns_empty(self):
        async def failing_store(provider: str, account_id: str):
            raise RuntimeError("store unavailable")

        result = await read_channel_ingress_store_allow_from_for_dm_policy(
            "telegram", "acc1", read_store=failing_store
        )
        assert result == []


class TestEffectiveAllowFrom:
    def test_basic_merge(self):
        result = resolve_channel_ingress_effective_allow_from_lists(
            allow_from=["alice", "bob"],
            store_allow_from=["charlie"],
        )
        assert "alice" in result["effectiveAllowFrom"]
        assert "bob" in result["effectiveAllowFrom"]
        assert "charlie" in result["effectiveAllowFrom"]

    def test_open_policy_ignores_store(self):
        result = resolve_channel_ingress_effective_allow_from_lists(
            allow_from=["alice"],
            store_allow_from=["bob"],
            dm_policy="open",
        )
        assert "alice" in result["effectiveAllowFrom"]
        assert "bob" not in result["effectiveAllowFrom"]

    def test_group_fallback(self):
        result = resolve_channel_ingress_effective_allow_from_lists(
            allow_from=["alice"],
            group_allow_from=None,
            group_allow_from_fallback_to_allow_from=True,
        )
        assert "alice" in result["effectiveGroupAllowFrom"]

    def test_group_no_fallback(self):
        result = resolve_channel_ingress_effective_allow_from_lists(
            allow_from=["alice"],
            group_allow_from=None,
            group_allow_from_fallback_to_allow_from=False,
        )
        assert result["effectiveGroupAllowFrom"] == []

    def test_empty_inputs(self):
        result = resolve_channel_ingress_effective_allow_from_lists()
        assert result["effectiveAllowFrom"] == []
        assert result["effectiveGroupAllowFrom"] == []


class TestDmAllowAuditState:
    async def test_basic(self):
        result = await resolve_dm_allow_audit_state(
            "telegram", "acc1", allow_from=["alice", "bob"]
        )
        assert "alice" in result["configAllowFrom"]
        assert result["hasWildcard"] is False
        assert result["allowCount"] >= 2
        assert result["isMultiUserDm"] is True

    async def test_wildcard(self):
        result = await resolve_dm_allow_audit_state(
            "telegram", "acc1", allow_from=["*"]
        )
        assert result["hasWildcard"] is True
        assert result["isMultiUserDm"] is True

    async def test_single_user(self):
        result = await resolve_dm_allow_audit_state(
            "telegram", "acc1", allow_from=["alice"]
        )
        assert result["isMultiUserDm"] is False

    async def test_with_store(self):
        async def read_store(provider: str, account_id: str):
            return ["charlie"]

        result = await resolve_dm_allow_audit_state(
            "telegram", "acc1", allow_from=["alice"], read_store=read_store
        )
        assert result["allowCount"] >= 2

    async def test_empty(self):
        result = await resolve_dm_allow_audit_state("telegram", "acc1")
        assert result["hasWildcard"] is False
        assert result["allowCount"] == 0
        assert result["isMultiUserDm"] is False
