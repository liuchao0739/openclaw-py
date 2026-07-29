"""Google Meet chrome node invoke policy."""

from __future__ import annotations

import importlib
from typing import Any

GOOGLE_MEET_CHROME_NODE_COMMAND = "googlemeet.chrome"

_START_MODES = {"agent", "bidi", "realtime", "transcribe"}


def _as_record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _read_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _read_positive_number(value: Any) -> int | float | None:
    if isinstance(value, (int, float)) and value > 0:
        return value
    return None


def _copy_command(command: list[str] | None) -> list[str] | None:
    return list(command) if command else None


def _denied(message: str, code: str = "GOOGLE_MEET_NODE_POLICY_DENIED") -> dict[str, Any]:
    return {"ok": False, "code": code, "message": message}


def _approved(params: dict[str, Any]) -> dict[str, Any]:
    return {"approved": True, "params": params}


def _build_start_params(params: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    runtime = importlib.import_module("openclaw_extensions.google_meet.src.runtime")
    try:
        url = runtime.normalize_meet_url(params.get("url"))
    except Exception as error:
        return {
            "approved": False,
            "result": _denied(
                str(error) if isinstance(error, Exception) else "googlemeet.chrome start requires url"
            ),
        }
    mode = _read_string(params.get("mode"))
    if mode and mode not in _START_MODES:
        return {"approved": False, "result": _denied(f"googlemeet.chrome start mode is unsupported: {mode}")}
    start_params: dict[str, Any] = {
        "action": "start",
        "url": url,
        "launch": False if params.get("launch") is False else config["chrome"]["launch"],
        "browserProfile": config["chrome"].get("browserProfile"),
        "joinTimeoutMs": config["chrome"]["joinTimeoutMs"],
    }
    if mode:
        start_params["mode"] = mode
    audio_input_command = _copy_command(config["chrome"].get("audioInputCommand"))
    if audio_input_command:
        start_params["audioInputCommand"] = audio_input_command
    audio_output_command = _copy_command(config["chrome"].get("audioOutputCommand"))
    if audio_output_command:
        start_params["audioOutputCommand"] = audio_output_command
    audio_bridge_command = _copy_command(config["chrome"].get("audioBridgeCommand"))
    if audio_bridge_command:
        start_params["audioBridgeCommand"] = audio_bridge_command
    audio_bridge_health_command = _copy_command(config["chrome"].get("audioBridgeHealthCommand"))
    if audio_bridge_health_command:
        start_params["audioBridgeHealthCommand"] = audio_bridge_health_command
    return _approved(start_params)


def _build_forward_params(params: dict[str, Any]) -> dict[str, Any] | None:
    action = _read_string(params.get("action"))
    if action == "setup":
        return {"action": action}
    if action == "status":
        bridge_id = _read_string(params.get("bridgeId"))
        return {"action": action, "bridgeId": bridge_id} if bridge_id else {"action": action}
    if action in ("list", "stopByUrl"):
        forwarded: dict[str, Any] = {"action": action}
        url = _read_string(params.get("url"))
        mode = _read_string(params.get("mode"))
        if url:
            forwarded["url"] = url
        if mode:
            forwarded["mode"] = mode
        if action == "stopByUrl":
            except_bridge_id = _read_string(params.get("exceptBridgeId"))
            if except_bridge_id:
                forwarded["exceptBridgeId"] = except_bridge_id
        return forwarded
    if action == "pullAudio":
        forwarded = {"action": action}
        bridge_id = _read_string(params.get("bridgeId"))
        timeout_ms = _read_positive_number(params.get("timeoutMs"))
        if bridge_id:
            forwarded["bridgeId"] = bridge_id
        if timeout_ms is not None:
            forwarded["timeoutMs"] = timeout_ms
        return forwarded
    if action == "pushAudio":
        forwarded = {"action": action}
        bridge_id = _read_string(params.get("bridgeId"))
        base64 = _read_string(params.get("base64"))
        if bridge_id:
            forwarded["bridgeId"] = bridge_id
        if base64:
            forwarded["base64"] = base64
        return forwarded
    if action in ("clearAudio", "stop"):
        bridge_id = _read_string(params.get("bridgeId"))
        return {"action": action, "bridgeId": bridge_id} if bridge_id else {"action": action}
    return None


def create_google_meet_chrome_node_invoke_policy(config: dict[str, Any]) -> dict[str, Any]:
    async def handle(ctx: Any) -> Any:
        if ctx["command"] != GOOGLE_MEET_CHROME_NODE_COMMAND:
            return _denied(f"unsupported Google Meet node command: {ctx['command']}")
        params = _as_record(ctx.get("params"))
        action = _read_string(params.get("action"))
        if action == "start":
            decision = _build_start_params(params, config)
        else:
            forward_params = _build_forward_params(params)
            decision = (
                _approved(forward_params)
                if forward_params is not None
                else {"approved": False, "result": _denied("unsupported googlemeet.chrome action")}
            )
        if not decision.get("approved"):
            return decision["result"]
        return await ctx["invokeNode"]({"params": decision["params"]})

    return {
        "commands": [GOOGLE_MEET_CHROME_NODE_COMMAND],
        "dangerous": True,
        "handle": handle,
    }
