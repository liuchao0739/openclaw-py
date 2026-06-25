"""Tests for agents/tools — common, web_shared, sessions_helpers, model_config, tokens, nodes, chat history."""

from __future__ import annotations

import pytest

from openclaw.agents.tools.chat_history_text import (
    extract_text_from_content,
    format_chat_history,
    format_chat_history_entry,
)
from openclaw.agents.tools.common import (
    ToolAuthorizationError,
    ToolInputError,
    as_tool_params_record,
    create_action_gate,
    json_error_result,
    json_text_result,
    read_array_param,
    read_boolean_param,
    read_number_param,
    read_optional_string_param,
    read_string_param,
)
from openclaw.agents.tools.manifest_capability_availability import (
    filter_available_tools,
    get_available_capabilities,
    has_capability,
    is_tool_available,
)
from openclaw.agents.tools.model_config_helpers import (
    get_api_key_env_var,
    resolve_api_key,
    resolve_model_config,
)
from openclaw.agents.tools.nodes_utils import (
    filter_nodes_by_platform,
    format_node_display_name,
    is_valid_node_id,
    resolve_node_by_id,
)
from openclaw.agents.tools.session_message_text import (
    extract_session_message_text,
    get_message_tool_calls,
    is_assistant_message,
    is_tool_result_message,
)
from openclaw.agents.tools.sessions_helpers import (
    format_session_display_name,
    is_valid_session_key,
    parse_session_key,
    resolve_session_target,
)
from openclaw.agents.tools.sessions_send_tokens import (
    estimate_message_tokens,
    estimate_tokens,
    is_within_send_limit,
    truncate_messages_to_limit,
)
from openclaw.agents.tools.web_search_provider_config import (
    get_web_search_provider_config,
    list_web_search_providers,
)
from openclaw.agents.tools.web_shared import (
    format_web_fetch_result,
    format_web_search_result,
    is_valid_url,
    normalize_url,
    truncate_web_content,
)


class TestCommon:
    def test_as_tool_params_record_dict(self):
        assert as_tool_params_record({"a": 1}) == {"a": 1}

    def test_as_tool_params_record_non_dict(self):
        assert as_tool_params_record(None) == {}
        assert as_tool_params_record([1, 2]) == {}
        assert as_tool_params_record("hello") == {}

    def test_read_string_param_required(self):
        with pytest.raises(ToolInputError, match="required"):
            read_string_param({}, "name", required=True)

    def test_read_string_param_present(self):
        assert read_string_param({"name": "hello"}, "name") == "hello"

    def test_read_string_param_snake_case(self):
        assert read_string_param({"session_id": "123"}, "sessionId") == "123"

    def test_read_string_param_optional(self):
        assert read_optional_string_param({}, "name") is None
        assert read_optional_string_param({"name": "  x  "}, "name") == "x"

    def test_read_number_param(self):
        assert read_number_param({"count": 42}, "count") == 42
        assert read_number_param({"count": "100"}, "count") == 100
        assert read_number_param({}, "count") is None

    def test_read_number_param_with_range(self):
        assert read_number_param({"n": 5}, "n", min_value=1, max_value=10) == 5
        with pytest.raises(ToolInputError, match="must be >="):
            read_number_param({"n": 0}, "n", min_value=1)
        with pytest.raises(ToolInputError, match="must be <="):
            read_number_param({"n": 20}, "n", max_value=10)

    def test_read_boolean_param(self):
        assert read_boolean_param({"flag": True}, "flag") is True
        assert read_boolean_param({"flag": "true"}, "flag") is True
        assert read_boolean_param({"flag": 1}, "flag") is True
        assert read_boolean_param({}, "flag", default=False) is False

    def test_read_array_param(self):
        assert read_array_param({"items": [1, 2, 3]}, "items") == [1, 2, 3]
        assert read_array_param({}, "items") == []

    def test_create_action_gate(self):
        gate = create_action_gate({"read": True, "write": False})
        assert gate("read") is True
        assert gate("write") is False
        assert gate("execute") is True  # default

    def test_create_action_gate_none(self):
        gate = create_action_gate(None)
        assert gate("anything") is True

    def test_json_text_result(self):
        result = json_text_result("hello")
        assert result["content"][0]["text"] == "hello"

    def test_json_error_result(self):
        result = json_error_result("failed")
        assert result["isError"] is True
        assert "failed" in result["content"][0]["text"]

    def test_tool_authorization_error(self):
        err = ToolAuthorizationError("denied")
        assert err.status == 403


class TestWebShared:
    def test_is_valid_url(self):
        assert is_valid_url("https://example.com")
        assert is_valid_url("http://localhost:8080")
        assert not is_valid_url("ftp://example.com")
        assert not is_valid_url("not a url")
        assert not is_valid_url(None)

    def test_normalize_url(self):
        assert normalize_url("example.com") == "https://example.com"
        assert normalize_url("http://example.com") == "http://example.com"

    def test_truncate_web_content(self):
        short = "hello"
        assert truncate_web_content(short) == short
        long = "x" * 200_000
        result = truncate_web_content(long, 100)
        assert len(result) <= 200
        assert "[Content truncated]" in result

    def test_format_web_fetch_result(self):
        result = format_web_fetch_result("https://example.com", "content", title="Example")
        text = result["content"][0]["text"]
        assert "https://example.com" in text
        assert "Example" in text

    def test_format_web_search_result(self):
        results = [
            {"title": "Test", "url": "https://test.com", "snippet": "snippet"},
        ]
        result = format_web_search_result(results)
        text = result["content"][0]["text"]
        assert "Test" in text
        assert "https://test.com" in text


class TestSessionsHelpers:
    def test_resolve_session_target(self):
        target = resolve_session_target({"sessionId": "s1", "agentId": "a1"})
        assert target["sessionId"] == "s1"
        assert target["agentId"] == "a1"

    def test_is_valid_session_key(self):
        assert is_valid_session_key("agent:main:telegram")
        assert is_valid_session_key("global:something")
        assert not is_valid_session_key("invalid")
        assert not is_valid_session_key(None)

    def test_parse_session_key(self):
        parsed = parse_session_key("agent:main:telegram:group:test")
        assert parsed["agentId"] == "main"
        assert parsed["channel"] == "telegram"

    def test_format_session_display_name(self):
        assert format_session_display_name("main", "telegram", "test") == "main/telegram/test"
        assert format_session_display_name() == "default"


class TestModelConfigHelpers:
    def test_resolve_model_config(self):
        config = {"models": {"providers": {"openai": {"baseUrl": "https://api.openai.com"}}}}
        result = resolve_model_config("openai", None, config)
        assert result["baseUrl"] == "https://api.openai.com"

    def test_resolve_model_config_missing(self):
        assert resolve_model_config("unknown", None, {}) is None
        assert resolve_model_config(None, None, None) is None

    def test_get_api_key_env_var(self):
        assert get_api_key_env_var("openai") == "OPENAI_API_KEY"
        assert get_api_key_env_var("unknown") is None

    def test_resolve_api_key_from_config(self):
        config = {"models": {"providers": {"openai": {"apiKey": "config-key"}}}}
        assert resolve_api_key("openai", config) == "config-key"

    def test_resolve_api_key_from_env(self):
        assert resolve_api_key("openai", None, env={"OPENAI_API_KEY": "env-key"}) == "env-key"


class TestSessionsSendTokens:
    def test_estimate_tokens(self):
        assert estimate_tokens("") == 0
        assert estimate_tokens("hello") == 2  # 5 chars / 4 = 1.25 -> 2

    def test_estimate_message_tokens_string(self):
        msg = {"content": "hello world"}
        assert estimate_message_tokens(msg) > 0

    def test_estimate_message_tokens_blocks(self):
        msg = {"content": [{"type": "text", "text": "hello"}]}
        assert estimate_message_tokens(msg) > 0

    def test_is_within_send_limit(self):
        msgs = [{"content": "short"}]
        assert is_within_send_limit(msgs, max_tokens=1000)

    def test_truncate_messages_to_limit(self):
        msgs = [{"content": "x" * 100} for _ in range(10)]
        result = truncate_messages_to_limit(msgs, max_tokens=50)
        assert len(result) < 10


class TestNodesUtils:
    def test_format_node_display_name(self):
        assert format_node_display_name({"name": "Node1", "platform": "linux"}) == "Node1 (linux)"
        assert format_node_display_name({"name": "Node1"}) == "Node1"
        assert format_node_display_name({}) == "Unknown"

    def test_is_valid_node_id(self):
        assert is_valid_node_id("node-1")
        assert not is_valid_node_id("")
        assert not is_valid_node_id(None)

    def test_resolve_node_by_id(self):
        nodes = [{"id": "n1", "name": "Node1"}, {"id": "n2", "name": "Node2"}]
        assert resolve_node_by_id(nodes, "n1")["name"] == "Node1"
        assert resolve_node_by_id(nodes, "n3") is None

    def test_filter_nodes_by_platform(self):
        nodes = [
            {"id": "n1", "platform": "linux"},
            {"id": "n2", "platform": "darwin"},
        ]
        result = filter_nodes_by_platform(nodes, "linux")
        assert len(result) == 1
        assert result[0]["id"] == "n1"


class TestChatHistoryText:
    def test_format_entry_string_content(self):
        entry = {"role": "user", "content": "hello"}
        assert format_chat_history_entry(entry) == "[user] hello"

    def test_format_entry_blocks_content(self):
        entry = {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}
        assert "[assistant]" in format_chat_history_entry(entry)
        assert "hi" in format_chat_history_entry(entry)

    def test_format_chat_history(self):
        entries = [{"role": "user", "content": str(i)} for i in range(5)]
        result = format_chat_history(entries, max_entries=3)
        assert "omitted" in result

    def test_extract_text_from_content(self):
        assert extract_text_from_content("hello") == "hello"
        assert extract_text_from_content([{"type": "text", "text": "world"}]) == "world"


class TestSessionMessageText:
    def test_extract_string_content(self):
        assert extract_session_message_text({"content": "hello"}) == "hello"

    def test_extract_blocks_content(self):
        msg = {"content": [{"type": "text", "text": "hello"}, {"type": "toolCall", "name": "bash"}]}
        result = extract_session_message_text(msg)
        assert "hello" in result
        assert "tool: bash" in result

    def test_is_assistant_message(self):
        assert is_assistant_message({"role": "assistant"})
        assert not is_assistant_message({"role": "user"})

    def test_get_message_tool_calls(self):
        msg = {"content": [{"type": "text", "text": "hi"}, {"type": "toolCall", "name": "bash"}]}
        calls = get_message_tool_calls(msg)
        assert len(calls) == 1
        assert calls[0]["name"] == "bash"


class TestWebSearchProviderConfig:
    def test_get_config(self):
        config = get_web_search_provider_config("brave")
        assert config is not None
        assert config["displayName"] == "Brave Search"
        assert config["apiKeyEnvVar"] == "BRAVE_API_KEY"

    def test_get_config_unknown(self):
        assert get_web_search_provider_config("unknown") is None
        assert get_web_search_provider_config(None) is None

    def test_list_providers(self):
        providers = list_web_search_providers()
        assert "brave" in providers
        assert "duckduckgo" in providers


class TestManifestCapability:
    def test_has_capability_list(self):
        manifest = {"capabilities": ["read", "write"]}
        assert has_capability(manifest, "read")
        assert not has_capability(manifest, "execute")

    def test_has_capability_dict(self):
        manifest = {"capabilities": {"read": True, "write": False}}
        assert has_capability(manifest, "read")
        assert not has_capability(manifest, "write")

    def test_get_available_capabilities(self):
        manifest = {"capabilities": ["read", "write"]}
        assert set(get_available_capabilities(manifest)) == {"read", "write"}

    def test_is_tool_available(self):
        manifest = {"tools": [{"name": "bash"}, {"name": "read"}]}
        assert is_tool_available(manifest, "bash")
        assert not is_tool_available(manifest, "grep")

    def test_filter_available_tools(self):
        manifest = {"tools": [{"name": "bash"}, {"name": "read"}]}
        result = filter_available_tools(manifest, ["bash", "grep", "read"])
        assert result == ["bash", "read"]
