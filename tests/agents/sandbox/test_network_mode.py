"""Sandbox network mode policy."""

from openclaw.agents.sandbox.network_mode import (
    get_blocked_network_mode_reason,
    is_dangerous_network_mode,
)


def test_blocks_host():
    assert get_blocked_network_mode_reason(network="host") == "host"


def test_blocks_container_join():
    assert (
        get_blocked_network_mode_reason(network="container:abc123")
        == "container_namespace_join"
    )


def test_dangerous_modes():
    assert is_dangerous_network_mode("host")
    assert is_dangerous_network_mode("container:x")