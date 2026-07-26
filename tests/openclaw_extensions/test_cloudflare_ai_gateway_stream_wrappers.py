"""Tests for Cloudflare AI Gateway stream wrappers."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from openclaw_extensions.cloudflare_ai_gateway.stream_wrappers import (
    create_cloudflare_ai_gateway_anthropic_thinking_prefill_wrapper,
    testing,
    wrap_cloudflare_ai_gateway_provider_stream,
)


def _create_payload_base_stream(payload: dict[str, Any]):
    def base_stream_fn(model: Any, _context: Any, options: dict[str, Any] | None = None):
        if options and options.get("onPayload"):
            options["onPayload"](payload, model)
        return {}

    return base_stream_fn


def _run_wrapper(payload: dict[str, Any]) -> dict[str, Any]:
    wrapper = create_cloudflare_ai_gateway_anthropic_thinking_prefill_wrapper(
        _create_payload_base_stream(payload)
    )
    wrapper(
        {"provider": "cloudflare-ai-gateway", "api": "anthropic-messages"},
        {},
        {},
    )
    return payload


def test_removes_trailing_assistant_prefill_when_thinking_is_enabled() -> None:
    payload = _run_wrapper(
        {
            "thinking": {"type": "enabled", "budget_tokens": 1024},
            "messages": [
                {"role": "user", "content": "Return JSON."},
                {"role": "assistant", "content": "{"},
            ],
        }
    )

    assert payload["messages"] == [{"role": "user", "content": "Return JSON."}]


@patch.object(testing.log, "warning")
def test_logs_single_removed_prefill_message(warn_mock: Any) -> None:
    _run_wrapper(
        {
            "thinking": {"type": "enabled", "budget_tokens": 1024},
            "messages": [
                {"role": "user", "content": "Return JSON."},
                {"role": "assistant", "content": "{"},
            ],
        }
    )

    warn_mock.assert_called_once_with(
        "removed %s trailing assistant prefill message%s because Anthropic extended "
        "thinking requires conversations to end with a user turn",
        1,
        "",
    )


def test_removes_multiple_trailing_assistant_prefill_messages() -> None:
    payload = _run_wrapper(
        {
            "thinking": {"type": "adaptive"},
            "messages": [
                {"role": "user", "content": "Return JSON."},
                {"role": "assistant", "content": "{"},
                {"role": "assistant", "content": '"status"'},
            ],
        }
    )

    assert payload["messages"] == [{"role": "user", "content": "Return JSON."}]


@patch.object(testing.log, "warning")
def test_logs_multiple_removed_prefill_messages(warn_mock: Any) -> None:
    _run_wrapper(
        {
            "thinking": {"type": "adaptive"},
            "messages": [
                {"role": "user", "content": "Return JSON."},
                {"role": "assistant", "content": "{"},
                {"role": "assistant", "content": '"status"'},
            ],
        }
    )

    warn_mock.assert_called_once_with(
        "removed %s trailing assistant prefill message%s because Anthropic extended "
        "thinking requires conversations to end with a user turn",
        2,
        "s",
    )


@patch.object(testing.log, "warning")
def test_keeps_assistant_prefill_when_thinking_is_disabled(warn_mock: Any) -> None:
    payload = _run_wrapper(
        {
            "thinking": {"type": "disabled"},
            "messages": [
                {"role": "user", "content": "Return JSON."},
                {"role": "assistant", "content": "{"},
            ],
        }
    )

    assert len(payload["messages"]) == 2
    warn_mock.assert_not_called()


@patch.object(testing.log, "warning")
def test_keeps_trailing_assistant_tool_use_turns_when_thinking_is_enabled(
    warn_mock: Any,
) -> None:
    payload = _run_wrapper(
        {
            "thinking": {"type": "enabled", "budget_tokens": 1024},
            "messages": [
                {"role": "user", "content": "Read a file."},
                {
                    "role": "assistant",
                    "content": [{"type": "tool_use", "id": "toolu_1", "name": "Read"}],
                },
            ],
        }
    )

    assert len(payload["messages"]) == 2
    warn_mock.assert_not_called()


def test_wrap_patches_anthropic_messages_models() -> None:
    payload = {
        "thinking": {"type": "enabled"},
        "messages": [
            {"role": "user", "content": "Return JSON."},
            {"role": "assistant", "content": "{"},
        ],
    }
    wrapped = wrap_cloudflare_ai_gateway_provider_stream(
        {
            "model": {"api": "anthropic-messages"},
            "streamFn": _create_payload_base_stream(payload),
        }
    )

    wrapped(
        {"provider": "cloudflare-ai-gateway", "api": "anthropic-messages"},
        {},
        {},
    )

    assert payload["messages"] == [{"role": "user", "content": "Return JSON."}]


@patch.object(testing.log, "warning")
def test_wrap_leaves_non_anthropic_model_apis_on_original_stream_path(
    warn_mock: Any,
) -> None:
    on_payload_was_installed = False

    def base_stream_fn(_model: Any, _context: Any, options: dict[str, Any] | None = None):
        nonlocal on_payload_was_installed
        on_payload_was_installed = callable(options.get("onPayload") if options else None)
        return {}

    wrapped = wrap_cloudflare_ai_gateway_provider_stream(
        {
            "model": {"api": "openai-completions"},
            "streamFn": base_stream_fn,
        }
    )
    wrapped({"api": "openai-completions"}, {}, {})

    assert wrapped is base_stream_fn
    assert on_payload_was_installed is False
    warn_mock.assert_not_called()


def test_treats_missing_model_api_as_default_anthropic_messages_route() -> None:
    assert testing.should_patch_anthropic_messages_payload({}) is True
