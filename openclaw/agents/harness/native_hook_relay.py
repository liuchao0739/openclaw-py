"""Bridges native harness hook events through registered relay processes.

This is a large module (~2400 lines in TypeScript). The full HTTP bridge,
permission approval, and provider adapter logic is deferred. This port
provides the core types, constants, and a minimal relay registry so
harness callers can register and query relay state without crashes.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any, Literal, TypedDict

NATIVE_HOOK_RELAY_EVENTS = ("pre_tool_use", "post_tool_use", "permission_request", "before_agent_finalize")
NATIVE_HOOK_RELAY_PROVIDERS = ("codex",)

NativeHookRelayEvent = Literal["pre_tool_use", "post_tool_use", "permission_request", "before_agent_finalize"]
NativeHookRelayProvider = Literal["codex"]

DEFAULT_RELAY_TTL_MS = 30 * 60 * 1000
DEFAULT_RELAY_TIMEOUT_MS = 5_000

NATIVE_HOOK_TOOL_NAME_ALIASES = {"exec_command": "exec"}


class NativeHookRelayProcessResponse(TypedDict):
    stdout: str
    stderr: str
    exitCode: int


class NativeHookRelayInvocation(TypedDict, total=False):
    provider: str
    relayId: str
    event: str
    nativeEventName: str
    agentId: str
    sessionId: str
    sessionKey: str
    runId: str
    cwd: str
    model: str
    turnId: str
    transcriptPath: str
    permissionMode: str
    stopHookActive: bool
    lastAssistantMessage: str
    toolName: str
    toolUseId: str
    rawPayload: Any
    receivedAt: str


_relays: dict[str, dict[str, Any]] = {}
_invocations: list[NativeHookRelayInvocation] = []


def _normalize_relay_id(value: str | None) -> str | None:
    if not value:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) > 160 or not all(c.isalnum() or c in "._:-" for c in trimmed):
        raise ValueError("native hook relay id must be non-empty, compact, and URL-safe")
    return trimmed


def _normalize_relay_generation(value: str | None) -> str | None:
    return _normalize_relay_id(value)


def _normalize_positive_integer(value: int | None, fallback: int) -> int:
    if isinstance(value, (int, float)) and value == value and value > 0:
        return int(value)
    return fallback


def _normalize_allowed_events(events: tuple[str, ...] | None) -> tuple[str, ...]:
    if not events:
        return NATIVE_HOOK_RELAY_EVENTS
    return tuple(dict.fromkeys(events))


def register_native_hook_relay(params: dict[str, Any]) -> dict[str, Any]:
    """Register a native hook relay and return a handle."""
    _prune_expired_relays()
    relay_id = _normalize_relay_id(params.get("relayId")) or str(uuid.uuid4())
    generation = _normalize_relay_generation(params.get("generation")) or str(uuid.uuid4())
    now = int(time.time() * 1000)
    ttl_ms = _normalize_positive_integer(params.get("ttlMs"), DEFAULT_RELAY_TTL_MS)
    expires_at_ms = now + ttl_ms
    allowed_events = _normalize_allowed_events(params.get("allowedEvents"))

    _unregister_native_hook_relay(relay_id)
    registration: dict[str, Any] = {
        "relayId": relay_id,
        "provider": params["provider"],
        "generation": generation,
        "sessionId": params["sessionId"],
        "runId": params["runId"],
        "allowedEvents": allowed_events,
        "expiresAtMs": expires_at_ms,
    }
    for key in ("agentId", "sessionKey", "config", "channelId"):
        if params.get(key):
            registration[key] = params[key]
    if params.get("generationMismatchGraceMs"):
        registration["generationMismatchGraceExpiresAtMs"] = now + int(params["generationMismatchGraceMs"])
    if params.get("signal"):
        registration["signal"] = params["signal"]

    _relays[relay_id] = registration

    def _should_relay_event(event: str) -> bool:
        return event in registration["allowedEvents"]

    def _unregister() -> None:
        _unregister_native_hook_relay(relay_id, registration)

    def _renew(ttl_ms: int | None = None) -> None:
        current = _relays.get(relay_id)
        if current is not registration:
            return
        renewed = _normalize_positive_integer(ttl_ms, DEFAULT_RELAY_TTL_MS)
        current["expiresAtMs"] = int(time.time() * 1000) + renewed

    handle = {
        **registration,
        "shouldRelayEvent": _should_relay_event,
        "renew": _renew,
        "unregister": _unregister,
    }
    return handle


def _unregister_native_hook_relay(relay_id: str, expected: dict[str, Any] | None = None) -> None:
    if expected is not None and _relays.get(relay_id) is not expected:
        return
    _relays.pop(relay_id, None)
    _remove_native_hook_relay_invocations(relay_id)


def _prune_expired_relays(now: int | None = None) -> None:
    if now is None:
        now = int(time.time() * 1000)
    for relay_id, registration in list(_relays.items()):
        if now > registration.get("expiresAtMs", 0):
            _unregister_native_hook_relay(relay_id, registration)


def _remove_native_hook_relay_invocations(relay_id: str) -> None:
    global _invocations
    _invocations = [inv for inv in _invocations if inv.get("relayId") != relay_id]


def _record_native_hook_relay_invocation(invocation: NativeHookRelayInvocation) -> None:
    _invocations.append(invocation)
    if len(_invocations) > 200:
        del _invocations[: len(_invocations) - 200]


def has_native_hook_relay_invocation(params: dict[str, Any]) -> bool:
    tool_use_id = (params.get("toolUseId") or "").strip()
    if not tool_use_id:
        return False
    return any(
        inv.get("relayId") == params["relayId"]
        and inv.get("event") == params["event"]
        and inv.get("toolUseId") == tool_use_id
        for inv in _invocations
    )


def is_native_hook_relay_bridge_stale_registration_error(error: Any) -> bool:
    return isinstance(error, Exception) and "stale registration" in str(error)


def _normalize_native_hook_tool_name(tool_name: str | None) -> str:
    normalized = (tool_name or "tool").strip().lower() or "tool"
    return NATIVE_HOOK_TOOL_NAME_ALIASES.get(normalized, normalized)


def clear_native_hook_relays_for_tests() -> None:
    _relays.clear()
    _invocations.clear()


def get_native_hook_relay_invocations_for_tests() -> list[NativeHookRelayInvocation]:
    return list(_invocations)


def get_native_hook_relay_registration_for_tests(relay_id: str) -> dict[str, Any] | None:
    return _relays.get(relay_id)
