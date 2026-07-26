"""Provider stream shared helpers implement reusable stream wrappers and payload policies."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from openclaw.llm.providers.stream_wrappers.stream_payload_utils import stream_with_payload_patch
from openclaw.packages.normalization_core import is_record

__all__ = [
    "create_deep_seek_v4_openai_compatible_thinking_wrapper",
    "create_payload_patch_stream_wrapper",
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
