from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.provider_auth import build_copilot_ide_headers, COPILOT_INTEGRATION_ID
from openclaw.plugin_sdk.provider_stream_shared import stream_with_payload_patch

from openclaw_extensions.github_copilot.connection_bound_ids import (
    rewrite_copilot_response_payload_connection_bound_ids,
)
from openclaw_extensions.github_copilot.replay_policy import (
    strip_copilot_assistant_thinking_messages,
)


def _contains_copilot_content_type(value: Any, content_type: str) -> bool:
    if isinstance(value, list):
        return any(_contains_copilot_content_type(item, content_type) for item in value)
    if not isinstance(value, dict):
        return False
    return value.get("type") == content_type or _contains_copilot_content_type(
        value.get("content"), content_type
    )


def _infer_copilot_initiator(messages: list[Any]) -> str:
    if not messages:
        return "user"
    last = messages[-1]
    if not isinstance(last, dict):
        return "user"
    if last.get("role") == "user" and _contains_copilot_content_type(last.get("content"), "tool_result"):
        return "agent"
    return "user" if last.get("role") == "user" else "agent"


def has_copilot_vision_input(messages: list[Any]) -> bool:
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = message.get("content")
        if role == "user" and isinstance(content, list):
            if any(_contains_copilot_content_type(item, "image") for item in content):
                return True
        if role == "toolResult" and isinstance(content, list):
            if any(_contains_copilot_content_type(item, "image") for item in content):
                return True
    return False


def build_copilot_dynamic_headers(params: dict[str, Any]) -> dict[str, str]:
    headers = dict(build_copilot_ide_headers())
    headers["Copilot-Integration-Id"] = COPILOT_INTEGRATION_ID
    headers["Openai-Organization"] = "github-copilot"
    headers["x-initiator"] = _infer_copilot_initiator(params.get("messages", []))
    if params.get("hasImages"):
        headers["Copilot-Vision-Request"] = "true"
    return headers


def _patch_on_payload_result(result: Any) -> Any:
    if hasattr(result, "then") and callable(getattr(result, "then")):
        return result.then(lambda next_val: (
            rewrite_copilot_response_payload_connection_bound_ids(next_val),
            next_val,
        )[1])
    rewrite_copilot_response_payload_connection_bound_ids(result)
    return result


def _build_copilot_request_headers(
    context: dict[str, Any],
    headers: dict[str, str] | None,
) -> dict[str, str]:
    result = build_copilot_dynamic_headers({
        "messages": context.get("messages", []),
        "hasImages": has_copilot_vision_input(context.get("messages", [])),
    })
    if headers:
        result.update(headers)
    return result


def _patch_copilot_anthropic_payload(payload: dict[str, Any]) -> None:
    messages = payload.get("messages")
    if isinstance(messages, list):
        payload["messages"] = strip_copilot_assistant_thinking_messages(messages)


def wrap_copilot_anthropic_stream(
    base_stream_fn: Any,
) -> Any:
    if base_stream_fn is None:
        return None
    underlying = base_stream_fn

    def wrapped(model: Any, context: Any, options: dict[str, Any] | None = None) -> Any:
        if model.get("provider") != "github-copilot" or model.get("api") != "anthropic-messages":
            return underlying(model, context, options)

        headers = _build_copilot_request_headers(context, options.get("headers") if options else None)

        def patch_payload(payload: dict[str, Any]) -> None:
            _patch_copilot_anthropic_payload(payload)

        return stream_with_payload_patch(
            underlying,
            model,
            context,
            {**(options or {}), "headers": headers},
            patch_payload,
        )

    return wrapped


def wrap_copilot_openai_responses_stream(
    base_stream_fn: Any,
) -> Any:
    if base_stream_fn is None:
        return None
    underlying = base_stream_fn

    def wrapped(model: Any, context: Any, options: dict[str, Any] | None = None) -> Any:
        if model.get("provider") != "github-copilot" or model.get("api") != "openai-responses":
            return underlying(model, context, options)

        original_on_payload = options.get("onPayload") if options else None
        headers = _build_copilot_request_headers(context, options.get("headers") if options else None)

        def on_payload(payload: Any, payload_model: Any = None) -> Any:
            rewrite_copilot_response_payload_connection_bound_ids(payload)
            if original_on_payload:
                return original_on_payload(payload, payload_model)
            return None

        wrapped_options = {**(options or {}), "headers": headers, "onPayload": on_payload}
        return underlying(model, context, wrapped_options)

    return wrapped


def wrap_copilot_openai_completions_stream(
    base_stream_fn: Any,
) -> Any:
    if base_stream_fn is None:
        return None
    underlying = base_stream_fn

    def wrapped(model: Any, context: Any, options: dict[str, Any] | None = None) -> Any:
        if model.get("provider") != "github-copilot" or model.get("api") != "openai-completions":
            return underlying(model, context, options)

        headers = _build_copilot_request_headers(context, options.get("headers") if options else None)
        return underlying(model, context, {**(options or {}), "headers": headers})

    return wrapped


def wrap_copilot_provider_stream(ctx: dict[str, Any]) -> Any:
    stream_fn = ctx.get("streamFn")
    return wrap_copilot_openai_completions_stream(
        wrap_copilot_openai_responses_stream(
            wrap_copilot_anthropic_stream(stream_fn),
        ),
    )
