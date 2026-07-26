"""Harness helper utilities ported from OpenClaw plugin-sdk agent-harness-runtime."""
# ruff: noqa: BLE001, S110

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from openclaw.node_host.with_timeout import with_timeout
from openclaw_packages.normalization_core import (
    finite_seconds_to_timer_safe_milliseconds,
    normalize_optional_string,
)

EMBEDDED_COMPACTION_TIMEOUT_MS = 180_000

MODEL_PROVIDER_REQUEST_TRANSPORT_KEY = "openclaw.modelProviderRequestTransport"

_TARGET_PREFIXES = frozenset({"channel", "chat", "direct", "dm", "group", "thread", "user"})

T = TypeVar("T")


def get_model_provider_request_transport(model: object) -> dict[str, Any] | None:
    if not isinstance(model, dict):
        return None
    transport = model.get(MODEL_PROVIDER_REQUEST_TRANSPORT_KEY)
    return transport if isinstance(transport, dict) else None


def attach_model_provider_request_transport(
    model: dict[str, Any],
    request: dict[str, Any] | None,
) -> dict[str, Any]:
    if not request:
        return model
    next_model = dict(model)
    next_model[MODEL_PROVIDER_REQUEST_TRANSPORT_KEY] = request
    return next_model


def _normalize_key(value: str | None) -> str:
    return (value or "").strip().lower()


def _strip_conversation_prefix(
    value: str | None,
    *providers: str | None,
) -> str | None:
    text = normalize_optional_string(value)
    if not text:
        return None

    separator_index = text.find(":")
    if separator_index == -1:
        return text

    prefix = _normalize_key(text[:separator_index])
    suffix = normalize_optional_string(text[separator_index + 1 :])
    if not suffix:
        return text
    if _TARGET_PREFIXES.intersection({prefix}) or any(
        prefix == _normalize_key(provider) for provider in providers if provider
    ):
        return suffix
    return text


def _parse_raw_session_conversation_ref(session_key: str | None) -> dict[str, str] | None:
    key = normalize_optional_string(session_key)
    if not key:
        return None
    parts = key.split(":")
    if len(parts) < 3:
        return None
    return {"rawId": parts[-1]}


def _resolve_agent_hook_channel(params: dict[str, Any]) -> str | None:
    message_channel = normalize_optional_string(params.get("messageChannel"))
    provider = normalize_optional_string(params.get("messageProvider"))
    if not message_channel:
        return provider

    separator_index = message_channel.find(":")
    if separator_index == -1:
        return message_channel

    prefix = normalize_optional_string(message_channel[:separator_index])
    if not prefix:
        return provider
    if _TARGET_PREFIXES.intersection({_normalize_key(prefix)}) or _normalize_key(prefix) == _normalize_key(
        provider
    ):
        return provider
    return prefix


def _resolve_agent_hook_channel_id(params: dict[str, Any]) -> str | None:
    provider = normalize_optional_string(params.get("messageProvider"))
    message_channel = normalize_optional_string(params.get("messageChannel"))
    parsed = _parse_raw_session_conversation_ref(params.get("sessionKey"))
    if parsed and parsed.get("rawId"):
        return parsed["rawId"]

    metadata_channel = _strip_conversation_prefix(
        params.get("currentChannelId"),
        provider,
        message_channel,
    ) or _strip_conversation_prefix(params.get("messageTo"), provider, message_channel)
    if metadata_channel and _normalize_key(metadata_channel) != _normalize_key(provider):
        return metadata_channel

    stripped_message_channel = _strip_conversation_prefix(
        params.get("messageChannel"),
        provider,
        message_channel,
    )
    if stripped_message_channel and _normalize_key(stripped_message_channel) != _normalize_key(provider):
        return stripped_message_channel
    return message_channel or provider


def build_agent_hook_context_channel_fields(params: dict[str, Any]) -> dict[str, Any]:
    channel = _resolve_agent_hook_channel(params)
    channel_id = _resolve_agent_hook_channel_id(params)
    return {
        "channel": channel,
        "messageProvider": normalize_optional_string(params.get("messageProvider")),
        "channelId": channel_id,
        "chatId": channel_id,
        "senderId": normalize_optional_string(params.get("senderId")),
    }


def resolve_compaction_timeout_ms(cfg: dict[str, Any] | None = None) -> int:
    if isinstance(cfg, dict):
        agents = cfg.get("agents")
        if isinstance(agents, dict):
            defaults = agents.get("defaults")
            if isinstance(defaults, dict):
                compaction = defaults.get("compaction")
                if isinstance(compaction, dict):
                    timeout_ms = finite_seconds_to_timer_safe_milliseconds(
                        compaction.get("timeoutSeconds"),
                        floor_seconds=True,
                    )
                    if timeout_ms is not None:
                        return timeout_ms
    return EMBEDDED_COMPACTION_TIMEOUT_MS


def _create_abort_error(abort_signal: Any) -> Exception:
    reason = getattr(abort_signal, "reason", None)
    if isinstance(reason, BaseException):
        return reason
    if reason:
        return Exception(str(reason))
    err = Exception("aborted")
    err.name = "AbortError"  # type: ignore[attr-defined]
    return err


def throw_if_aborted(abort_signal: Any | None = None) -> None:
    if abort_signal is None or not getattr(abort_signal, "aborted", False):
        return
    raise _create_abort_error(abort_signal)


async def compact_with_safety_timeout(
    compact: Callable[[Any | None], Awaitable[T]],
    timeout_ms: int = EMBEDDED_COMPACTION_TIMEOUT_MS,
    opts: dict[str, Any] | None = None,
) -> T:
    options = opts or {}
    abort_signal = options.get("abortSignal")
    canceled = False

    def cancel() -> None:
        nonlocal canceled
        if canceled:
            return
        canceled = True
        on_cancel = options.get("onCancel")
        if callable(on_cancel):
            try:
                on_cancel()
            except Exception:
                pass

    if abort_signal is not None and getattr(abort_signal, "aborted", False):
        cancel()
        raise _create_abort_error(abort_signal)

    async def _run_work(timeout_event: asyncio.Event | None) -> T:
        if abort_signal is not None:

            async def _wait_for_abort() -> None:
                if hasattr(abort_signal, "add_event_listener"):
                    done = asyncio.Event()

                    def _on_abort() -> None:
                        done.set()

                    abort_signal.add_event_listener("abort", _on_abort, once=True)
                    await done.wait()
                    return
                while not getattr(abort_signal, "aborted", False):
                    await asyncio.sleep(0)
                return

            compact_task = asyncio.create_task(compact(abort_signal))
            abort_task = asyncio.create_task(_wait_for_abort())
            done, pending = await asyncio.wait(
                {compact_task, abort_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if abort_task in done and getattr(abort_signal, "aborted", False):
                cancel()
                compact_task.cancel()
                try:
                    await compact_task
                except asyncio.CancelledError:
                    pass
                raise _create_abort_error(abort_signal)
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            return await compact_task

        if timeout_event is not None and timeout_event.is_set():
            cancel()
            raise TimeoutError("Compaction timed out")
        return await compact(None)

    try:
        return await with_timeout(_run_work, timeout_ms, "Compaction")
    except TimeoutError:
        cancel()
        raise
