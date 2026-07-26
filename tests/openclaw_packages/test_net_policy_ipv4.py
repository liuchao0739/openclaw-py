"""Tests for net-policy IPv4 validation."""

from __future__ import annotations

from openclaw_packages.net_policy import (
    validate_dotted_decimal_ipv4_input,
    validate_ipv4_address_input,
)


def test_requires_a_value_for_custom_bind_mode() -> None:
    assert validate_dotted_decimal_ipv4_input(None) == "IP address is required for custom bind mode"
    assert validate_dotted_decimal_ipv4_input("") == "IP address is required for custom bind mode"
    assert validate_dotted_decimal_ipv4_input("   ") == "Invalid IPv4 address (e.g., 192.168.1.100)"


def test_accepts_canonical_dotted_decimal_ipv4_only() -> None:
    assert validate_dotted_decimal_ipv4_input("0.0.0.0") is None
    assert validate_dotted_decimal_ipv4_input("192.168.1.100") is None
    assert validate_dotted_decimal_ipv4_input(" 192.168.1.100 ") is None
    assert validate_dotted_decimal_ipv4_input("0177.0.0.1") == (
        "Invalid IPv4 address (e.g., 192.168.1.100)"
    )
    assert validate_dotted_decimal_ipv4_input("[192.168.1.100]") is None
    assert (
        validate_dotted_decimal_ipv4_input("127.1") == "Invalid IPv4 address (e.g., 192.168.1.100)"
    )
    assert validate_dotted_decimal_ipv4_input("example.com") == (
        "Invalid IPv4 address (e.g., 192.168.1.100)"
    )


def test_keeps_backward_compatible_alias_wired_to_same_validation() -> None:
    assert validate_ipv4_address_input("192.168.1.100") is None
    assert validate_ipv4_address_input("bad-ip") == "Invalid IPv4 address (e.g., 192.168.1.100)"
