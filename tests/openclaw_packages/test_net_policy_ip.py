"""Tests for net-policy IP helpers."""

from __future__ import annotations

from openclaw_packages.net_policy import (
    blocked_ipv6_multicast_literals,
    extract_embedded_ipv4_from_ipv6,
    is_blocked_special_use_ipv4_address,
    is_blocked_special_use_ipv6_address,
    is_canonical_dotted_decimal_ipv4,
    is_carrier_grade_nat_ipv4_address,
    is_cloud_metadata_ip_address,
    is_ip_in_cidr,
    is_ipv4_address,
    is_ipv6_address,
    is_legacy_ipv4_literal,
    is_link_local_ip_address,
    is_loopback_ip_address,
    is_private_or_loopback_ip_address,
    is_rfc1918_ipv4_address,
    normalize_ip_address,
    parse_canonical_ip_address,
    parse_loose_ip_address,
)


def test_distinguishes_canonical_dotted_ipv4_from_legacy_forms() -> None:
    assert is_canonical_dotted_decimal_ipv4("127.0.0.1") is True
    assert is_canonical_dotted_decimal_ipv4("0177.0.0.1") is False
    assert is_legacy_ipv4_literal("0177.0.0.1") is True
    assert is_legacy_ipv4_literal("127.1") is True
    assert is_legacy_ipv4_literal("example.com") is False


def test_matches_both_ipv4_and_ipv6_cidrs() -> None:
    assert is_ip_in_cidr("10.42.0.59", "10.42.0.0/24") is True
    assert is_ip_in_cidr("10.43.0.59", "10.42.0.0/24") is False
    assert is_ip_in_cidr("2001:db8::1234", "2001:db8::/32") is True
    assert is_ip_in_cidr("2001:db9::1234", "2001:db8::/32") is False
    assert is_ip_in_cidr("::ffff:127.0.0.1", "127.0.0.1") is True
    assert is_ip_in_cidr("127.0.0.1", "::ffff:127.0.0.2") is False


def test_extracts_embedded_ipv4_for_transition_prefixes() -> None:
    cases = [
        ("::ffff:127.0.0.1", "127.0.0.1"),
        ("::127.0.0.1", "127.0.0.1"),
        ("64:ff9b::8.8.8.8", "8.8.8.8"),
        ("64:ff9b:1::10.0.0.1", "10.0.0.1"),
        ("2002:0808:0808::", "8.8.8.8"),
        ("2001::f7f7:f7f7", "8.8.8.8"),
        ("2001:4860:1::5efe:7f00:1", "127.0.0.1"),
    ]
    for ipv6_literal, expected_ipv4 in cases:
        parsed = parse_canonical_ip_address(ipv6_literal)
        assert parsed is not None, ipv6_literal
        assert is_ipv6_address(parsed), ipv6_literal
        embedded = extract_embedded_ipv4_from_ipv6(parsed)
        assert embedded is not None, ipv6_literal
        assert str(embedded) == expected_ipv4, ipv6_literal


def test_treats_blocked_ipv6_classes_as_private_internal() -> None:
    assert is_private_or_loopback_ip_address("fec0::1") is True
    assert is_private_or_loopback_ip_address("2001:db8::1") is True
    assert is_private_or_loopback_ip_address("2001:2::1") is True
    assert is_private_or_loopback_ip_address("100::1") is True
    assert is_private_or_loopback_ip_address("2001:20::1") is True
    for literal in blocked_ipv6_multicast_literals:
        assert is_private_or_loopback_ip_address(literal) is True
    assert is_private_or_loopback_ip_address("2001:4860:4860::8888") is False


def test_normalizes_canonical_ip_strings_and_loopback_detection() -> None:
    assert normalize_ip_address("[::FFFF:127.0.0.1]") == "127.0.0.1"
    assert normalize_ip_address("  [2001:DB8::1]  ") == "2001:db8::1"
    assert is_loopback_ip_address("::ffff:127.0.0.1") is True
    assert is_loopback_ip_address("198.18.0.1") is False


def test_detects_link_local_addresses_without_treating_private_ranges_as_link_local() -> None:
    assert is_link_local_ip_address("169.254.169.254") is True
    assert is_link_local_ip_address("::ffff:169.254.169.254") is True
    assert is_link_local_ip_address("2852039166") is True
    assert is_link_local_ip_address("0xa9fea9fe") is True
    assert is_link_local_ip_address("0xa9.0xfe.0xa9.0xfe") is True
    assert is_link_local_ip_address("64:ff9b::169.254.169.254") is True
    assert is_link_local_ip_address("64:ff9b:1::a9fe:a9fe") is True
    assert is_link_local_ip_address("2002:a9fe:a9fe::") is True
    assert is_link_local_ip_address("fe80::1%lo0") is True
    assert is_link_local_ip_address("[fe80::1]") is True
    assert is_link_local_ip_address("10.0.0.5") is False
    assert is_link_local_ip_address("127.0.0.1") is False
    assert is_link_local_ip_address("fd00::1") is False


def test_detects_known_non_link_local_cloud_metadata_ips() -> None:
    assert is_cloud_metadata_ip_address("100.100.100.200") is True
    assert is_cloud_metadata_ip_address("::ffff:100.100.100.200") is True
    assert is_cloud_metadata_ip_address("64:ff9b::100.100.100.200") is True
    assert is_cloud_metadata_ip_address("64:ff9b:1::6464:64c8") is True
    assert is_cloud_metadata_ip_address("2002:6464:64c8::") is True
    assert is_cloud_metadata_ip_address("1684301000") is True
    assert is_cloud_metadata_ip_address("fd00:ec2::254") is True
    assert is_cloud_metadata_ip_address("[fd00:ec2::254]") is True
    assert is_cloud_metadata_ip_address("100.100.100.201") is False
    assert is_cloud_metadata_ip_address("169.254.169.254") is False
    assert is_cloud_metadata_ip_address("fd00::1") is False


def test_parses_loose_legacy_ipv4_literals_that_canonical_parsing_rejects() -> None:
    assert parse_canonical_ip_address("0177.0.0.1") is None
    assert str(parse_loose_ip_address("0177.0.0.1")) == "127.0.0.1"
    assert str(parse_loose_ip_address("[::1]")) == "::1"


def test_classifies_rfc1918_and_carrier_grade_nat_ipv4_ranges() -> None:
    assert is_rfc1918_ipv4_address("10.42.0.59") is True
    assert is_rfc1918_ipv4_address("100.64.0.1") is False
    assert is_carrier_grade_nat_ipv4_address("100.64.0.1") is True
    assert is_carrier_grade_nat_ipv4_address("10.42.0.59") is False


def test_blocks_special_use_ipv4_ranges_while_allowing_optional_rfc2544_benchmark() -> None:
    loopback = parse_canonical_ip_address("127.0.0.1")
    benchmark = parse_canonical_ip_address("198.18.0.1")
    assert loopback is not None and is_ipv4_address(loopback)
    assert benchmark is not None and is_ipv4_address(benchmark)
    assert is_blocked_special_use_ipv4_address(loopback) is True
    assert is_blocked_special_use_ipv4_address(benchmark) is True
    assert (
        is_blocked_special_use_ipv4_address(
            benchmark,
            {"allow_rfc2544_benchmark_range": True},
        )
        is False
    )


def test_blocks_ipv6_unique_local_addresses_by_default_and_exempts_on_opt_in() -> None:
    ula = parse_canonical_ip_address("fc00::1")
    assert ula is not None and is_ipv6_address(ula)
    assert is_blocked_special_use_ipv6_address(ula) is True
    assert is_blocked_special_use_ipv6_address(ula, {}) is True
    assert is_blocked_special_use_ipv6_address(ula, {"allow_unique_local_range": False}) is True
    assert is_blocked_special_use_ipv6_address(ula, {"allow_unique_local_range": True}) is False


def test_unique_local_exemption_does_not_bleed_into_other_special_use_ipv6_ranges() -> None:
    loopback = parse_canonical_ip_address("::1")
    multicast = parse_canonical_ip_address("ff02::1")
    site_local = parse_canonical_ip_address("fec0::1")
    assert loopback is not None and is_ipv6_address(loopback)
    assert multicast is not None and is_ipv6_address(multicast)
    assert site_local is not None and is_ipv6_address(site_local)
    for options in ({}, {"allow_unique_local_range": True}):
        assert is_blocked_special_use_ipv6_address(loopback, options) is True
        assert is_blocked_special_use_ipv6_address(multicast, options) is True
        assert is_blocked_special_use_ipv6_address(site_local, options) is True
