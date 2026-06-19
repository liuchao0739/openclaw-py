"""Tests for gateway protocol."""

from __future__ import annotations

from openclaw.protocol.client_info import GatewayClientId, GatewayClientInfo, GatewayClientMode
from openclaw.protocol.connect_error_details import (
    ConnectErrorDetailCode,
    normalize_connect_error_details,
)
from openclaw.protocol.schema import HelloRequest, HelloResponse
from openclaw.protocol.version import MIN_CLIENT_PROTOCOL_VERSION, PROTOCOL_VERSION


def test_protocol_version_constants() -> None:
    assert PROTOCOL_VERSION == 4
    assert MIN_CLIENT_PROTOCOL_VERSION == 4


def test_hello_roundtrip() -> None:
    req = HelloRequest(
        client=GatewayClientInfo(
            id=GatewayClientId.CLI,
            version="0.1.0",
            platform="darwin",
            mode=GatewayClientMode.CLI,
        )
    )
    payload = req.model_dump(by_alias=True)
    assert payload["protocolVersion"] == 4
    assert payload["client"]["id"] == "cli"

    resp = HelloResponse(server_version="0.1.0")
    assert resp.model_dump(by_alias=True)["type"] == "hello-ok"


def test_normalize_connect_error_details() -> None:
    details = normalize_connect_error_details(
        {"code": "AUTH_REQUIRED", "message": " token missing ", "scopes": ["admin", "  "]}
    )
    assert details.code == ConnectErrorDetailCode.AUTH_REQUIRED
    assert details.message == "token missing"
    assert details.scopes == ["admin"]
