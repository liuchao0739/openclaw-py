"""Tests for cli/program — program context, routes, command tree."""

from __future__ import annotations

from openclaw.cli.program.command_tree import remove_command, remove_command_by_name
from openclaw.cli.program.program_context import get_program_context, set_program_context
from openclaw.cli.program.routes import RouteSpec, find_routed_command, register_route


class TestProgramContext:
    def test_set_and_get(self):
        program = type("Program", (), {})()
        ctx = {"agentId": "main"}
        set_program_context(program, ctx)
        assert get_program_context(program) is ctx

    def test_get_without_set(self):
        program = type("Program", (), {})()
        assert get_program_context(program) is None


class TestRoutes:
    def test_find_matching_route(self):
        route = RouteSpec(["gateway", "start"])
        register_route(route)
        result = find_routed_command(["gateway", "start"])
        assert result is route

    def test_find_no_match(self):
        result = find_routed_command(["unknown", "command"])
        assert result is None

    def test_find_with_can_run_check(self):
        route = RouteSpec(["test"], can_run=lambda argv: False)
        register_route(route)
        result = find_routed_command(["test"], ["arg1"])
        assert result is None  # can_run returns False

    def test_find_with_can_run_pass(self):
        route = RouteSpec(["test2"], can_run=lambda argv: True)
        register_route(route)
        result = find_routed_command(["test2"], ["arg1"])
        assert result is route


class TestCommandTree:
    def test_remove_command(self):
        cmd = type("Cmd", (), {"name": "test"})()
        program = type("Program", (), {"commands": [cmd]})()
        assert remove_command(program, cmd) is True
        assert cmd not in program.commands

    def test_remove_command_not_found(self):
        cmd = type("Cmd", (), {"name": "test"})()
        program = type("Program", (), {"commands": []})()
        assert remove_command(program, cmd) is False

    def test_remove_by_name(self):
        cmd = type("Cmd", (), {"name": lambda self: "test", "aliases": lambda self: ["t"]})()
        program = type("Program", (), {"commands": [cmd]})()
        assert remove_command_by_name(program, "test") is True
        assert cmd not in program.commands

    def test_remove_by_alias(self):
        cmd = type("Cmd", (), {"name": lambda self: "test", "aliases": lambda self: ["t"]})()
        program = type("Program", (), {"commands": [cmd]})()
        assert remove_command_by_name(program, "t") is True

    def test_remove_by_name_not_found(self):
        program = type("Program", (), {"commands": []})()
        assert remove_command_by_name(program, "nonexistent") is False
