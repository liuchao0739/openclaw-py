"""Test fixtures for net-policy IP helpers.

Mirrors packages/net-policy/src/ip-test-fixtures.ts.
"""

from __future__ import annotations

blocked_ipv6_multicast_literals = ("ff02::1", "ff05::1:3", "[ff02::1]")

__all__ = ["blocked_ipv6_multicast_literals"]
