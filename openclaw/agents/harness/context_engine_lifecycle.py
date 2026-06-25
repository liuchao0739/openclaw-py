"""Manages context-engine lifecycle hooks for native agent harnesses.

The full context-engine integration depends on several unported modules
(context-engine types, runtime-settings, maintenance). This port provides
the public function signatures with graceful no-op fallbacks so callers can
wire harness lifecycle without crashes during the migration window.
"""

from __future__ import annotations

from typing import Any


def is_active_harness_context_engine(context_engine: Any | None) -> bool:
    """Return True when a non-legacy context engine should affect plugin harness behavior."""
    return bool(context_engine is not None and getattr(context_engine, "info", {}).get("id") != "legacy")


def _build_harness_context_engine_runtime_settings(params: dict[str, Any]) -> Any:
    runtime_settings = params.get("runtimeSettings")
    if runtime_settings is not None:
        return runtime_settings
    try:
        from openclaw.context_engine.runtime_settings import build_context_engine_runtime_settings

        return build_context_engine_runtime_settings(
            {
                "contextEngineHost": params.get("contextEngineHostSupport"),
                "harnessId": params.get("harnessId"),
                "runtimeId": params.get("runtimeId"),
                "provider": params.get("providerId"),
                "requestedModel": params.get("requestedModelId"),
                "resolvedModel": params.get("modelId") or params.get("requestedModelId"),
                "modelFamily": params.get("modelFamily"),
                "selectedContextEngineId": getattr(params.get("contextEngine"), "info", {}).get("id") if params.get("contextEngine") else None,
                "contextEngineSelectionSource": "default",
                "promptTokenBudget": params.get("tokenBudget"),
                "maxOutputTokens": params.get("maxOutputTokens"),
                "fallbackReason": params.get("fallbackReason"),
                "degradedReason": params.get("degradedReason"),
            }
        )
    except Exception:
        return None


async def bootstrap_harness_context_engine(params: dict[str, Any]) -> None:
    """Run optional bootstrap + bootstrap maintenance for a harness-owned context engine."""
    context_engine = params.get("contextEngine")
    if not params.get("hadSessionFile") or context_engine is None:
        return
    if getattr(context_engine, "bootstrap", None) is None and getattr(context_engine, "maintain", None) is None:
        return
    try:
        runtime_settings = _build_harness_context_engine_runtime_settings(params)
        bootstrap_fn = getattr(context_engine, "bootstrap", None)
        if bootstrap_fn is not None:
            await bootstrap_fn(
                {
                    "sessionId": params["sessionId"],
                    "sessionKey": params.get("sessionKey"),
                    "sessionFile": params["sessionFile"],
                    "runtimeSettings": runtime_settings,
                }
            )
        run_maintenance = params.get("runMaintenance") or run_harness_context_engine_maintenance
        await run_maintenance(
            {
                "contextEngine": context_engine,
                "sessionId": params["sessionId"],
                "sessionKey": params.get("sessionKey"),
                "sessionFile": params["sessionFile"],
                "reason": "bootstrap",
                "sessionManager": params.get("sessionManager"),
                "runtimeSettings": runtime_settings,
                "config": params.get("config"),
            }
        )
    except Exception as bootstrap_err:
        params["warn"](f"context engine bootstrap failed: {bootstrap_err}")


async def assemble_harness_context_engine(params: dict[str, Any]) -> Any:
    """Assemble model context through the active harness-owned context engine."""
    context_engine = params.get("contextEngine")
    if context_engine is None:
        return None
    messages = params.get("messages", [])
    runtime_settings = _build_harness_context_engine_runtime_settings(params)
    assemble_fn = getattr(context_engine, "assemble", None)
    if assemble_fn is None:
        return None
    result = await assemble_fn(
        {
            "sessionId": params["sessionId"],
            "sessionKey": params.get("sessionKey"),
            "messages": messages,
            "tokenBudget": params.get("tokenBudget"),
            "model": params.get("modelId"),
            "runtimeSettings": runtime_settings,
            **({"availableTools": params["availableTools"]} if params.get("availableTools") else {}),
            **({"citationsMode": params["citationsMode"]} if params.get("citationsMode") else {}),
            **({"prompt": params["prompt"]} if params.get("prompt") is not None else {}),
        }
    )
    return _ensure_assemble_result_shape(result, getattr(context_engine, "info", {}).get("id", "unknown"))


def _ensure_assemble_result_shape(result: Any, engine_id: str) -> dict[str, Any]:
    if not result or not isinstance(result, dict):
        raise ValueError(
            f'context engine "{engine_id}" assemble() returned an invalid result: expected an object with a "messages" array'
        )
    if not isinstance(result.get("messages"), list):
        raise ValueError(
            f'context engine "{engine_id}" assemble() returned an invalid result: expected an object with a "messages" array'
        )
    return result


async def finalize_harness_context_engine_turn(params: dict[str, Any]) -> dict[str, bool]:
    """Finalize a completed harness turn via afterTurn or ingest fallbacks."""
    context_engine = params.get("contextEngine")
    if context_engine is None:
        return {"postTurnFinalizationSucceeded": True}

    runtime_settings = _build_harness_context_engine_runtime_settings(params)
    post_turn_finalization_succeeded = True
    after_turn_fn = getattr(context_engine, "afterTurn", None)

    if after_turn_fn is not None:
        try:
            await after_turn_fn(
                {
                    "sessionId": params["sessionIdUsed"],
                    "sessionKey": params.get("sessionKey"),
                    "sessionFile": params["sessionFile"],
                    "messages": params.get("messagesSnapshot", []),
                    "prePromptMessageCount": params.get("prePromptMessageCount", 0),
                    "tokenBudget": params.get("tokenBudget"),
                    "runtimeSettings": runtime_settings,
                    "runtimeContext": params.get("runtimeContext"),
                    "isHeartbeat": params.get("isHeartbeat"),
                }
            )
        except Exception as after_turn_err:
            post_turn_finalization_succeeded = False
            params["warn"](f"context engine afterTurn failed: {after_turn_err}")

    if (
        not params.get("promptError")
        and not params.get("aborted")
        and not params.get("yieldAborted")
        and post_turn_finalization_succeeded
    ):
        run_maintenance = params.get("runMaintenance") or run_harness_context_engine_maintenance
        await run_maintenance(
            {
                "contextEngine": context_engine,
                "sessionId": params["sessionIdUsed"],
                "sessionKey": params.get("sessionKey"),
                "sessionFile": params["sessionFile"],
                "reason": "turn",
                "sessionManager": params.get("sessionManager"),
                "runtimeContext": params.get("runtimeContext"),
                "runtimeSettings": runtime_settings,
                "config": params.get("config"),
            }
        )

    return {"postTurnFinalizationSucceeded": post_turn_finalization_succeeded}


async def run_harness_context_engine_maintenance(params: dict[str, Any]) -> Any:
    """Run optional transcript maintenance for a harness-owned context engine."""
    try:
        from openclaw.agents.embedded_agent_runner.context_engine_maintenance import (
            run_context_engine_maintenance,
        )

        runtime_settings = _build_harness_context_engine_runtime_settings(params)
        return await run_context_engine_maintenance(
            {
                "contextEngine": params.get("contextEngine"),
                "sessionId": params["sessionId"],
                "sessionKey": params.get("sessionKey"),
                "sessionFile": params["sessionFile"],
                "reason": params["reason"],
                "sessionManager": params.get("sessionManager"),
                "runtimeContext": params.get("runtimeContext"),
                "runtimeSettings": runtime_settings,
                "executionMode": params.get("executionMode"),
                "onDeferredMaintenance": params.get("onDeferredMaintenance"),
                "config": params.get("config"),
            }
        )
    except Exception:
        return None
