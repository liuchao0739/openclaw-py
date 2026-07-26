"""Provider stream shared helpers implement reusable stream wrappers and payload policies."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from openclaw.llm.providers.stream_wrappers.stream_payload_utils import stream_with_payload_patch
from openclaw.packages.normalization_core import is_record

__all__ = [
    "create_anthropic_thinking_prefill_payload_wrapper",
    "create_deep_seek_v4_openai_compatible_thinking_wrapper",
    "create_payload_patch_stream_wrapper",
    "strip_trailing_anthropic_assistant_prefill_when_thinking",
]


def create_payload_patch_stream_wrapper(
    base_stream_fn: Callable[..., Any] | None,
    patch_payload: Callable[[dict[str, Any]], None],
    wrapper_options: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    """Wrap a provider stream so callers can patch the outbound provider payload once."""

    def wrapped(model: Any, context: Any, options: dict[str, Any] | None = None) -> Any:
        if wrapper_options and wrapper_options.get("shouldPatch"):
            should_patch = wrapper_options["shouldPatch"]
            if not should_patch({"model": model, "context": context, "options": options}):
                if base_stream_fn is None:
                    raise RuntimeError("stream function is not configured")
                return base_stream_fn(model, context, options)

        def patch(payload: dict[str, Any]) -> None:
            patch_payload(
                {
                    "payload": payload,
                    "model": model,
                    "context": context,
                    "options": options,
                }
            )

        if base_stream_fn is None:
            raise RuntimeError("stream function is not configured")
        return stream_with_payload_patch(base_stream_fn, model, context, options, patch)

    return wrapped


def _is_disabled_deep_seek_v4_thinking_level(thinking_level: Any) -> bool:
    normalized = thinking_level.strip().lower() if isinstance(thinking_level, str) else ""
    return normalized in {"off", "none"}


def _resolve_deep_seek_v4_reasoning_effort(thinking_level: Any) -> str:
    normalized = thinking_level.strip().lower() if isinstance(thinking_level, str) else ""
    return "max" if normalized in {"xhigh", "max"} else "high"


def _strip_deep_seek_v4_reasoning_content(payload: dict[str, Any]) -> None:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return
    for message in messages:
        if is_record(message):
            message.pop("reasoning_content", None)


def _ensure_deep_seek_v4_assistant_reasoning_content(
    payload: dict[str, Any],
    *,
    should_backfill_assistant_message: Callable[[dict[str, Any]], bool] | None = None,
) -> None:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return
    for message in messages:
        if not is_record(message) or message.get("role") != "assistant":
            continue
        if should_backfill_assistant_message and not should_backfill_assistant_message(message):
            continue
        if "reasoning_content" not in message:
            message["reasoning_content"] = ""


def _is_anthropic_thinking_enabled(payload: dict[str, Any]) -> bool:
    thinking = payload.get("thinking")
    if not is_record(thinking):
        return False
    return thinking.get("type") != "disabled"


def _assistant_message_has_anthropic_tool_use(message: dict[str, Any]) -> bool:
    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list) and len(tool_calls) > 0:
        return True
    content = message.get("content")
    if not isinstance(content, list):
        return False
    return any(
        is_record(block) and block.get("type") in ("tool_use", "toolCall") for block in content
    )


def _strip_trailing_assistant_prefill_messages(payload: dict[str, Any]) -> int:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return 0

    stripped = 0
    while messages:
        final_message = messages[-1]
        if not is_record(final_message):
            break
        if final_message.get("role") != "assistant" or _assistant_message_has_anthropic_tool_use(
            final_message
        ):
            break
        messages.pop()
        stripped += 1
    return stripped


def strip_trailing_anthropic_assistant_prefill_when_thinking(payload: dict[str, Any]) -> int:
    if not _is_anthropic_thinking_enabled(payload):
        return 0
    return _strip_trailing_assistant_prefill_messages(payload)


def create_anthropic_thinking_prefill_payload_wrapper(
    base_stream_fn: Callable[..., Any] | None,
    on_stripped: Callable[[int], None] | None = None,
    wrapper_options: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    def patch_payload(params: dict[str, Any]) -> None:
        payload = params["payload"]
        stripped = strip_trailing_anthropic_assistant_prefill_when_thinking(payload)
        if stripped > 0 and on_stripped is not None:
            on_stripped(stripped)

    return create_payload_patch_stream_wrapper(base_stream_fn, patch_payload, wrapper_options)


def create_deep_seek_v4_openai_compatible_thinking_wrapper(
    *,
    base_stream_fn: Callable[..., Any] | None,
    thinking_level: Any,
    should_patch_model: Callable[[Any], bool],
    resolve_reasoning_effort: Callable[[Any], str] | None = None,
    should_backfill_assistant_reasoning_content: Callable[[dict[str, Any]], bool] | None = None,
) -> Callable[..., Any] | None:
    if base_stream_fn is None:
        return None

    underlying = base_stream_fn
    resolve_effort = resolve_reasoning_effort or _resolve_deep_seek_v4_reasoning_effort

    def wrapped(model: Any, context: Any, options: dict[str, Any] | None = None) -> Any:
        if not should_patch_model(model):
            return underlying(model, context, options)

        def patch(payload: dict[str, Any]) -> None:
            if _is_disabled_deep_seek_v4_thinking_level(thinking_level):
                payload["thinking"] = {"type": "disabled"}
                payload.pop("reasoning_effort", None)
                payload.pop("reasoning", None)
                _strip_deep_seek_v4_reasoning_content(payload)
                return

            payload["thinking"] = {"type": "enabled"}
            payload["reasoning_effort"] = resolve_effort(thinking_level)
            _ensure_deep_seek_v4_assistant_reasoning_content(
                payload,
                should_backfill_assistant_message=should_backfill_assistant_reasoning_content,
            )

        return stream_with_payload_patch(underlying, model, context, options, patch)

    return wrapped
