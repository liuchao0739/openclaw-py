"""Tests for gateway root modules."""

import asyncio

from openclaw.gateway.control_plane_identity import normalize_control_plane_identity_part
from openclaw.gateway.device_auth import (
    build_device_auth_payload,
    build_device_auth_payload_v3,
    normalize_device_metadata_for_auth,
)
from openclaw.gateway.event_loop_ready import wait_for_event_loop_ready


class TestControlPlaneIdentity:
    def test_valid_string(self):
        assert normalize_control_plane_identity_part("agent-1", "fallback") == "agent-1"

    def test_trims_whitespace(self):
        assert normalize_control_plane_identity_part("  agent-1  ", "fallback") == "agent-1"

    def test_empty_string(self):
        assert normalize_control_plane_identity_part("", "fallback") == "fallback"

    def test_whitespace_only(self):
        assert normalize_control_plane_identity_part("   ", "fallback") == "fallback"

    def test_non_string(self):
        assert normalize_control_plane_identity_part(123, "fallback") == "fallback"
        assert normalize_control_plane_identity_part(None, "fallback") == "fallback"
        assert normalize_control_plane_identity_part(True, "fallback") == "fallback"


class TestDeviceAuth:
    def test_build_payload(self):
        result = build_device_auth_payload({"deviceId": "dev-1"})
        assert result["deviceId"] == "dev-1"

    def test_build_payload_v3(self):
        result = build_device_auth_payload_v3({"deviceId": "dev-1", "version": 3})
        assert result["deviceId"] == "dev-1"

    def test_normalize_metadata(self):
        result = normalize_device_metadata_for_auth({"a": 1, "b": None, "c": "x"})
        assert result == {"a": 1, "c": "x"}

    def test_normalize_metadata_non_dict(self):
        assert normalize_device_metadata_for_auth(None) == {}
        assert normalize_device_metadata_for_auth("string") == {}


class TestEventLoopReady:
    def test_returns_ready(self):
        result = asyncio.run(wait_for_event_loop_ready())
        assert result["ready"] is True
        assert "elapsed_ms" in result
