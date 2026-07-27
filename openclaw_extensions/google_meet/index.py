"""Google Meet plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from openclaw.cli.gateway_cli import call_gateway_cli
from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry

from openclaw_extensions.google_meet.src.config import (
    GoogleMeetConfig,
    GoogleMeetMode,
    GoogleMeetTransport,
    resolve_google_meet_config,
    resolve_google_meet_gateway_operation_timeout_ms,
)

_google_meet_tool_deps: dict[str, Any] = {
    "call_gateway_from_cli": call_gateway_cli,
    "platform": lambda: sys.platform,
}


def _normalize_transport(value: Any) -> GoogleMeetTransport | None:
    if value in ("chrome", "chrome-node", "twilio"):
        return value
    return None


def _normalize_mode(value: Any) -> GoogleMeetMode | None:
    if value == "realtime":
        return "agent"
    if value in ("agent", "bidi", "transcribe"):
        return value
    return None


def _is_google_meet_talk_back_mode(mode: GoogleMeetMode) -> bool:
    return mode in ("agent", "bidi")


def _should_join_created_meet(raw: Mapping[str, Any]) -> bool:
    join = raw.get("join")
    return join is not False and join != "false"


def is_google_meet_agent_tool_action_unsupported_on_host(params: Mapping[str, Any]) -> bool:
    platform = params.get("platform") or _google_meet_tool_deps["platform"]()
    if platform == "darwin":
        return False

    raw = params["raw"]
    action = raw.get("action")
    if action not in ("join", "test_speech") and not (
        action == "create" and _should_join_created_meet(raw)
    ):
        return False

    config = params["config"]
    transport = _normalize_transport(raw.get("transport")) or config.default_transport
    if action == "test_speech":
        mode: GoogleMeetMode = "agent"
    else:
        mode = _normalize_mode(raw.get("mode")) or config.default_mode

    return transport == "chrome" and _is_google_meet_talk_back_mode(mode)


def set_call_gateway_from_cli_for_tests(
    next_call: Callable[..., Awaitable[Any]] | None = None,
) -> None:
    _google_meet_tool_deps["call_gateway_from_cli"] = next_call or call_gateway_cli


def set_platform_for_tests(next_platform: Callable[[], str] | None = None) -> None:
    _google_meet_tool_deps["platform"] = next_platform or (lambda: sys.platform)


testing = {
    "setCallGatewayFromCliForTests": set_call_gateway_from_cli_for_tests,
    "setPlatformForTests": set_platform_for_tests,
    "isGoogleMeetAgentToolActionUnsupportedOnHost": is_google_meet_agent_tool_action_unsupported_on_host,
    "resolveGoogleMeetGatewayOperationTimeoutMs": resolve_google_meet_gateway_operation_timeout_ms,
}

__testing__ = testing


def _register(_api: OpenClawPluginApi) -> None:
    return None


google_meet_config_schema = {
    "parse": resolve_google_meet_config,
}


default = define_plugin_entry(
    id="google-meet",
    name="Google Meet",
    description="OpenClaw Google Meet participant plugin for joining calls through Chrome or Twilio transports.",
    config_schema=google_meet_config_schema,
    register=_register,
)
