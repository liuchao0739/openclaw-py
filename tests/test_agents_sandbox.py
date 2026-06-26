"""Tests for agents/sandbox modules."""

from openclaw.agents.sandbox import (
    hash_text_sha256,
    get_browser_bridges,
    register_browser_bridge,
    unregister_browser_bridge,
    clear_browser_bridges,
    find_docker_args_call,
    collect_docker_flag_values,
    parse_sandbox_stat_size,
    parse_sandbox_stat_mtime_ms,
)


class TestHash:
    def test_deterministic(self):
        assert hash_text_sha256("test") == hash_text_sha256("test")

    def test_different(self):
        assert hash_text_sha256("a") != hash_text_sha256("b")

    def test_hex(self):
        result = hash_text_sha256("hello")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


class TestBrowserBridges:
    def setup_method(self):
        clear_browser_bridges()

    def test_register_and_get(self):
        register_browser_bridge("s1", {"url": "ws://"}, "container1")
        bridges = get_browser_bridges()
        assert "s1" in bridges
        assert bridges["s1"]["containerName"] == "container1"

    def test_unregister(self):
        register_browser_bridge("s1", {}, "c1")
        unregister_browser_bridge("s1")
        assert "s1" not in get_browser_bridges()

    def test_unregister_missing(self):
        unregister_browser_bridge("nope")

    def test_with_auth(self):
        register_browser_bridge("s1", {}, "c1", auth_token="tok", auth_password="pass")
        b = get_browser_bridges()["s1"]
        assert b["authToken"] == "tok"
        assert b["authPassword"] == "pass"


class TestDockerArgs:
    def test_find_call(self):
        calls = [[["run", "--name", "x"]], [["build", "."]]]
        result = find_docker_args_call(calls, "run")
        assert result == ["run", "--name", "x"]

    def test_find_not_found(self):
        assert find_docker_args_call([[["build"]]], "run") is None

    def test_collect_flag_values(self):
        args = ["-e", "A=1", "-e", "B=2", "-v", "/host:/container"]
        envs = collect_docker_flag_values(args, "-e")
        assert envs == ["A=1", "B=2"]

    def test_collect_no_values(self):
        assert collect_docker_flag_values(["-e"], "-v") == []

    def test_collect_trailing_flag(self):
        assert collect_docker_flag_values(["-e", "A=1", "-e"], "-e") == ["A=1"]


class TestStatParse:
    def test_size_simple(self):
        assert parse_sandbox_stat_size("1024") == 1024

    def test_size_none(self):
        assert parse_sandbox_stat_size(None) == 0

    def test_size_empty(self):
        assert parse_sandbox_stat_size("") == 0

    def test_size_huge(self):
        result = parse_sandbox_stat_size("99999999999999999999999999")
        assert result == 9007199254740991

    def test_size_non_numeric(self):
        assert parse_sandbox_stat_size("abc") == 0

    def test_mtime_epoch(self):
        assert parse_sandbox_stat_mtime_ms("1700000000") == 1700000000000

    def test_mtime_epoch_decimal(self):
        assert parse_sandbox_stat_mtime_ms("1700000000.5") == 1700000000500

    def test_mtime_none(self):
        assert parse_sandbox_stat_mtime_ms(None) == 0

    def test_mtime_invalid(self):
        assert parse_sandbox_stat_mtime_ms("not-a-date") == 0
