"""IPv4 validation helpers for custom bind mode.

Mirrors packages/net-policy/src/ipv4.ts.
"""

from __future__ import annotations

from .ip import is_canonical_dotted_decimal_ipv4

__all__ = [
    "validate_dotted_decimal_ipv4_input",
    "validate_ipv4_address_input",
]


def validate_dotted_decimal_ipv4_input(value: str | None) -> str | None:
    if not value:
        return "IP address is required for custom bind mode"
    if is_canonical_dotted_decimal_ipv4(value):
        return None
    return "Invalid IPv4 address (e.g., 192.168.1.100)"


def validate_ipv4_address_input(value: str | None) -> str | None:
    return validate_dotted_decimal_ipv4_input(value)
