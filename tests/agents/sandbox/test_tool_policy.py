"""Sandbox tool policy resolver."""

from openclaw.agents.sandbox.tool_policy import (
    is_tool_allowed,
    resolve_sandbox_tool_policy_for_agent,
)


def test_default_deny_blocks_browser():
    policy = resolve_sandbox_tool_policy_for_agent()
    assert not is_tool_allowed({"allow": policy["allow"], "deny": policy["deny"]}, "browser")


def test_exec_allowed_by_default():
    policy = resolve_sandbox_tool_policy_for_agent()
    assert is_tool_allowed({"allow": policy["allow"], "deny": policy["deny"]}, "exec")


def test_bash_alias_exec():
    policy = resolve_sandbox_tool_policy_for_agent()
    assert is_tool_allowed({"allow": policy["allow"], "deny": policy["deny"]}, "bash")