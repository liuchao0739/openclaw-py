"""ipaddr.js-compatible parsing and range helpers for net-policy.

Internal module — mirrors the subset of ipaddr.js used by packages/net-policy.
"""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Callable
from typing import TypeAlias

ParsedIpAddress: TypeAlias = ipaddress.IPv4Address | ipaddress.IPv6Address

_IPV4_PART = r"(0?\d+|0x[a-f0-9]+)"
_IPV4_FOUR_OCTET_RE = re.compile(
    rf"^{_IPV4_PART}\.{_IPV4_PART}\.{_IPV4_PART}\.{_IPV4_PART}$",
    re.IGNORECASE,
)
_IPV4_THREE_OCTET_RE = re.compile(
    rf"^{_IPV4_PART}\.{_IPV4_PART}\.{_IPV4_PART}$",
    re.IGNORECASE,
)
_IPV4_TWO_OCTET_RE = re.compile(rf"^{_IPV4_PART}\.{_IPV4_PART}$", re.IGNORECASE)
_IPV4_LONG_VALUE_RE = re.compile(rf"^{_IPV4_PART}$", re.IGNORECASE)
_OCTAL_RE = re.compile(r"^0[0-7]+$", re.IGNORECASE)
_HEX_RE = re.compile(r"^0x[a-f0-9]+$", re.IGNORECASE)
_FOUR_PART_DECIMAL_RE = re.compile(r"^(0|[1-9]\d*)(\.(0|[1-9]\d*)){3}$")
_EMBEDDED_IPV4_RE = re.compile(
    r"^(.*:)([^:%]+(?:\.[^:%]+){3})(%[0-9A-Za-z]+)?$",
    re.IGNORECASE,
)

_IPV4_SPECIAL_RANGE_NETWORKS: list[tuple[str, list[ipaddress.IPv4Network]]] = [
    ("unspecified", [ipaddress.ip_network("0.0.0.0/8")]),
    ("broadcast", [ipaddress.ip_network("255.255.255.255/32")]),
    ("multicast", [ipaddress.ip_network("224.0.0.0/4")]),
    ("linkLocal", [ipaddress.ip_network("169.254.0.0/16")]),
    ("loopback", [ipaddress.ip_network("127.0.0.0/8")]),
    ("carrierGradeNat", [ipaddress.ip_network("100.64.0.0/10")]),
    ("private", [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
    ]),
    ("reserved", [
        ipaddress.ip_network("192.0.0.0/24"),
        ipaddress.ip_network("192.0.2.0/24"),
        ipaddress.ip_network("192.88.99.0/24"),
        ipaddress.ip_network("198.18.0.0/15"),
        ipaddress.ip_network("198.51.100.0/24"),
        ipaddress.ip_network("203.0.113.0/24"),
        ipaddress.ip_network("240.0.0.0/4"),
    ]),
    ("as112", [
        ipaddress.ip_network("192.175.48.0/24"),
        ipaddress.ip_network("192.31.196.0/24"),
    ]),
    ("amt", [ipaddress.ip_network("192.52.193.0/24")]),
]

_IPV6_SPECIAL_RANGE_NETWORKS: list[tuple[str, list[ipaddress.IPv6Network]]] = [
    ("unspecified", [ipaddress.ip_network("::/128")]),
    ("linkLocal", [ipaddress.ip_network("fe80::/10")]),
    ("multicast", [ipaddress.ip_network("ff00::/8")]),
    ("loopback", [ipaddress.ip_network("::1/128")]),
    ("uniqueLocal", [ipaddress.ip_network("fc00::/7")]),
    ("ipv4Mapped", [ipaddress.ip_network("::ffff:0:0/96")]),
    ("deprecatedSiteLocal", [ipaddress.ip_network("fec0::/10")]),
    ("discard", [ipaddress.ip_network("100::/64")]),
    ("rfc6145", [ipaddress.ip_network("::ffff:0:0/96")]),
    ("rfc6052", [
        ipaddress.ip_network("64:ff9b::/96"),
        ipaddress.ip_network("64:ff9b:1::/48"),
    ]),
    ("6to4", [ipaddress.ip_network("2002::/16")]),
    ("teredo", [ipaddress.ip_network("2001::/32")]),
    ("benchmarking", [ipaddress.ip_network("2001:2::/48")]),
    ("amt", [ipaddress.ip_network("2001:3::/32")]),
    ("as112v6", [
        ipaddress.ip_network("2001:4:112::/48"),
        ipaddress.ip_network("2620:4f:8000::/48"),
    ]),
    ("deprecatedOrchid", [ipaddress.ip_network("2001:10::/28")]),
    ("orchid2", [ipaddress.ip_network("2001:20::/28")]),
    ("droneRemoteIdProtocolEntityTags", [ipaddress.ip_network("2001:30::/28")]),
    ("segmentRouting", [ipaddress.ip_network("5f00::/16")]),
    ("reserved", [
        ipaddress.ip_network("2001::/23"),
        ipaddress.ip_network("2001:db8::/32"),
        ipaddress.ip_network("3fff::/20"),
    ]),
]

RFC2544_BENCHMARK_NETWORK = ipaddress.ip_network("198.18.0.0/15")


def _parse_int_auto(value: str) -> int:
    if _HEX_RE.fullmatch(value):
        return int(value, 16)
    if value.startswith("0") and len(value) > 1 and value[1].isdigit():
        if _OCTAL_RE.fullmatch(value):
            return int(value, 8)
        raise ValueError(f"ipaddr: cannot parse {value} as octal")
    return int(value, 10)


def _parse_ipv4_octets(string: str) -> list[int] | None:
    match = _IPV4_FOUR_OCTET_RE.fullmatch(string)
    if match:
        return [_parse_int_auto(part) for part in match.groups()]

    match = _IPV4_LONG_VALUE_RE.fullmatch(string)
    if match:
        value = _parse_int_auto(match.group(1))
        if value > 0xFFFFFFFF or value < 0:
            raise ValueError("ipaddr: address outside defined range")
        return [
            (value >> 24) & 0xFF,
            (value >> 16) & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF,
        ]

    match = _IPV4_TWO_OCTET_RE.fullmatch(string)
    if match:
        first = _parse_int_auto(match.group(1))
        value = _parse_int_auto(match.group(2))
        if value > 0xFFFFFF or value < 0:
            raise ValueError("ipaddr: address outside defined range")
        return [
            first,
            (value >> 16) & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF,
        ]

    match = _IPV4_THREE_OCTET_RE.fullmatch(string)
    if match:
        first = _parse_int_auto(match.group(1))
        second = _parse_int_auto(match.group(2))
        value = _parse_int_auto(match.group(3))
        if value > 0xFFFF or value < 0:
            raise ValueError("ipaddr: address outside defined range")
        return [first, second, (value >> 8) & 0xFF, value & 0xFF]

    return None


def _is_ipv4_valid(string: str) -> bool:
    try:
        octets = _parse_ipv4_octets(string)
        if octets is None:
            return False
        _ipv4_from_octets(octets)
        return True
    except (ValueError, ipaddress.AddressValueError):
        return False


def is_valid_four_part_decimal(string: str) -> bool:
    return _is_ipv4_valid(string) and _FOUR_PART_DECIMAL_RE.fullmatch(string) is not None


def _ipv4_from_octets(octets: list[int]) -> ipaddress.IPv4Address:
    return ipaddress.IPv4Address(".".join(str(octet) for octet in octets))


def _parse_ipv4(string: str) -> ipaddress.IPv4Address:
    octets = _parse_ipv4_octets(string)
    if octets is None:
        raise ValueError("ipaddr: string is not formatted like an IPv4 Address")
    return _ipv4_from_octets(octets)


def _is_ipv6_valid(string: str) -> bool:
    if ":" not in string:
        return False
    try:
        _parse_ipv6(string)
        return True
    except (ValueError, ipaddress.AddressValueError):
        return False


def _parse_ipv6(string: str) -> ipaddress.IPv6Address:
    zone_id: str | None = None
    if "%" in string:
        host, zone_id = string.split("%", 1)
        if not zone_id:
            raise ValueError("ipaddr: string is not formatted like an IPv6 Address")
        string = host

    deprecated_transitional = re.fullmatch(
        rf"^::({_IPV4_PART}\.{_IPV4_PART}\.{_IPV4_PART}\.{_IPV4_PART})$",
        string,
        re.IGNORECASE,
    )
    if deprecated_transitional:
        return _parse_ipv6(f"::ffff:{deprecated_transitional.group(1)}")

    transitional = re.fullmatch(
        rf"^((?:{_IPV4_PART}:)+|(?:::)(?:{_IPV4_PART}:)*)({_IPV4_PART})\.({_IPV4_PART})\.({_IPV4_PART})\.({_IPV4_PART})(%[0-9A-Za-z]+)?$",
        string,
        re.IGNORECASE,
    )
    if transitional:
        prefix, o1, o2, o3, o4, zone_suffix = transitional.groups()
        octets = [_parse_int_auto(part) for part in (o1, o2, o3, o4)]
        if any(octet < 0 or octet > 255 for octet in octets):
            raise ValueError("ipaddr: string is not formatted like an IPv6 Address")
        embedded = ".".join(str(octet) for octet in octets)
        rebuilt = f"{prefix}{embedded}{zone_suffix or ''}"
        parsed = parse_ipv6_with_embedded_ipv4(rebuilt)
        if parsed is not None:
            return parsed

    try:
        address = ipaddress.IPv6Address(string)
    except ipaddress.AddressValueError as exc:
        embedded = parse_ipv6_with_embedded_ipv4(string)
        if embedded is not None:
            return embedded
        raise ValueError("ipaddr: string is not formatted like an IPv6 Address") from exc

    return address


def _is_valid(string: str) -> bool:
    return _is_ipv6_valid(string) or _is_ipv4_valid(string)


def _parse(string: str) -> ParsedIpAddress:
    if _is_ipv6_valid(string):
        return _parse_ipv6(string)
    if _is_ipv4_valid(string):
        return _parse_ipv4(string)
    raise ValueError("ipaddr: string is not formatted like an IP Address")


def _subnet_match(
    address: ParsedIpAddress,
    range_list: list[tuple[str, list[ipaddress.IPv4Network | ipaddress.IPv6Network]]],
    *,
    default_name: str = "unicast",
) -> str:
    for range_name, networks in range_list:
        for network in networks:
            if (
                (
                    isinstance(address, ipaddress.IPv4Address)
                    and isinstance(network, ipaddress.IPv4Network)
                )
                or (
                    isinstance(address, ipaddress.IPv6Address)
                    and isinstance(network, ipaddress.IPv6Network)
                )
            ) and address in network:
                return range_name
    return default_name


def ipv4_range(address: ipaddress.IPv4Address) -> str:
    return _subnet_match(address, _IPV4_SPECIAL_RANGE_NETWORKS)


def ipv6_range(address: ipaddress.IPv6Address) -> str:
    return _subnet_match(address, _IPV6_SPECIAL_RANGE_NETWORKS)


def ipv6_parts(address: ipaddress.IPv6Address) -> list[int]:
    packed = address.packed
    return [(packed[index] << 8) | packed[index + 1] for index in range(0, 16, 2)]


def is_ipv4_mapped_address(address: ipaddress.IPv6Address) -> bool:
    return ipv6_range(address) == "ipv4Mapped"


def to_ipv4_address(address: ipaddress.IPv6Address) -> ipaddress.IPv4Address:
    if not is_ipv4_mapped_address(address):
        raise ValueError("ipaddr: trying to convert a generic ipv6 address to ipv4")
    parts = ipv6_parts(address)
    high, low = parts[6], parts[7]
    return decode_ipv4_from_hextets(high, low)


def parse_ipv6_with_embedded_ipv4(raw: str) -> ipaddress.IPv6Address | None:
    if ":" not in raw or "." not in raw:
        return None
    match = _EMBEDDED_IPV4_RE.fullmatch(raw)
    if not match:
        return None
    prefix, embedded_ipv4, zone_suffix = match.groups()
    if not is_valid_four_part_decimal(embedded_ipv4):
        return None
    octets = [int(part) for part in embedded_ipv4.split(".")]
    high = format((octets[0] << 8) | octets[1], "x")
    low = format((octets[2] << 8) | octets[3], "x")
    normalized_ipv6 = f"{prefix}{high}:{low}{zone_suffix or ''}"
    if not _is_ipv6_valid(normalized_ipv6):
        return None
    return _parse_ipv6(normalized_ipv6)


def parse_cidr(candidate: str) -> tuple[ParsedIpAddress, int]:
    if "/" not in candidate:
        raise ValueError("not cidr")
    base_text, prefix_text = candidate.rsplit("/", 1)
    prefix_length = int(prefix_text)
    if _is_ipv6_valid(base_text):
        if not 0 <= prefix_length <= 128:
            raise ValueError("invalid prefix")
        return _parse_ipv6(base_text), prefix_length
    if _is_ipv4_valid(base_text):
        if not 0 <= prefix_length <= 32:
            raise ValueError("invalid prefix")
        return _parse_ipv4(base_text), prefix_length
    raise ValueError("invalid cidr")


def address_in_cidr(address: ParsedIpAddress, base: ParsedIpAddress, prefix_length: int) -> bool:
    if isinstance(address, ipaddress.IPv4Address) and isinstance(base, ipaddress.IPv4Address):
        network = ipaddress.ip_network(f"{base}/{prefix_length}", strict=False)
        return address in network
    if isinstance(address, ipaddress.IPv6Address) and isinstance(base, ipaddress.IPv6Address):
        network = ipaddress.ip_network(f"{base}/{prefix_length}", strict=False)
        return address in network
    return False


def in_rfc2544_benchmark_range(address: ipaddress.IPv4Address) -> bool:
    return address in RFC2544_BENCHMARK_NETWORK


def decode_ipv4_from_hextets(high: int, low: int) -> ipaddress.IPv4Address:
    return _ipv4_from_octets(
        [(high >> 8) & 0xFF, high & 0xFF, (low >> 8) & 0xFF, low & 0xFF]
    )


EmbeddedIpv4Rule = tuple[Callable[[list[int]], bool], Callable[[list[int]], tuple[int, int]]]

EMBEDDED_IPV4_SENTINEL_RULES: list[EmbeddedIpv4Rule] = [
    (
        lambda parts: parts[0:6] == [0, 0, 0, 0, 0, 0],
        lambda parts: (parts[6], parts[7]),
    ),
    (
        lambda parts: parts[0:6] == [0x0064, 0xFF9B, 0x0001, 0, 0, 0],
        lambda parts: (parts[6], parts[7]),
    ),
    (
        lambda parts: parts[0] == 0x2002,
        lambda parts: (parts[1], parts[2]),
    ),
    (
        lambda parts: parts[0] == 0x2001 and parts[1] == 0x0000,
        lambda parts: (parts[6] ^ 0xFFFF, parts[7] ^ 0xFFFF),
    ),
    (
        lambda parts: (parts[4] & 0xFCFF) == 0 and parts[5] == 0x5EFE,
        lambda parts: (parts[6], parts[7]),
    ),
]
