"""Defines and dispatches runtime diagnostic event payloads.

Mirrors src/infra/diagnostic-events.ts (core dispatcher subset).
"""

from __future__ import annotations

import copy
import sys
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, TypedDict

from openclaw.infra.diagnostic_trace_context import get_active_diagnostic_trace_context
from openclaw.infra.prototype_keys import is_blocked_object_key

DiagnosticEventPayload = dict[str, Any]


class DiagnosticEventMetadata(TypedDict, total=False):
    internal: bool
    trustedTraceContext: bool
    trusted: bool


class DiagnosticModelCallContent(TypedDict, total=False):
    inputMessages: Any
    outputMessages: Any
    systemPrompt: str
    toolDefinitions: Any


class DiagnosticToolCallContent(TypedDict, total=False):
    toolInput: Any
    toolOutput: Any


class DiagnosticEventPrivateData(TypedDict, total=False):
    modelContent: DiagnosticModelCallContent
    toolContent: DiagnosticToolCallContent


DiagnosticEventInput = Mapping[str, Any]

DiagnosticEventListener = Callable[[DiagnosticEventPayload, DiagnosticEventMetadata], None]
TrustedDiagnosticEventListener = Callable[
    [DiagnosticEventPayload, DiagnosticEventMetadata, DiagnosticEventPrivateData],
    None,
]

_MAX_ASYNC_DIAGNOSTIC_EVENTS = 10_000
_MAX_ASYNC_DIAGNOSTIC_EVENTS_PER_TURN = 100
_DIAGNOSTIC_EVENTS_STATE_KEY = "openclaw.diagnosticEvents.state.v1"
_dispatched_trusted_diagnostic_metadata: set[int] = set()
_ASYNC_DIAGNOSTIC_EVENT_TYPES = frozenset(
    {
        "tool.execution.started",
        "tool.execution.completed",
        "tool.execution.error",
        "tool.execution.blocked",
        "skill.used",
        "exec.process.completed",
        "message.delivery.started",
        "message.delivery.completed",
        "message.delivery.error",
        "talk.event",
        "model.call.started",
        "model.call.completed",
        "model.call.error",
        "run.progress",
        "harness.run.completed",
        "harness.run.error",
        "context.assembled",
        "log.record",
    }
)
_PRIORITY_ASYNC_DIAGNOSTIC_EVENT_TYPES = frozenset(
    {
        "tool.execution.completed",
        "tool.execution.error",
        "tool.execution.blocked",
    }
)


@dataclass
class _QueuedDiagnosticEvent:
    event: DiagnosticEventPayload
    metadata: DiagnosticEventMetadata
    private_data: DiagnosticEventPrivateData | None = None


@dataclass
class _DiagnosticEventsState:
    enabled: bool = True
    seq: int = 0
    listeners: set[DiagnosticEventListener] = field(default_factory=set)
    trusted_listeners: set[TrustedDiagnosticEventListener] = field(default_factory=set)
    dispatch_depth: int = 0
    async_queue: list[_QueuedDiagnosticEvent] = field(default_factory=list)
    async_drain_scheduled: bool = False
    async_dropped_events: int = 0
    async_dropped_trusted_events: int = 0
    async_dropped_untrusted_events: int = 0
    async_dropped_priority_events: int = 0


def _get_diagnostic_events_state() -> _DiagnosticEventsState:
    module = sys.modules[__name__]
    existing = getattr(module, _DIAGNOSTIC_EVENTS_STATE_KEY, None)
    if isinstance(existing, _DiagnosticEventsState):
        return existing
    state = _DiagnosticEventsState()
    setattr(module, _DIAGNOSTIC_EVENTS_STATE_KEY, state)
    return state


def is_diagnostics_enabled(config: Mapping[str, Any] | None = None) -> bool:
    """Return whether diagnostics are enabled for a loaded config."""
    if config is None:
        return True
    diagnostics = config.get("diagnostics")
    if not isinstance(diagnostics, Mapping):
        return True
    return diagnostics.get("enabled") is not False


def set_diagnostics_enabled_for_process(enabled: bool) -> None:
    """Set the process-wide diagnostic dispatcher enable flag."""
    _get_diagnostic_events_state().enabled = enabled


def are_diagnostics_enabled_for_process() -> bool:
    """Return the current process-wide diagnostic dispatcher enable flag."""
    return _get_diagnostic_events_state().enabled


def _deep_freeze_diagnostic_value(value: Any, seen: set[int] | None = None) -> Any:
    if seen is None:
        seen = set()
    if not isinstance(value, (dict, list)):
        return value
    value_id = id(value)
    if value_id in seen:
        return value
    seen.add(value_id)
    if isinstance(value, list):
        for index, item in enumerate(value):
            value[index] = _deep_freeze_diagnostic_value(item, seen)
        return value
    for key, nested in list(value.items()):
        value[key] = _deep_freeze_diagnostic_value(nested, seen)
    return value


def _clone_diagnostic_event_for_listener(event: DiagnosticEventPayload) -> DiagnosticEventPayload:
    return _deep_freeze_diagnostic_value(copy.deepcopy(event))


def _clone_diagnostic_private_data_for_listener(
    private_data: DiagnosticEventPrivateData | None,
) -> DiagnosticEventPrivateData:
    if not private_data:
        return {}
    return _deep_freeze_diagnostic_value(copy.deepcopy(private_data))


def _create_diagnostic_metadata_for_listener(
    metadata: DiagnosticEventMetadata,
) -> DiagnosticEventMetadata:
    listener_metadata = dict(metadata)
    if listener_metadata.get("trusted"):
        _dispatched_trusted_diagnostic_metadata.add(id(listener_metadata))
    return listener_metadata


def _create_internal_diagnostic_metadata(trusted: bool) -> DiagnosticEventMetadata:
    return {"internal": True, "trusted": trusted}


def _dispatch_diagnostic_event(
    state: _DiagnosticEventsState,
    enriched: DiagnosticEventPayload,
    metadata: DiagnosticEventMetadata,
    private_data: DiagnosticEventPrivateData | None = None,
) -> None:
    if state.dispatch_depth > 100:
        print(
            f"[diagnostic-events] recursion guard tripped at depth={state.dispatch_depth}, "
            f"dropping type={enriched.get('type')}",
            file=sys.stderr,
        )
        return

    state.dispatch_depth += 1
    try:
        for listener in list(state.listeners):
            try:
                listener(
                    _clone_diagnostic_event_for_listener(enriched),
                    _create_diagnostic_metadata_for_listener(metadata),
                )
            except Exception as err:  # noqa: BLE001
                print(
                    f"[diagnostic-events] listener error type={enriched.get('type')} "
                    f"seq={enriched.get('seq')}: {err}",
                    file=sys.stderr,
                )
        for listener in list(state.trusted_listeners):
            try:
                listener(
                    _clone_diagnostic_event_for_listener(enriched),
                    _create_diagnostic_metadata_for_listener(metadata),
                    _clone_diagnostic_private_data_for_listener(private_data),
                )
            except Exception as err:  # noqa: BLE001
                print(
                    f"[diagnostic-events] trusted listener error type={enriched.get('type')} "
                    f"seq={enriched.get('seq')}: {err}",
                    file=sys.stderr,
                )
    finally:
        state.dispatch_depth -= 1


def _is_priority_async_diagnostic_event(entry: _QueuedDiagnosticEvent) -> bool:
    return (
        entry.metadata.get("trusted") is True
        and entry.event.get("type") in _PRIORITY_ASYNC_DIAGNOSTIC_EVENT_TYPES
    )


def _note_async_diagnostic_drop(
    state: _DiagnosticEventsState,
    entry: _QueuedDiagnosticEvent,
) -> None:
    state.async_dropped_events += 1
    if entry.metadata.get("trusted"):
        state.async_dropped_trusted_events += 1
    else:
        state.async_dropped_untrusted_events += 1
    if _is_priority_async_diagnostic_event(entry):
        state.async_dropped_priority_events += 1


def _make_room_for_priority_async_diagnostic_event(
    state: _DiagnosticEventsState,
) -> _QueuedDiagnosticEvent | None:
    for index, entry in enumerate(state.async_queue):
        if not _is_priority_async_diagnostic_event(entry):
            return state.async_queue.pop(index)
    if state.async_queue:
        return state.async_queue.pop(0)
    return None


def _schedule_async_diagnostic_drain(state: _DiagnosticEventsState) -> None:
    if state.async_drain_scheduled:
        return
    state.async_drain_scheduled = True

    def drain() -> None:
        state.async_drain_scheduled = False
        batch = state.async_queue[:_MAX_ASYNC_DIAGNOSTIC_EVENTS_PER_TURN]
        del state.async_queue[: len(batch)]
        for entry in batch:
            _dispatch_diagnostic_event(state, entry.event, entry.metadata, entry.private_data)
        if state.async_queue:
            _schedule_async_diagnostic_drain(state)

    threading.Timer(0, drain).start()


def _enrich_diagnostic_event(
    state: _DiagnosticEventsState,
    event: Mapping[str, Any],
) -> DiagnosticEventPayload:
    enriched: dict[str, Any] = {}
    for key, value in event.items():
        if is_blocked_object_key(key):
            continue
        enriched[key] = value
    if "trace" not in enriched:
        active_trace = get_active_diagnostic_trace_context()
        if active_trace is not None:
            enriched["trace"] = dict(active_trace)
    state.seq += 1
    enriched["seq"] = state.seq
    enriched["ts"] = int(time.time() * 1000)
    return enriched


def _emit_diagnostic_event_with_trust(
    event: Mapping[str, Any],
    trusted: bool,
    *,
    allow_security_event: bool = False,
    internal: bool = False,
    private_data: DiagnosticEventPrivateData | None = None,
    trusted_trace_context: bool = False,
) -> None:
    state = _get_diagnostic_events_state()
    if not state.enabled:
        return
    if event.get("type") == "security.event" and not allow_security_event:
        return

    enriched = _enrich_diagnostic_event(state, event)
    metadata: DiagnosticEventMetadata = (
        _create_internal_diagnostic_metadata(trusted) if internal else {"trusted": trusted}
    )
    if trusted_trace_context:
        metadata["trustedTraceContext"] = True

    event_type = enriched.get("type")
    if isinstance(event_type, str) and event_type in _ASYNC_DIAGNOSTIC_EVENT_TYPES:
        if len(state.async_queue) >= _MAX_ASYNC_DIAGNOSTIC_EVENTS:
            entry = _QueuedDiagnosticEvent(enriched, metadata, private_data)
            if not trusted or event_type not in _PRIORITY_ASYNC_DIAGNOSTIC_EVENT_TYPES:
                _note_async_diagnostic_drop(state, entry)
                return
            dropped_entry = _make_room_for_priority_async_diagnostic_event(state)
            if dropped_entry is not None:
                _note_async_diagnostic_drop(state, dropped_entry)
        state.async_queue.append(_QueuedDiagnosticEvent(enriched, metadata, private_data))
        _schedule_async_diagnostic_drain(state)
        return

    _dispatch_diagnostic_event(state, enriched, metadata, private_data)


def emit_diagnostic_event(event: DiagnosticEventInput) -> None:
    """Emit an untrusted diagnostic event from external/plugin-facing code."""
    _emit_diagnostic_event_with_trust(event, False)


def emit_diagnostic_event_with_trusted_trace_context(event: DiagnosticEventInput) -> None:
    """Emit an untrusted event whose trace context came from OpenClaw-owned scope."""
    _emit_diagnostic_event_with_trust(event, False, trusted_trace_context=True)


def emit_internal_diagnostic_event(event: DiagnosticEventInput) -> None:
    """Emit an untrusted diagnostic event tagged as internal dispatcher provenance."""
    _emit_diagnostic_event_with_trust(event, False, internal=True)


def emit_trusted_diagnostic_event(event: DiagnosticEventInput) -> None:
    """Emit a trusted diagnostic event from core/runtime-owned instrumentation."""
    _emit_diagnostic_event_with_trust(event, True)


def emit_trusted_diagnostic_event_with_private_data(
    event: DiagnosticEventInput,
    private_data: DiagnosticEventPrivateData | None = None,
) -> None:
    """Emit a trusted diagnostic event with private listener-only payload data."""
    _emit_diagnostic_event_with_trust(event, True, private_data=private_data)


def on_internal_diagnostic_event(listener: DiagnosticEventListener) -> Callable[[], None]:
    """Subscribe to all diagnostic events with dispatcher metadata."""
    state = _get_diagnostic_events_state()
    state.listeners.add(listener)

    def unsubscribe() -> None:
        state.listeners.discard(listener)

    return unsubscribe


def on_trusted_internal_diagnostic_event(
    listener: TrustedDiagnosticEventListener,
) -> Callable[[], None]:
    """Subscribe to all diagnostic events plus trusted private payload data."""
    state = _get_diagnostic_events_state()
    state.trusted_listeners.add(listener)

    def unsubscribe() -> None:
        state.trusted_listeners.discard(listener)

    return unsubscribe


def on_diagnostic_event(
    listener: Callable[[DiagnosticEventPayload], None],
) -> Callable[[], None]:
    """Subscribe to public untrusted diagnostic events only."""

    def wrapped(event: DiagnosticEventPayload, metadata: DiagnosticEventMetadata) -> None:
        if metadata.get("trusted") or event.get("type") == "log.record":
            return
        listener(event)

    return on_internal_diagnostic_event(wrapped)


async def wait_for_diagnostic_events_drained() -> None:
    """Wait until queued async diagnostic events have been delivered to listeners."""
    state = _get_diagnostic_events_state()
    while state.async_drain_scheduled or state.async_queue:
        await __import__("asyncio").sleep(0)


def is_internal_diagnostic_event_metadata(metadata: DiagnosticEventMetadata) -> bool:
    """Return whether listener metadata marks dispatcher-internal provenance."""
    return metadata.get("internal") is True


def reset_diagnostic_events_for_test() -> None:
    """Reset dispatcher state between tests."""
    state = _get_diagnostic_events_state()
    state.enabled = True
    state.seq = 0
    state.listeners.clear()
    state.trusted_listeners.clear()
    state.dispatch_depth = 0
    state.async_queue.clear()
    state.async_drain_scheduled = False
    state.async_dropped_events = 0
    state.async_dropped_trusted_events = 0
    state.async_dropped_untrusted_events = 0
    state.async_dropped_priority_events = 0
