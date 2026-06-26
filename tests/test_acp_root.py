"""Tests for ACP root modules."""

import os
import tempfile

from openclaw.acp.conversation_id import normalize_conversation_text
from openclaw.acp.types import ACP_AGENT_INFO, normalize_acp_provenance_mode
from openclaw.acp.secret_file import read_secret_from_file, MAX_SECRET_FILE_BYTES
from openclaw.acp.commands import BASE_AVAILABLE_COMMANDS, get_available_commands, register_dock_command


class TestNormalizeConversationText:
    def test_string(self):
        assert normalize_conversation_text("  hello  ") == "hello"

    def test_int(self):
        assert normalize_conversation_text(42) == "42"

    def test_bool(self):
        assert normalize_conversation_text(True) == "True"

    def test_none(self):
        assert normalize_conversation_text(None) == ""

    def test_object(self):
        assert normalize_conversation_text({"a": 1}) == ""


class TestAcpTypes:
    def test_agent_info(self):
        assert ACP_AGENT_INFO["name"] == "openclaw-acp"
        assert "version" in ACP_AGENT_INFO

    def test_provenance_off(self):
        assert normalize_acp_provenance_mode("off") == "off"
        assert normalize_acp_provenance_mode(None) == "off"

    def test_provenance_on(self):
        assert normalize_acp_provenance_mode("on") == "on"
        assert normalize_acp_provenance_mode("always") == "on"

    def test_provenance_auto(self):
        assert normalize_acp_provenance_mode("auto") == "auto"

    def test_provenance_invalid(self):
        assert normalize_acp_provenance_mode("bogus") == "off"


class TestSecretFile:
    def test_read(self, tmp_path):
        f = tmp_path / "secret.txt"
        f.write_text("my-secret\n")
        assert read_secret_from_file(str(f), "test") == "my-secret"

    def test_not_found(self):
        try:
            read_secret_from_file("/nonexistent", "test")
            assert False
        except FileNotFoundError:
            pass

    def test_too_large(self, tmp_path):
        f = tmp_path / "big.txt"
        f.write_text("x" * (MAX_SECRET_FILE_BYTES + 1))
        try:
            read_secret_from_file(str(f), "test")
            assert False
        except ValueError:
            pass

    def test_symlink_rejected(self, tmp_path):
        target = tmp_path / "target.txt"
        target.write_text("secret")
        link = tmp_path / "link.txt"
        os.symlink(target, link)
        try:
            read_secret_from_file(str(link), "test")
            assert False
        except ValueError:
            pass


class TestCommands:
    def test_base_commands(self):
        names = [c["name"] for c in BASE_AVAILABLE_COMMANDS]
        assert "help" in names
        assert "model" in names

    def test_get_available_commands(self):
        cmds = get_available_commands()
        assert len(cmds) >= len(BASE_AVAILABLE_COMMANDS)

    def test_register_dock(self):
        register_dock_command("dock:test", "Test dock command")
        cmds = get_available_commands()
        assert any(c["name"] == "dock:test" for c in cmds)
