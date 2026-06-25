"""Tests for commands/migrate — types, context."""

from __future__ import annotations

import re

from openclaw.commands.migrate import (
    build_migration_context,
    build_migration_report_dir,
    create_migration_logger,
)


class TestCreateMigrationLogger:
    def test_basic(self):
        logger = create_migration_logger({"log": print, "error": print})
        assert callable(logger["debug"])
        assert callable(logger["info"])
        assert callable(logger["warn"])
        assert callable(logger["error"])

    def test_json_mode_uses_error_for_info(self):
        errors: list[str] = []
        logger = create_migration_logger({"error": lambda m: errors.append(m)}, json_output=True)
        logger["info"]("test message")
        assert "test message" in errors[0]

    def test_debug_requires_verbose(self):
        messages: list[str] = []
        logger = create_migration_logger({"log": lambda m: messages.append(m)})
        logger["debug"]("debug msg")
        assert messages == []  # Not verbose

    def test_debug_with_verbose(self):
        import os

        os.environ["OPENCLAW_VERBOSE"] = "1"
        try:
            messages: list[str] = []
            logger = create_migration_logger({"log": lambda m: messages.append(m)})
            logger["debug"]("debug msg")
            assert "debug msg" in messages
        finally:
            del os.environ["OPENCLAW_VERBOSE"]


class TestBuildMigrationReportDir:
    def test_path_structure(self):
        result = build_migration_report_dir("anthropic", "/tmp/state", 1700000000000)
        parts = result.replace("\\", "/").split("/")
        assert "migration" in parts
        assert "anthropic" in parts
        # Should contain a timestamp
        stamp = parts[-1]
        assert re.match(r"\d{8}T\d{6}Z", stamp)


class TestBuildMigrationContext:
    def test_basic(self):
        ctx = build_migration_context(
            source="test-source",
            include_secrets=True,
            overwrite=False,
        )
        assert ctx["source"] == "test-source"
        assert ctx["includeSecrets"] is True
        assert ctx["overwrite"] is False
        assert "config" in ctx
        assert "stateDir" in ctx
        assert "logger" in ctx

    def test_with_config_override(self):
        custom_config = {"custom": True}
        ctx = build_migration_context(config_override=custom_config)
        assert ctx["config"] == custom_config

    def test_with_provider_options(self):
        ctx = build_migration_context(provider_options={"key": "value"})
        assert ctx["providerOptions"] == {"key": "value"}

    def test_logger_present(self):
        ctx = build_migration_context()
        assert callable(ctx["logger"]["info"])
        assert callable(ctx["logger"]["error"])
