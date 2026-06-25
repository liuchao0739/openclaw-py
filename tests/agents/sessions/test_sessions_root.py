"""Tests for agents/sessions root — event bus, source info, diagnostics, config, auth, slash commands."""

from __future__ import annotations

import os

import pytest

from openclaw.agents.sessions.auth_guidance import get_auth_guidance, register_auth_guidance
from openclaw.agents.sessions.defaults import DEFAULT_THINKING_LEVEL
from openclaw.agents.sessions.diagnostics import (
    create_diagnostic,
    is_error,
    is_info,
    is_warning,
)
from openclaw.agents.sessions.event_bus import create_event_bus
from openclaw.agents.sessions.messages import convert_to_llm
from openclaw.agents.sessions.provider_display_names import (
    get_provider_display_name,
    register_provider_display_name,
)
from openclaw.agents.sessions.resolve_config_value import (
    resolve_config_value,
    resolve_optional_config_value,
)
from openclaw.agents.sessions.session_cwd import detect_missing_session_cwd
from openclaw.agents.sessions.slash_commands import (
    create_slash_command_info,
    is_builtin_command,
    is_extension_command,
)
from openclaw.agents.sessions.source_info import (
    create_source_info,
    create_synthetic_source_info,
)


class TestEventBus:
    def test_emit_and_on(self):
        bus = create_event_bus()
        received = []
        bus.on("test", lambda data: received.append(data))
        bus.emit("test", {"msg": "hello"})
        assert received == [{"msg": "hello"}]

    def test_unsubscribe(self):
        bus = create_event_bus()
        received = []
        unsub = bus.on("test", lambda data: received.append(data))
        bus.emit("test", "first")
        unsub()
        bus.emit("test", "second")
        assert received == ["first"]

    def test_handler_isolation(self):
        bus = create_event_bus()
        received = []
        bus.on("test", lambda data: (_ for _ in ()).throw(ValueError("boom")))
        bus.on("test", lambda data: received.append(data))
        bus.emit("test", "hello")
        assert received == ["hello"]

    def test_clear(self):
        bus = create_event_bus()
        received = []
        bus.on("test", lambda data: received.append(data))
        bus.clear()
        bus.emit("test", "hello")
        assert received == []


class TestSourceInfo:
    def test_create_source_info(self):
        metadata = {"source": "package", "scope": "user", "origin": "package", "baseDir": "/tmp"}
        info = create_source_info("/path/to/file", metadata)
        assert info["path"] == "/path/to/file"
        assert info["source"] == "package"
        assert info["scope"] == "user"

    def test_create_synthetic_source_info(self):
        info = create_synthetic_source_info("<inline>", {"source": "test"})
        assert info["path"] == "<inline>"
        assert info["source"] == "test"
        assert info["scope"] == "temporary"

    def test_create_synthetic_source_info_with_options(self):
        info = create_synthetic_source_info("/path", {"source": "ext", "scope": "project", "origin": "package"})
        assert info["scope"] == "project"
        assert info["origin"] == "package"


class TestDiagnostics:
    def test_create_diagnostic(self):
        diag = create_diagnostic("warning", "test message", "/path")
        assert diag["type"] == "warning"
        assert diag["message"] == "test message"
        assert diag["path"] == "/path"

    def test_is_warning(self):
        diag = create_diagnostic("warning", "test")
        assert is_warning(diag) is True
        assert is_error(diag) is False
        assert is_info(diag) is False

    def test_is_error(self):
        diag = create_diagnostic("error", "test")
        assert is_error(diag) is True
        assert is_warning(diag) is False


class TestProviderDisplayNames:
    def test_known_provider(self):
        assert get_provider_display_name("openai") == "OpenAI"
        assert get_provider_display_name("anthropic") == "Anthropic"

    def test_unknown_provider(self):
        assert get_provider_display_name("unknown") == "unknown"

    def test_none_provider(self):
        assert get_provider_display_name(None) == "Unknown"

    def test_register_override(self):
        register_provider_display_name("custom", "Custom Provider")
        assert get_provider_display_name("custom") == "Custom Provider"


class TestResolveConfigValue:
    def test_passthrough(self):
        assert resolve_config_value(42) == 42
        assert resolve_config_value("hello") == "hello"

    def test_env_var(self):
        env = {"MY_VAR": "env_value"}
        assert resolve_config_value("env:MY_VAR", env=env) == "env_value"

    def test_env_var_missing(self):
        assert resolve_config_value("env:MISSING", env={}) == ""

    def test_callable(self):
        assert resolve_config_value(lambda: "computed") == "computed"

    def test_optional_with_default(self):
        assert resolve_optional_config_value(None, "default") == "default"
        assert resolve_optional_config_value("", "default") == "default"
        assert resolve_optional_config_value("value", "default") == "value"


class TestAuthGuidance:
    def test_known_provider(self):
        guidance = get_auth_guidance("openai")
        assert guidance is not None
        assert guidance["provider"] == "openai"
        assert "OPENAI_API_KEY" in guidance["envVar"]

    def test_unknown_provider(self):
        assert get_auth_guidance("unknown") is None
        assert get_auth_guidance(None) is None

    def test_register(self):
        register_auth_guidance("custom", {"provider": "custom", "message": "test"})
        guidance = get_auth_guidance("custom")
        assert guidance["message"] == "test"


class TestSlashCommands:
    def test_create_builtin(self):
        cmd = create_slash_command_info("help", "Show help")
        assert cmd["name"] == "help"
        assert cmd["source"] == "builtin"
        assert is_builtin_command(cmd) is True
        assert is_extension_command(cmd) is False

    def test_create_extension(self):
        cmd = create_slash_command_info("custom", "Custom command", source="extension")
        assert is_extension_command(cmd) is True
        assert is_builtin_command(cmd) is False


class TestMessages:
    def test_convert_to_llm_passthrough(self):
        messages = [{"role": "user", "content": "hello"}]
        result = convert_to_llm(messages)
        assert result == messages


class TestSessionCwd:
    def test_missing_cwd(self):
        source = {"getCwd": lambda: "/nonexistent/path", "getSessionFile": lambda: "/tmp/session.jsonl"}
        result = detect_missing_session_cwd(source, "/tmp")
        assert result is not None
        assert result["sessionCwd"] == "/nonexistent/path"
        assert result["fallbackCwd"] == "/tmp"

    def test_valid_cwd(self):
        source = {"getCwd": lambda: os.path.expanduser("~"), "getSessionFile": lambda: None}
        result = detect_missing_session_cwd(source, "/tmp")
        assert result is None

    def test_empty_cwd(self):
        source = {"getCwd": lambda: "", "getSessionFile": lambda: None}
        result = detect_missing_session_cwd(source, "/tmp")
        assert result is not None
        assert result["sessionCwd"] == ""


class TestDefaults:
    def test_default_thinking_level(self):
        assert DEFAULT_THINKING_LEVEL == "medium"
