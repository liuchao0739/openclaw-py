"""Tests for hooks core modules."""

from openclaw.hooks.gmail_watcher_errors import is_address_in_use_error
from openclaw.hooks.internal_hook_types import InternalHookEvent
from openclaw.hooks.legacy_config import get_legacy_internal_hook_handlers
from openclaw.hooks.installs import record_hook_install


class TestGmailWatcherErrors:
    def test_address_in_use(self):
        assert is_address_in_use_error("Error: address already in use") is True

    def test_eaddrinuse(self):
        assert is_address_in_use_error("EADDRINUSE 0.0.0.0:3000") is True

    def test_case_insensitive(self):
        assert is_address_in_use_error("Address Already In Use") is True

    def test_other_error(self):
        assert is_address_in_use_error("Connection refused") is False

    def test_empty(self):
        assert is_address_in_use_error("") is False


class TestInternalHookEvent:
    def test_creation(self):
        event = InternalHookEvent(
            type="session",
            action="end",
            session_key="agent:main:sess-1",
        )
        assert event.type == "session"
        assert event.action == "end"
        assert event.context == {}
        assert event.messages == []

    def test_with_context(self):
        event = InternalHookEvent(
            type="command",
            action="run",
            session_key="key",
            context={"cmd": "ls"},
            messages=["started"],
        )
        assert event.context["cmd"] == "ls"
        assert event.messages == ["started"]


class TestLegacyConfig:
    def test_valid_handlers(self):
        config = {
            "hooks": {
                "internal": {
                    "handlers": [
                        {"event": "session_end", "module": "./my-hook.js"},
                    ]
                }
            }
        }
        handlers = get_legacy_internal_hook_handlers(config)
        assert len(handlers) == 1
        assert handlers[0]["event"] == "session_end"

    def test_no_hooks(self):
        assert get_legacy_internal_hook_handlers({}) == []

    def test_no_internal(self):
        assert get_legacy_internal_hook_handlers({"hooks": {}}) == []

    def test_no_handlers(self):
        assert get_legacy_internal_hook_handlers({"hooks": {"internal": {}}}) == []

    def test_handlers_not_list(self):
        config = {"hooks": {"internal": {"handlers": "not a list"}}}
        assert get_legacy_internal_hook_handlers(config) == []

    def test_non_dict(self):
        assert get_legacy_internal_hook_handlers(None) == []
        assert get_legacy_internal_hook_handlers("string") == []


class TestInstalls:
    def test_record_new_install(self):
        cfg = {}
        result = record_hook_install(cfg, {"hookId": "my-hook", "version": "1.0"})
        assert result["hooks"]["internal"]["installs"]["my-hook"]["version"] == "1.0"
        assert "installedAt" in result["hooks"]["internal"]["installs"]["my-hook"]

    def test_record_with_explicit_timestamp(self):
        cfg = {}
        result = record_hook_install(cfg, {
            "hookId": "my-hook",
            "installedAt": "2025-01-01T00:00:00Z",
        })
        assert result["hooks"]["internal"]["installs"]["my-hook"]["installedAt"] == "2025-01-01T00:00:00Z"

    def test_record_preserves_existing(self):
        cfg = {
            "hooks": {
                "internal": {
                    "installs": {"existing": {"version": "0.9"}}
                }
            }
        }
        result = record_hook_install(cfg, {"hookId": "new-hook", "version": "1.0"})
        assert "existing" in result["hooks"]["internal"]["installs"]
        assert "new-hook" in result["hooks"]["internal"]["installs"]

    def test_record_merges_existing(self):
        cfg = {
            "hooks": {
                "internal": {
                    "installs": {"my-hook": {"version": "0.9", "source": "npm"}}
                }
            }
        }
        result = record_hook_install(cfg, {"hookId": "my-hook", "version": "1.0"})
        install = result["hooks"]["internal"]["installs"]["my-hook"]
        assert install["version"] == "1.0"
        assert install["source"] == "npm"

    def test_does_not_mutate_original(self):
        cfg = {}
        record_hook_install(cfg, {"hookId": "my-hook"})
        assert cfg == {}
