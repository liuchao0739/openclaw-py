"""Evaluates tool descriptors against runtime availability constraints.

Mirrors src/tools/availability.ts.
"""

from __future__ import annotations

from collections.abc import Sequence

from openclaw.packages.normalization_core import is_record
from openclaw.tools.types import (
    JsonObject,
    JsonPrimitive,
    JsonValue,
    ToolAvailabilityContext,
    ToolAvailabilityDiagnostic,
    ToolAvailabilityExpression,
    ToolAvailabilitySignal,
    ToolAvailabilitySignalConfig,
    ToolDescriptor,
    ToolUnavailableReason,
)


def _resolve_config_path(
    config: JsonObject | None,
    path: Sequence[str],
) -> JsonValue | None:
    current: JsonValue | None = config
    for segment in path:
        if not is_record(current):
            return None
        current = current.get(segment)
    return current


def _has_configured_value(
    *,
    value: JsonValue | None,
    signal: ToolAvailabilitySignalConfig,
    context: ToolAvailabilityContext,
) -> bool:
    if value is None:
        return False
    check = signal.get("check", "exists")
    if check == "available":
        resolver = context.get("is_config_value_available")
        return (
            resolver(
                {
                    "value": value,
                    "path": signal["path"],
                    "signal": signal,
                }
            )
            is True
            if resolver is not None
            else False
        )
    if check == "exists":
        return True
    if isinstance(value, str):
        return len(value.strip()) > 0
    if isinstance(value, list):
        return len(value) > 0
    if is_record(value):
        return len(value) > 0
    return True


def _has_availability_expression_shape(value: ToolAvailabilityExpression) -> bool:
    return "kind" in value or "all_of" in value or "any_of" in value


def _diagnostic(
    reason: ToolUnavailableReason,
    signal: ToolAvailabilitySignal | None,
    message: str,
) -> ToolAvailabilityDiagnostic:
    result: ToolAvailabilityDiagnostic = {"reason": reason, "message": message}
    if signal is not None:
        result["signal"] = signal
    return result


def _evaluate_signal(
    signal: ToolAvailabilitySignal,
    context: ToolAvailabilityContext,
) -> ToolAvailabilityDiagnostic | None:
    kind = signal["kind"]
    if kind == "always":
        return None
    if kind == "auth":
        provider_ids = context.get("auth_provider_ids")
        return (
            None
            if provider_ids is not None and signal["provider_id"] in provider_ids
            else _diagnostic(
                "auth-missing",
                signal,
                f"Missing auth provider: {signal['provider_id']}",
            )
        )
    if kind == "config":
        value = _resolve_config_path(context.get("config"), signal["path"])
        return (
            None
            if _has_configured_value(value=value, signal=signal, context=context)
            else _diagnostic(
                "config-missing",
                signal,
                f"Missing config path: {'.'.join(signal['path'])}",
            )
        )
    if kind == "env":
        env = context.get("env") or {}
        env_value = env.get(signal["name"])
        return (
            None
            if isinstance(env_value, str) and env_value.strip()
            else _diagnostic(
                "env-missing",
                signal,
                f"Missing environment value: {signal['name']}",
            )
        )
    if kind == "plugin-enabled":
        enabled_plugin_ids = context.get("enabled_plugin_ids")
        return (
            None
            if enabled_plugin_ids is not None and signal["plugin_id"] in enabled_plugin_ids
            else _diagnostic(
                "plugin-disabled",
                signal,
                f"Plugin is not enabled: {signal['plugin_id']}",
            )
        )
    if kind == "context":
        values = context.get("values") or {}
        value: JsonPrimitive | None = values.get(signal["key"])
        if "equals" not in signal:
            return (
                _diagnostic(
                    "context-mismatch",
                    signal,
                    f"Missing context value: {signal['key']}",
                )
                if value is None
                else None
            )
        return (
            None
            if value == signal["equals"]
            else _diagnostic(
                "context-mismatch",
                signal,
                f"Context value did not match: {signal['key']}",
            )
        )
    return _diagnostic("unsupported-signal", signal, "Unsupported availability signal")


def _evaluate_expression(
    expression: ToolAvailabilityExpression,
    context: ToolAvailabilityContext,
) -> list[ToolAvailabilityDiagnostic]:
    if "kind" in expression:
        diagnostic = _evaluate_signal(expression, context)
        return [diagnostic] if diagnostic is not None else []
    if "all_of" in expression:
        entries = expression["all_of"]
        if len(entries) == 0:
            return [
                {
                    "reason": "unsupported-signal",
                    "message": "Empty availability allOf group",
                }
            ]
        result: list[ToolAvailabilityDiagnostic] = []
        for entry in entries:
            result.extend(_evaluate_expression(entry, context))
        return result
    if "any_of" in expression:
        entries = expression["any_of"]
        if len(entries) == 0:
            return [
                {
                    "reason": "unsupported-signal",
                    "message": "Empty availability anyOf group",
                }
            ]
        diagnostics = [_evaluate_expression(entry, context) for entry in entries]
        unsupported = [
            entry
            for branch in diagnostics
            for entry in branch
            if entry.get("reason") == "unsupported-signal"
        ]
        if any(len(branch) == 0 for branch in diagnostics):
            return unsupported
        return [entry for branch in diagnostics for entry in branch]
    return [
        {
            "reason": "unsupported-signal",
            "message": "Unsupported availability expression",
        }
    ]


def evaluate_tool_availability(
    *,
    descriptor: ToolDescriptor,
    context: ToolAvailabilityContext | None = None,
) -> list[ToolAvailabilityDiagnostic]:
    """Evaluate one descriptor against runtime context and return hidden-tool diagnostics."""
    resolved_context = context or {}
    availability: ToolAvailabilityExpression = descriptor.get("availability") or {"kind": "always"}
    if not _has_availability_expression_shape(availability):
        return [
            {
                "reason": "unsupported-signal",
                "message": "Unsupported availability expression",
            }
        ]
    return _evaluate_expression(availability, resolved_context)
