"""Tests for agents/harness tool-result middleware and native hook relay."""

from __future__ import annotations

import pytest

from openclaw.agents.harness.native_hook_relay import (
    clear_native_hook_relays_for_tests,
    get_native_hook_relay_invocations_for_tests,
    get_native_hook_relay_registration_for_tests,
    has_native_hook_relay_invocation,
    register_native_hook_relay,
)
from openclaw.agents.harness.tool_result_middleware import (
    build_middleware_failure_result,
    create_agent_tool_result_middleware_runner,
    is_valid_middleware_content_block,
    is_valid_middleware_details,
    is_valid_middleware_tool_result,
    sanitize_middleware_details_value,
)


@pytest.fixture(autouse=True)
def _clean_relays():
    clear_native_hook_relays_for_tests()
    yield
    clear_native_hook_relays_for_tests()


class TestMiddlewareValidation:
    def test_valid_text_block(self):
        assert is_valid_middleware_content_block({"type": "text", "text": "hello"})

    def test_invalid_text_block_missing_text(self):
        assert not is_valid_middleware_content_block({"type": "text"})

    def test_valid_image_block(self):
        assert is_valid_middleware_content_block(
            {"type": "image", "mimeType": "image/png", "data": "base64data"}
        )

    def test_invalid_block_type(self):
        assert not is_valid_middleware_content_block({"type": "unknown", "data": "x"})

    def test_valid_details_none(self):
        assert is_valid_middleware_details(None)

    def test_valid_details_string(self):
        assert is_valid_middleware_details("hello")

    def test_valid_details_nested(self):
        assert is_valid_middleware_details({"a": {"b": [1, 2, 3]}})

    def test_valid_tool_result(self):
        result = {
            "content": [{"type": "text", "text": "output"}],
            "details": {"status": "ok"},
        }
        assert is_valid_middleware_tool_result(result)

    def test_invalid_tool_result_no_content(self):
        assert not is_valid_middleware_tool_result({"details": {}})

    def test_invalid_tool_result_oversized_content(self):
        result = {
            "content": [{"type": "text", "text": "x"} for _ in range(201)],
        }
        assert not is_valid_middleware_tool_result(result)


class TestMiddlewareRunner:
    async def test_no_handlers_returns_result_unchanged(self):
        runner = create_agent_tool_result_middleware_runner({"runtime": "openclaw"}, [])
        event = {"result": {"content": [], "details": None}, "toolName": "exec"}
        out = await runner.apply_tool_result_middleware(event)
        assert out is event["result"]

    async def test_handler_chain(self):
        async def handler(event, ctx):
            return {"result": {**event["result"], "content": [{"type": "text", "text": "modified"}]}}

        runner = create_agent_tool_result_middleware_runner({"runtime": "codex"}, [handler])
        event = {
            "result": {"content": [{"type": "text", "text": "original"}], "details": None},
            "toolName": "exec",
        }
        out = await runner.apply_tool_result_middleware(event)
        assert out["content"][0]["text"] == "modified"

    async def test_failure_returns_middleware_failure_result(self):
        async def bad_handler(event, ctx):
            raise RuntimeError("boom")

        runner = create_agent_tool_result_middleware_runner({"runtime": "codex"}, [bad_handler])
        event = {
            "result": {"content": [{"type": "text", "text": "x"}], "details": None},
            "toolName": "exec",
        }
        out = await runner.apply_tool_result_middleware(event)
        assert out == build_middleware_failure_result()


class TestSanitizeDetails:
    def test_round_trip_simple(self):
        assert sanitize_middleware_details_value({"a": 1}) == {"a": 1}

    def test_truncates_large(self):
        large = "x" * 200_000
        result = sanitize_middleware_details_value(large)
        assert isinstance(result, dict)
        assert result.get("truncated") is True


class TestNativeHookRelay:
    def test_register_and_query(self):
        handle = register_native_hook_relay(
            {"provider": "codex", "sessionId": "s1", "runId": "r1"}
        )
        assert handle["relayId"]
        assert handle["provider"] == "codex"
        reg = get_native_hook_relay_registration_for_tests(handle["relayId"])
        assert reg is not None
        assert reg["sessionId"] == "s1"

    def test_should_relay_event(self):
        handle = register_native_hook_relay(
            {"provider": "codex", "sessionId": "s1", "runId": "r1"}
        )
        assert handle["shouldRelayEvent"]("pre_tool_use") is True
        assert handle["shouldRelayEvent"]("unknown_event") is False

    def test_unregister(self):
        handle = register_native_hook_relay(
            {"provider": "codex", "sessionId": "s1", "runId": "r1"}
        )
        handle["unregister"]()
        assert get_native_hook_relay_registration_for_tests(handle["relayId"]) is None

    def test_has_invocation_false_when_empty(self):
        assert has_native_hook_relay_invocation(
            {"relayId": "x", "event": "pre_tool_use", "toolUseId": "t1"}
        ) is False

    def test_custom_relay_id(self):
        handle = register_native_hook_relay(
            {"provider": "codex", "sessionId": "s1", "runId": "r1", "relayId": "my-relay-1"}
        )
        assert handle["relayId"] == "my-relay-1"

    def test_invalid_relay_id_raises(self):
        with pytest.raises(ValueError):
            register_native_hook_relay(
                {"provider": "codex", "sessionId": "s1", "runId": "r1", "relayId": "bad relay id!"}
            )
