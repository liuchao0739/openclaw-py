"""Tests for auto_reply root — heartbeat, sender identity, send policy, group activation, model directive."""

from __future__ import annotations

from openclaw.auto_reply.group_activation import (
    normalize_group_activation,
    parse_activation_command,
)
from openclaw.auto_reply.heartbeat_reply_payload import (
    has_outbound_reply_content,
    resolve_heartbeat_reply_payload,
)
from openclaw.auto_reply.model import extract_model_directive
from openclaw.auto_reply.send_policy import parse_send_policy_command
from openclaw.auto_reply.sender_identity import should_use_from_as_sender_fallback


class TestHeartbeatReplyPayload:
    def test_none(self):
        assert resolve_heartbeat_reply_payload(None) is None

    def test_single_payload(self):
        payload = {"text": "hello"}
        assert resolve_heartbeat_reply_payload(payload) == payload

    def test_list_returns_last_with_content(self):
        payloads = [{"text": ""}, {"text": "second"}, {"text": "third"}]
        result = resolve_heartbeat_reply_payload(payloads)
        assert result["text"] == "third"

    def test_list_no_content(self):
        payloads = [{"text": ""}, {}]
        assert resolve_heartbeat_reply_payload(payloads) is None

    def test_has_outbound_content(self):
        assert has_outbound_reply_content({"text": "hello"}) is True
        assert has_outbound_reply_content({"text": ""}) is False
        assert has_outbound_reply_content({"content": [{"type": "text"}]}) is True
        assert has_outbound_reply_content({}) is False


class TestSenderIdentity:
    def test_direct_chat_from(self):
        assert should_use_from_as_sender_fallback({"from": "user123", "chatType": "direct"}) is True

    def test_group_chat(self):
        assert should_use_from_as_sender_fallback({"from": "user123", "chatType": "group"}) is False

    def test_conversation_like_identity(self):
        assert should_use_from_as_sender_fallback({"from": "chat_id:123", "chatType": "direct"}) is False
        assert should_use_from_as_sender_fallback({"from": "channel:abc", "chatType": "direct"}) is False

    def test_empty_from(self):
        assert should_use_from_as_sender_fallback({"from": "", "chatType": "direct"}) is False
        assert should_use_from_as_sender_fallback({}) is False

    def test_no_chat_type(self):
        assert should_use_from_as_sender_fallback({"from": "user123"}) is True


class TestSendPolicy:
    def test_no_command(self):
        result = parse_send_policy_command("hello world")
        assert result["hasCommand"] is False

    def test_allow(self):
        result = parse_send_policy_command("/send allow")
        assert result["hasCommand"] is True
        assert result["mode"] == "allow"

    def test_deny(self):
        result = parse_send_policy_command("/send deny")
        assert result["hasCommand"] is True
        assert result["mode"] == "deny"

    def test_on_off_aliases(self):
        assert parse_send_policy_command("/send on")["mode"] == "allow"
        assert parse_send_policy_command("/send off")["mode"] == "deny"

    def test_inherit(self):
        result = parse_send_policy_command("/send inherit")
        assert result["mode"] == "inherit"

    def test_no_mode(self):
        result = parse_send_policy_command("/send")
        assert result["hasCommand"] is True
        assert "mode" not in result

    def test_empty(self):
        assert parse_send_policy_command("")["hasCommand"] is False
        assert parse_send_policy_command(None)["hasCommand"] is False


class TestGroupActivation:
    def test_normalize(self):
        assert normalize_group_activation("mention") == "mention"
        assert normalize_group_activation("always") == "always"
        assert normalize_group_activation("invalid") is None
        assert normalize_group_activation(None) is None

    def test_parse_mention(self):
        result = parse_activation_command("/activation mention")
        assert result["hasCommand"] is True
        assert result["mode"] == "mention"

    def test_parse_always(self):
        result = parse_activation_command("/activation always")
        assert result["hasCommand"] is True
        assert result["mode"] == "always"

    def test_parse_no_mode(self):
        result = parse_activation_command("/activation")
        assert result["hasCommand"] is True
        assert result.get("mode") is None

    def test_parse_no_command(self):
        assert parse_activation_command("hello")["hasCommand"] is False
        assert parse_activation_command("")["hasCommand"] is False

    def test_parse_colon_syntax(self):
        result = parse_activation_command("/activation: mention")
        assert result["hasCommand"] is True
        assert result["mode"] == "mention"


class TestModelDirective:
    def test_no_directive(self):
        result = extract_model_directive("hello world")
        assert result["hasDirective"] is False
        assert result["cleaned"] == "hello world"

    def test_empty(self):
        result = extract_model_directive(None)
        assert result["hasDirective"] is False

    def test_model_directive(self):
        result = extract_model_directive("hello /model gpt-4 world")
        assert result["hasDirective"] is True
        assert result["rawModel"] == "gpt-4"
        assert "hello" in result["cleaned"]
        assert "world" in result["cleaned"]

    def test_model_with_profile(self):
        result = extract_model_directive("/model gpt-4@myprofile")
        assert result["rawModel"] == "gpt-4"
        assert result["rawProfile"] == "myprofile"

    def test_model_with_provider(self):
        result = extract_model_directive("/model openai/gpt-4")
        assert result["rawModel"] == "openai/gpt-4"

    def test_model_with_runtime(self):
        result = extract_model_directive("/model gpt-4 --runtime codex")
        assert result["rawModel"] == "gpt-4"
        assert result["rawRuntime"] == "codex"

    def test_model_no_ref(self):
        result = extract_model_directive("/model do something")
        assert result["hasDirective"] is True
        assert result["rawModel"] == "do"

    def test_alias(self):
        result = extract_model_directive("/gpt hello", {"aliases": ["gpt"]})
        assert result["hasDirective"] is True
