"""Tests for agents/auth-profiles modules."""

from openclaw.agents.auth_profiles import (
    AUTH_PROFILE_FILENAME,
    AUTH_STATE_FILENAME,
    LEGACY_AUTH_FILENAME,
    resolve_auth_store_path,
    resolve_auth_state_path,
    resolve_legacy_auth_store_path,
    resolve_oauth_refresh_lock_path,
    set_auth_profile_failure_hook,
    notify_auth_profile_failure_hook,
    clone_auth_profile_store,
)


class TestPathConstants:
    def test_filenames(self):
        assert AUTH_PROFILE_FILENAME == "auth-profiles.json"
        assert AUTH_STATE_FILENAME == "auth-state.json"
        assert LEGACY_AUTH_FILENAME == "auth.json"


class TestPaths:
    def test_store_path(self):
        assert resolve_auth_store_path("/tmp/state") == "/tmp/state/auth-profiles.json"

    def test_state_path(self):
        assert resolve_auth_state_path("/tmp/state") == "/tmp/state/auth-state.json"

    def test_legacy_path(self):
        assert resolve_legacy_auth_store_path("/tmp/state") == "/tmp/state/auth.json"

    def test_oauth_lock_path(self):
        assert resolve_oauth_refresh_lock_path("/tmp/state") == "/tmp/state/oauth-refresh.lock"


class TestFailureHook:
    def test_set_and_notify(self):
        calls = []
        set_auth_profile_failure_hook(lambda: calls.append(1))
        notify_auth_profile_failure_hook()
        assert calls == [1]

    def test_no_hook(self):
        set_auth_profile_failure_hook(None)
        notify_auth_profile_failure_hook()

    def test_replace_hook(self):
        calls1 = []
        calls2 = []
        set_auth_profile_failure_hook(lambda: calls1.append(1))
        set_auth_profile_failure_hook(lambda: calls2.append(1))
        notify_auth_profile_failure_hook()
        assert calls1 == []
        assert calls2 == [1]


class TestClone:
    def test_deep_clone(self):
        store = {"profiles": {"p1": {"token": "abc"}}, "active": "p1"}
        result = clone_auth_profile_store(store)
        assert result == store
        assert result is not store
        assert result["profiles"] is not store["profiles"]

    def test_rejects_non_json(self):
        try:
            clone_auth_profile_store({"fn": lambda: None})
            assert False
        except TypeError:
            pass

    def test_empty(self):
        assert clone_auth_profile_store({}) == {}

    def test_nested_lists(self):
        store = {"items": [1, "two", {"three": True}]}
        result = clone_auth_profile_store(store)
        assert result == store
        assert result["items"] is not store["items"]
