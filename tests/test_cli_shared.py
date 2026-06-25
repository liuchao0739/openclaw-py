"""Tests for cli/shared — port parsing."""

from __future__ import annotations

from openclaw.cli.shared import MAX_TCP_PORT, parse_port


class TestParsePort:
    def test_valid_port(self):
        assert parse_port(8080) == 8080
        assert parse_port("8080") == 8080
        assert parse_port(1) == 1
        assert parse_port(MAX_TCP_PORT) == MAX_TCP_PORT

    def test_invalid_port_zero(self):
        assert parse_port(0) is None
        assert parse_port("0") is None

    def test_invalid_port_too_high(self):
        assert parse_port(MAX_TCP_PORT + 1) is None
        assert parse_port(100000) is None

    def test_invalid_port_negative(self):
        assert parse_port(-1) is None

    def test_invalid_port_non_numeric(self):
        assert parse_port("abc") is None
        assert parse_port(None) is None

    def test_invalid_port_bool(self):
        assert parse_port(True) is None
        assert parse_port(False) is None

    def test_max_tcp_port(self):
        assert MAX_TCP_PORT == 65535
