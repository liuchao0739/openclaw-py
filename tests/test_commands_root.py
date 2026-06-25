"""Tests for commands root — barrel stubs."""

from __future__ import annotations

from openclaw.commands.auth_token import (
    ANTHROPIC_SETUP_TOKEN_PREFIX,
    validate_anthropic_setup_token,
)
from openclaw.commands.model_picker import apply_primary_model
from openclaw.commands.status import get_status_summary, status_command


class TestAuthToken:
    def test_prefix(self):
        assert ANTHROPIC_SETUP_TOKEN_PREFIX == "sk-ant-setup"

    def test_validate_valid_prefix(self):
        assert validate_anthropic_setup_token("sk-ant-setup-12345") is True

    def test_validate_invalid(self):
        assert validate_anthropic_setup_token("invalid") is False
        assert validate_anthropic_setup_token("") is False


class TestStatusBarrel:
    async def test_status_command_stub(self):
        result = await status_command({})
        assert result["ok"] is False

    def test_get_status_summary_stub(self):
        result = get_status_summary()
        assert result["ok"] is False


class TestModelPickerBarrel:
    def test_not_implemented(self):
        import pytest

        with pytest.raises(NotImplementedError):
            apply_primary_model()
