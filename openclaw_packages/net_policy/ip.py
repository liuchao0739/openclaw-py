"""Network policy IP parsing and SSRF classification helpers.

Mirrors packages/net-policy/src/ip.ts.
"""

from __future__ import annotations

import ipaddress
import re
from typing import TypedDict

from openclaw.packages.normalization_core import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
)

from ._ipaddr_compat import (
    EMBEDDED_IPV4_SENTINEL_RULES,
    ParsedIpAddress,
    _is_ipv4_valid,
    _is_ipv6_valid,
    _is_valid,
    _parse,
    _parse_ipv4,
    _parse_ipv6,
    address_in_cidr,
    decode_ipv4_from_hextets,
    in_rfc2544_benchmark_range,
    ipv4_range,
    ipv6_parts,
    ipv6_range,
    is_ipv4_mapped_address,
    is_valid_four_part_decimal,
    parse_cidr,
    parse_ipv6_with_embedded_ipv4,
    to_ipv4_address,
)

__all__ = [
    "Ipv4SpecialUseBlockOptions",
    "Ipv6SpecialUseBlockOptions",
    "ParsedIpAddress",
    "extract_embedded_ipv4_from_ipv6",
    "is_blocked_special_use_ipv4_address",
    "is_blocked_special_use_ipv6_address",
    "is_canonical_dotted_decimal_ipv4",
    "is_carrier_grade_nat_ipv4_address",
    "is_cloud_metadata_ip_address",
    "is_ip_in_cidr",
    "is_ipv4_address",
    "is_ipv6_address",
    "is_legacy_ipv4_literal",
    "is_link_local_ip_address",
    "is_loopback_ip_address",
    "is_private_or_loopback_ip_address",
    "is_rfc1918_ipv4_address",
    "normalize_ip_address",
    "parse_canonical_ip_address",
    "parse_loose_ip_address",
]

BLOCKED_IPV4_SPECIAL_USE_RANGES = frozenset({
    "unspecified",
    "broadcast",
    "multicast",
    "linkLocal",
    "private",
    "reserved",
    "loopback",
    "carrierGradeNat",
})

PRIVATE_OR_LOOPBACK_IPV4_RANGES = frozenset({
    "loopback",
    "private",
    "linkLocal",
    "carrierGradeNat",
})

BLOCKED_IPV6_SPECIAL_USE_RANGES = frozenset({
    "unspecified",
    "loopback",
    "linkLocal",
    "uniqueLocal",
    "multicast",
    "reserved",
    "benchmarking",
    "discard",
    "orchid2",
})

CLOUD_METADATA_IP_ADDRESSES = frozenset({"100.100.100.200", "fd00:ec2::254"})

_NUMERIC_IPV4_LITERAL_PART_RE = re.compile(r"^[0-9]+$|^0x[0-9a-f]+$", re.IGNORECASE)


class Ipv4SpecialUseBlockOptions(TypedDict, total=False):
    allow_rfc2544_benchmark_range: bool


class Ipv6SpecialUseBlockOptions(TypedDict, total=False):
    allow_unique_local_range: bool


def is_ipv4_address(address: ParsedIpAddress) -> bool:
    return isinstance(address, ipaddress.IPv4Address)


def is_ipv6_address(address: ParsedIpAddress) -> bool:
    return isinstance(address, ipaddress.IPv6Address)


def _strip_ipv6_brackets(value: str) -> str:
    if value.startswith("[") and value.endswith("]"):
        return value[1:-1]
    return value


def _normalize_ipv4_mapped_address(address: ParsedIpAddress) -> ParsedIpAddress:
    if not is_ipv6_address(address):
        return address
    if not is_ipv4_mapped_address(address):
        return address
    return to_ipv4_address(address)


def _normalize_ip_parse_input(raw: str | None) -> str | None:
    trimmed = normalize_optional_string(raw)
    if not trimmed:
        return None
    return _strip_ipv6_brackets(trimmed)


def parse_canonical_ip_address(raw: str | None) -> ParsedIpAddress | None:
    normalized = _normalize_ip_parse_input(raw)
    if not normalized:
        return None
    if _is_ipv4_valid(normalized):
        if not is_valid_four_part_decimal(normalized):
            return None
        return _parse_ipv4(normalized)
    if _is_ipv6_valid(normalized):
        return _parse_ipv6(normalized)
    return parse_ipv6_with_embedded_ipv4(normalized)


def parse_loose_ip_address(raw: str | None) -> ParsedIpAddress | None:
    normalized = _normalize_ip_parse_input(raw)
    if not normalized:
        return None
    if _is_valid(normalized):
        return _parse(normalized)
    return parse_ipv6_with_embedded_ipv4(normalized)


def normalize_ip_address(raw: str | None) -> str | None:
    parsed = parse_canonical_ip_address(raw)
    if not parsed:
        return None
    normalized = _normalize_ipv4_mapped_address(parsed)
    return normalize_lowercase_string_or_empty(str(normalized))


def is_canonical_dotted_decimal_ipv4(raw: str | None) -> bool:
    trimmed = normalize_optional_string(raw)
    if not trimmed:
        return False
    normalized = _strip_ipv6_brackets(trimmed)
    if not normalized:
        return False
    return is_valid_four_part_decimal(normalized)


def is_legacy_ipv4_literal(raw: str | None) -> bool:
    trimmed = normalize_optional_string(raw)
    if not trimmed:
        return False
    normalized = _strip_ipv6_brackets(trimmed)
    if not normalized or ":" in normalized:
        return False
    if is_canonical_dotted_decimal_ipv4(normalized):
        return False
    parts = normalized.split(".")
    if not parts or len(parts) > 4:
        return False
    if any(not part for part in parts):
        return False
    return all(_NUMERIC_IPV4_LITERAL_PART_RE.fullmatch(part) for part in parts)


def is_loopback_ip_address(raw: str | None) -> bool:
    parsed = parse_canonical_ip_address(raw)
    if not parsed:
        return False
    normalized = _normalize_ipv4_mapped_address(parsed)
    if is_ipv4_address(normalized):
        return ipv4_range(normalized) == "loopback"
    return ipv6_range(normalized) == "loopback"


def is_link_local_ip_address(raw: str | None) -> bool:
    parsed = parse_loose_ip_address(raw)
    if not parsed:
        return False
    normalized = _normalize_ipv4_mapped_address(parsed)
    if is_ipv4_address(normalized):
        return ipv4_range(normalized) == "linkLocal"
    embedded_ipv4 = extract_embedded_ipv4_from_ipv6(normalized)
    if embedded_ipv4 is not None and ipv4_range(embedded_ipv4) == "linkLocal":
        return True
    return ipv6_range(normalized) == "linkLocal"


def is_cloud_metadata_ip_address(raw: str | None) -> bool:
    parsed = parse_loose_ip_address(raw)
    if not parsed:
        return False
    normalized = _normalize_ipv4_mapped_address(parsed)
    if is_ipv6_address(normalized):
        embedded_ipv4 = extract_embedded_ipv4_from_ipv6(normalized)
        if embedded_ipv4 is not None and str(embedded_ipv4) in CLOUD_METADATA_IP_ADDRESSES:
            return True
    return str(normalized) in CLOUD_METADATA_IP_ADDRESSES


def is_private_or_loopback_ip_address(raw: str | None) -> bool:
    parsed = parse_canonical_ip_address(raw)
    if not parsed:
        return False
    normalized = _normalize_ipv4_mapped_address(parsed)
    if is_ipv4_address(normalized):
        return ipv4_range(normalized) in PRIVATE_OR_LOOPBACK_IPV4_RANGES
    return is_blocked_special_use_ipv6_address(normalized)


def is_blocked_special_use_ipv6_address(
    address: ipaddress.IPv6Address,
    options: Ipv6SpecialUseBlockOptions | None = None,
) -> bool:
    opts = options or {}
    range_name = ipv6_range(address)
    if range_name == "uniqueLocal" and opts.get("allow_unique_local_range") is True:
        return False
    if range_name in BLOCKED_IPV6_SPECIAL_USE_RANGES:
        return True
    return (ipv6_parts(address)[0] & 0xFFC0) == 0xFEC0


def is_rfc1918_ipv4_address(raw: str | None) -> bool:
    parsed = parse_canonical_ip_address(raw)
    if not parsed or not is_ipv4_address(parsed):
        return False
    return ipv4_range(parsed) == "private"


def is_carrier_grade_nat_ipv4_address(raw: str | None) -> bool:
    parsed = parse_canonical_ip_address(raw)
    if not parsed or not is_ipv4_address(parsed):
        return False
    return ipv4_range(parsed) == "carrierGradeNat"


def is_blocked_special_use_ipv4_address(
    address: ipaddress.IPv4Address,
    options: Ipv4SpecialUseBlockOptions | None = None,
) -> bool:
    opts = options or {}
    in_benchmark_range = in_rfc2544_benchmark_range(address)
    if in_benchmark_range and opts.get("allow_rfc2544_benchmark_range") is True:
        return False
    return ipv4_range(address) in BLOCKED_IPV4_SPECIAL_USE_RANGES or in_benchmark_range


def extract_embedded_ipv4_from_ipv6(
    address: ipaddress.IPv6Address,
) -> ipaddress.IPv4Address | None:
    if is_ipv4_mapped_address(address):
        return to_ipv4_address(address)
    range_name = ipv6_range(address)
    parts = ipv6_parts(address)
    if range_name == "rfc6145":
        return decode_ipv4_from_hextets(parts[6], parts[7])
    if range_name == "rfc6052":
        return decode_ipv4_from_hextets(parts[6], parts[7])
    for matches, to_hextets in EMBEDDED_IPV4_SENTINEL_RULES:
        if not matches(parts):
            continue
        high, low = to_hextets(parts)
        return decode_ipv4_from_hextets(high, low)
    return None


def is_ip_in_cidr(ip: str, cidr: str) -> bool:
    normalized_ip = parse_canonical_ip_address(ip)
    if not normalized_ip:
        return False
    candidate = cidr.strip()
    if not candidate:
        return False
    comparable_ip = _normalize_ipv4_mapped_address(normalized_ip)
    if "/" not in candidate:
        exact = parse_canonical_ip_address(candidate)
        if not exact:
            return False
        comparable_exact = _normalize_ipv4_mapped_address(exact)
        return (
            comparable_ip.version == comparable_exact.version
            and str(comparable_ip) == str(comparable_exact)
        )
    try:
        base_address, prefix_length = parse_cidr(candidate)
    except (ValueError, ipaddress.AddressValueError):
        return False
    comparable_base = _normalize_ipv4_mapped_address(base_address)
    if comparable_ip.version != comparable_base.version:
        return False
    try:
        return address_in_cidr(comparable_ip, comparable_base, prefix_length)
    except (ValueError, ipaddress.AddressValueError):
        return False
