"""Tests for embedded run failure signals (P2-0014)."""

from openclaw.agents.embedded_agent_runner.failure_signal import (
    resolve_embedded_run_failure_signal,
)


def test_cron_exec_denial():
    assert resolve_embedded_run_failure_signal(
        trigger="cron",
        last_tool_error={
            "toolName": "exec",
            "errorCode": "SYSTEM_RUN_DENIED",
            "error": "SYSTEM_RUN_DENIED: approval required",
        },
    ) == {
        "kind": "execution_denied",
        "source": "tool",
        "toolName": "exec",
        "code": "SYSTEM_RUN_DENIED",
        "message": "SYSTEM_RUN_DENIED: approval required",
        "fatalForCron": True,
    }


def test_invalid_request_bash():
    sig = resolve_embedded_run_failure_signal(
        trigger="cron",
        last_tool_error={
            "toolName": "bash",
            "errorCode": "INVALID_REQUEST",
            "error": "INVALID_REQUEST: approval denied",
        },
    )
    assert sig is not None
    assert sig["code"] == "INVALID_REQUEST"


def test_non_cron():
    assert (
        resolve_embedded_run_failure_signal(
            trigger="user",
            last_tool_error={
                "toolName": "exec",
                "errorCode": "SYSTEM_RUN_DENIED",
                "error": "SYSTEM_RUN_DENIED: approval required",
            },
        )
        is None
    )


def test_ordinary_exec_failure():
    assert (
        resolve_embedded_run_failure_signal(
            trigger="cron",
            last_tool_error={
                "toolName": "exec",
                "error": "/bin/bash: line 1: python: command not found",
            },
        )
        is None
    )


def test_non_exec_invalid_request():
    assert (
        resolve_embedded_run_failure_signal(
            trigger="cron",
            last_tool_error={
                "toolName": "browser",
                "errorCode": "INVALID_REQUEST",
                "error": "INVALID_REQUEST: url required",
            },
        )
        is None
    )


def test_error_text_without_code():
    assert (
        resolve_embedded_run_failure_signal(
            trigger="cron",
            last_tool_error={
                "toolName": "exec",
                "error": "The fetched page says SYSTEM_RUN_DENIED in its troubleshooting section.",
            },
        )
        is None
    )