"""Tests for Google Meet plugin testing exports."""

from __future__ import annotations

from openclaw_extensions.google_meet.index import testing
from openclaw_extensions.google_meet.src.config import resolve_google_meet_config


def test_testing_exposes_gateway_timeout_helper() -> None:
    assert testing["resolveGoogleMeetGatewayOperationTimeoutMs"](resolve_google_meet_config({})) == 60_000


def test_is_google_meet_agent_tool_action_unsupported_on_host_blocks_linux_chrome_join() -> None:
    checker = testing["isGoogleMeetAgentToolActionUnsupportedOnHost"]
    config = resolve_google_meet_config({})

    assert checker({"config": config, "raw": {"action": "join"}, "platform": "linux"}) is True
    assert checker({"config": config, "raw": {"action": "join", "mode": "transcribe"}, "platform": "linux"}) is False
    assert checker(
        {"config": config, "raw": {"action": "join", "transport": "chrome-node"}, "platform": "linux"}
    ) is False


def test_is_google_meet_agent_tool_action_unsupported_on_host_allows_darwin() -> None:
    checker = testing["isGoogleMeetAgentToolActionUnsupportedOnHost"]
    config = resolve_google_meet_config({})

    assert checker({"config": config, "raw": {"action": "join"}, "platform": "darwin"}) is False


def test_set_platform_for_tests_overrides_host_platform() -> None:
    testing["setPlatformForTests"](lambda: "linux")
    checker = testing["isGoogleMeetAgentToolActionUnsupportedOnHost"]
    config = resolve_google_meet_config({})
    assert checker({"config": config, "raw": {"action": "join"}}) is True
    testing["setPlatformForTests"](None)


def test_set_call_gateway_from_cli_for_tests_restores_default() -> None:
    import asyncio

    seen: list[str] = []

    async def stub(method: str, *_args: object, **_kwargs: object) -> dict[str, str]:
        seen.append(method)
        return {"ok": True}

    testing["setCallGatewayFromCliForTests"](stub)
    gateway = testing["setCallGatewayFromCliForTests"].__globals__["_google_meet_tool_deps"]["call_gateway_from_cli"]
    asyncio.run(gateway("googlemeet.status", {}, {}))
    assert seen == ["googlemeet.status"]
    testing["setCallGatewayFromCliForTests"](None)
