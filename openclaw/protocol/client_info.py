"""Gateway client identity contract."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class GatewayClientId(StrEnum):
    WEBCHAT_UI = "webchat-ui"
    CONTROL_UI = "openclaw-control-ui"
    TUI = "openclaw-tui"
    WEBCHAT = "webchat"
    CLI = "cli"
    GATEWAY_CLIENT = "gateway-client"
    MACOS_APP = "openclaw-macos"
    IOS_APP = "openclaw-ios"
    ANDROID_APP = "openclaw-android"
    NODE_HOST = "node-host"
    TEST = "test"
    FINGERPRINT = "fingerprint"
    PROBE = "openclaw-probe"


class GatewayClientMode(StrEnum):
    WEBCHAT = "webchat"
    CLI = "cli"
    UI = "ui"
    BACKEND = "backend"
    NODE = "node"
    PROBE = "probe"
    TEST = "test"


class GatewayClientCap(StrEnum):
    TOOL_EVENTS = "tool-events"


class GatewayClientInfo(BaseModel):
    id: GatewayClientId
    version: str
    platform: str
    mode: GatewayClientMode
    display_name: str | None = Field(default=None, alias="displayName")
    device_family: str | None = Field(default=None, alias="deviceFamily")
    model_identifier: str | None = Field(default=None, alias="modelIdentifier")
    instance_id: str | None = Field(default=None, alias="instanceId")

    model_config = {"populate_by_name": True}


ConnectRecoveryNextStep = Literal[
    "retry_with_device_token",
    "update_auth_configuration",
    "update_auth_credentials",
    "wait_then_retry",
    "review_auth_configuration",
]
