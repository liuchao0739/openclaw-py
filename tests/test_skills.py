"""Tests for skills config and research modules."""

from openclaw.skills.config.mutations import patch_skill_config_entry, REDACTED_SENTINEL
from openclaw.skills.research.text import extract_transcript_text, compact_whitespace


class TestPatchSkillConfigEntry:
    def test_enable_skill(self):
        cfg = {"skills": {"entries": {"my-skill": {"enabled": False}}}}
        result = patch_skill_config_entry(cfg, "my-skill", {"enabled": True})
        assert result["skills"]["entries"]["my-skill"]["enabled"] is True

    def test_new_skill(self):
        cfg = {}
        result = patch_skill_config_entry(cfg, "new-skill", {"enabled": True})
        assert result["skills"]["entries"]["new-skill"]["enabled"] is True

    def test_set_api_key(self):
        cfg = {}
        result = patch_skill_config_entry(cfg, "s", {"apiKey": "secret123"})
        assert result["skills"]["entries"]["s"]["apiKey"] == "secret123"

    def test_redacted_api_key_preserved(self):
        cfg = {"skills": {"entries": {"s": {"apiKey": "existing"}}}}
        result = patch_skill_config_entry(cfg, "s", {"apiKey": REDACTED_SENTINEL})
        assert result["skills"]["entries"]["s"]["apiKey"] == "existing"

    def test_empty_api_key_removed(self):
        cfg = {"skills": {"entries": {"s": {"apiKey": "existing"}}}}
        result = patch_skill_config_entry(cfg, "s", {"apiKey": "  "})
        assert "apiKey" not in result["skills"]["entries"]["s"]

    def test_env_merge(self):
        cfg = {"skills": {"entries": {"s": {"env": {"A": "1"}}}}}
        result = patch_skill_config_entry(cfg, "s", {"env": {"B": "2"}})
        assert result["skills"]["entries"]["s"]["env"]["A"] == "1"
        assert result["skills"]["entries"]["s"]["env"]["B"] == "2"

    def test_env_remove_empty(self):
        cfg = {"skills": {"entries": {"s": {"env": {"A": "1"}}}}}
        result = patch_skill_config_entry(cfg, "s", {"env": {"A": "  "}})
        assert "A" not in result["skills"]["entries"]["s"]["env"]

    def test_env_redacted_preserved(self):
        cfg = {"skills": {"entries": {"s": {"env": {"A": "1"}}}}}
        result = patch_skill_config_entry(cfg, "s", {"env": {"A": REDACTED_SENTINEL}})
        assert result["skills"]["entries"]["s"]["env"]["A"] == "1"

    def test_does_not_mutate_original(self):
        cfg = {"skills": {"entries": {"s": {"enabled": False}}}}
        patch_skill_config_entry(cfg, "s", {"enabled": True})
        assert cfg["skills"]["entries"]["s"]["enabled"] is False


class TestExtractTranscriptText:
    def test_string_content(self):
        messages = [{"role": "user", "content": "hello"}]
        result = extract_transcript_text(messages)
        assert len(result) == 1
        assert result[0] == {"role": "user", "text": "hello"}

    def test_typed_text_blocks(self):
        messages = [{"role": "assistant", "content": [{"type": "text", "text": "hi"}]}]
        result = extract_transcript_text(messages)
        assert result[0]["text"] == "hi"

    def test_filters_non_text_blocks(self):
        messages = [{"role": "assistant", "content": [{"type": "image", "text": "x"}, {"type": "text", "text": "y"}]}]
        result = extract_transcript_text(messages)
        assert result[0]["text"] == "y"

    def test_skips_no_role(self):
        messages = [{"content": "x"}]
        assert extract_transcript_text(messages) == []

    def test_skips_empty_text(self):
        messages = [{"role": "user", "content": "   "}]
        assert extract_transcript_text(messages) == []

    def test_input_text_block_type(self):
        messages = [{"role": "user", "content": [{"type": "input_text", "text": "in"}]}]
        result = extract_transcript_text(messages)
        assert result[0]["text"] == "in"


class TestCompactWhitespace:
    def test_basic(self):
        assert compact_whitespace("hello   world") == "hello world"

    def test_newlines(self):
        assert compact_whitespace("hello\n\nworld") == "hello world"

    def test_tabs(self):
        assert compact_whitespace("hello\t\tworld") == "hello world"

    def test_trims(self):
        assert compact_whitespace("  hello  ") == "hello"

    def test_empty(self):
        assert compact_whitespace("") == ""

    def test_non_string(self):
        assert compact_whitespace(123) == ""
