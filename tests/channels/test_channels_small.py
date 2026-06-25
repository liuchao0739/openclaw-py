"""Tests for channels — allowlists, status, transport."""

from __future__ import annotations

import time

from openclaw.channels.allowlists.resolve_utils import (
    build_allowlist_resolution_summary,
    canonicalize_allowlist_with_resolved_ids,
    merge_allowlist,
)
from openclaw.channels.status.read_model import (
    get_runtime_channel_accounts,
    has_runtime_credential_available,
    mark_configured_unavailable_credential_statuses_available,
    normalize_runtime_channel_account_snapshots,
)
from openclaw.channels.transport.stall_watchdog import create_armable_stall_watchdog


class TestAllowlists:
    def test_merge_allowlist(self):
        result = merge_allowlist(["alice", "bob"], ["charlie", "alice"])
        assert "alice" in result
        assert "bob" in result
        assert "charlie" in result
        assert len(result) == 3  # deduped

    def test_merge_allowlist_empty(self):
        assert merge_allowlist(None, []) == []

    def test_build_resolution_summary(self):
        users = [
            {"input": "alice", "resolved": True, "id": "user-1"},
            {"input": "bob", "resolved": False},
        ]
        result = build_allowlist_resolution_summary(users)
        assert len(result["mapping"]) == 1
        assert "alice" in result["mapping"][0]
        assert len(result["unresolved"]) == 1
        assert result["additions"] == ["user-1"]

    def test_canonicalize_with_resolved_ids(self):
        resolved_map = {"alice": {"resolved": True, "id": "user-1"}}
        result = canonicalize_allowlist_with_resolved_ids(["alice", "bob", "*"], resolved_map)
        assert "user-1" in result
        assert "bob" in result
        assert "*" in result


class TestStatus:
    def test_get_runtime_channel_accounts(self):
        payload = {"channelAccounts": {"telegram": [{"accountId": "acc1"}]}}
        accounts = get_runtime_channel_accounts(payload, "telegram")
        assert len(accounts) == 1
        assert accounts[0]["accountId"] == "acc1"

    def test_get_runtime_channel_accounts_missing(self):
        accounts = get_runtime_channel_accounts({}, "telegram")
        assert accounts == []

    def test_normalize_snapshots(self):
        payload = {
            "channelAccounts": {
                "telegram": [{"accountId": "a1"}, {"accountId": "a2"}],
                "discord": [{"notAccountId": "x"}],
            }
        }
        result = normalize_runtime_channel_account_snapshots(payload)
        assert "telegram" in result
        assert len(result["telegram"]) == 2
        assert "discord" not in result

    def test_has_runtime_credential_available(self):
        accounts = [{"accountId": "acc1", "running": True}]
        assert has_runtime_credential_available(accounts, "acc1") is True

    def test_has_runtime_credential_unavailable(self):
        accounts = [{"accountId": "acc1", "tokenStatus": "configured_unavailable"}]
        assert has_runtime_credential_available(accounts, "acc1") is False

    def test_has_runtime_credential_not_found(self):
        assert has_runtime_credential_available([], "acc1") is False

    def test_mark_unavailable_as_available(self):
        account = {"accountId": "a1", "tokenStatus": "configured_unavailable"}
        result = mark_configured_unavailable_credential_statuses_available(account)
        assert result["tokenStatus"] == "available"


class TestStallWatchdog:
    def test_arm_and_disarm(self):
        called = []
        wd = create_armable_stall_watchdog("test", 1000, lambda meta: called.append(meta))
        wd.arm()
        assert wd.is_armed() is True
        wd.disarm()
        assert wd.is_armed() is False
        wd.stop()

    def test_stop_prevents_arm(self):
        wd = create_armable_stall_watchdog("test", 1000, lambda meta: None)
        wd.stop()
        wd.arm()
        assert wd.is_armed() is False

    def test_touch_updates_activity(self):
        wd = create_armable_stall_watchdog("test", 10000, lambda meta: None)
        wd.arm()
        wd.touch()
        wd.stop()

    def test_timeout_fires(self):
        called = []
        wd = create_armable_stall_watchdog(
            "test", 50, lambda meta: called.append(meta), check_interval_ms=25
        )
        wd.arm()
        time.sleep(0.15)
        wd.stop()
        assert len(called) >= 1
        assert called[0]["timeoutMs"] == 50

    def test_timeout_disarms(self):
        called = []
        wd = create_armable_stall_watchdog(
            "test", 50, lambda meta: called.append(meta), check_interval_ms=25
        )
        wd.arm()
        time.sleep(0.15)
        assert wd.is_armed() is False
        wd.stop()
