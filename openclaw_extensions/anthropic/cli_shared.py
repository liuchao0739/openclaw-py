from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from openclaw.packages.normalization_core import (
    is_record,
    normalize_lowercase_string_or_empty,
    normalize_optional_lowercase_string,
)

from .cli_constants import (
    CLAUDE_CLI_BACKEND_ID,
    CLAUDE_CLI_DEFAULT_ALLOWLIST_REFS,
    CLAUDE_CLI_DEFAULT_MODEL_REF,
    CLAUDE_CLI_MODEL_ALIASES,
    CLAUDE_CLI_SESSION_ID_FIELDS,
)

CLAUDE_CLI_CLEAR_ENV = [
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_API_KEY_OLD",
    "ANTHROPIC_API_TOKEN",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_CUSTOM_HEADERS",
    "ANTHROPIC_OAUTH_TOKEN",
    "ANTHROPIC_UNIX_SOCKET",
    "CLAUDE_CONFIG_DIR",
    "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_OAUTH_REFRESH_TOKEN",
    "CLAUDE_CODE_OAUTH_SCOPES",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR",
    "CLAUDE_CODE_PLUGIN_CACHE_DIR",
    "CLAUDE_CODE_PLUGIN_SEED_DIR",
    "CLAUDE_CODE_REMOTE",
    "CLAUDE_CODE_USE_COWORK_PLUGINS",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_VERTEX",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_HEADERS",
    "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT",
    "OTEL_EXPORTER_OTLP_LOGS_HEADERS",
    "OTEL_EXPORTER_OTLP_LOGS_PROTOCOL",
    "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
    "OTEL_EXPORTER_OTLP_METRICS_HEADERS",
    "OTEL_EXPORTER_OTLP_METRICS_PROTOCOL",
    "OTEL_EXPORTER_OTLP_PROTOCOL",
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    "OTEL_EXPORTER_OTLP_TRACES_HEADERS",
    "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL",
    "OTEL_LOGS_EXPORTER",
    "OTEL_METRICS_EXPORTER",
    "OTEL_SDK_DISABLED",
    "OTEL_TRACES_EXPORTER",
]

_CLAUDE_LEGACY_SKIP_PERMISSIONS_ARG = "--dangerously-skip-permissions"
_CLAUDE_PERMISSION_MODE_ARG = "--permission-mode"
_CLAUDE_SETTING_SOURCES_ARG = "--setting-sources"
_CLAUDE_EFFORT_ARG = "--effort"
_CLAUDE_BARE_ARG = "--bare"
_CLAUDE_SAFE_MODE_ARG = "--safe-mode"
_CLAUDE_TOOLS_ARG = "--tools"
_CLAUDE_DISALLOWED_TOOLS_ARG = "--disallowedTools"
_CLAUDE_MCP_CONFIG_ARG = "--mcp-config"
_CLAUDE_STRICT_MCP_CONFIG_ARG = "--strict-mcp-config"
_CLAUDE_NO_SESSION_PERSISTENCE_ARG = "--no-session-persistence"
_CLAUDE_MAX_TURNS_ARG = "--max-turns"
_CLAUDE_SESSION_ID_ARG = "--session-id"
_CLAUDE_RESUME_ARG = "--resume"
_CLAUDE_RESUME_SESSION_AT_ARG = "--resume-session-at"
_CLAUDE_RESUME_SHORT_ARG = "-r"
_CLAUDE_CONTINUE_ARG = "--continue"
_CLAUDE_CONTINUE_SHORT_ARG = "-c"
_CLAUDE_FORK_SESSION_ARG = "--fork-session"
_CLAUDE_SAFE_SETTING_SOURCES = "user"
_CLAUDE_BYPASS_PERMISSION_MODE = "bypassPermissions"
_CLAUDE_DEFAULT_PERMISSION_MODE = "default"
_CLAUDE_NO_TOOLS_VALUE = ""
_CLAUDE_DENY_MCP_TOOLS_VALUE = "mcp__*"

CLAUDE_CLI_OFF_THINKING_PROFILE: dict[str, Any] = {
    "levels": [{"id": "off"}],
    "defaultLevel": "off",
}


def is_claude_cli_provider(provider_id: str) -> bool:
    return normalize_optional_lowercase_string(provider_id) == CLAUDE_CLI_BACKEND_ID


def _is_openclaw_requested_yolo(context: dict[str, Any] | None = None) -> bool:
    agent_exec = None
    if context and context.get("agentId"):
        agent_id = context.get("agentId")
        agents = context.get("config", {}).get("agents", {}).get("list", [])
        for agent in agents:
            if agent.get("id") == agent_id:
                agent_exec = agent.get("tools", {}).get("exec")
                break
    exec_cfg = agent_exec or (context or {}).get("config", {}).get("tools", {}).get("exec")
    security = (exec_cfg or {}).get("security", "full")
    ask = (exec_cfg or {}).get("ask", "off")
    return security == "full" and ask == "off"


def resolve_claude_permission_mode(
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if _is_openclaw_requested_yolo(context):
        return {"mode": _CLAUDE_BYPASS_PERMISSION_MODE, "overrideExisting": False}
    return {"overrideExisting": False}


def normalize_claude_permission_args(
    args: list[str] | None = None,
    options: dict[str, Any] | None = None,
) -> list[str] | None:
    if not args:
        if options and options.get("mode"):
            return [_CLAUDE_PERMISSION_MODE_ARG, options["mode"]]
        return args
    normalized: list[str] = []
    has_permission_mode = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == _CLAUDE_LEGACY_SKIP_PERMISSIONS_ARG:
            i += 1
            continue
        if arg == _CLAUDE_PERMISSION_MODE_ARG:
            maybe_value = args[i + 1] if i + 1 < len(args) else None
            if (
                isinstance(maybe_value, str)
                and maybe_value.strip()
                and not maybe_value.startswith("-")
            ):
                has_permission_mode = True
                if not options or not options.get("overrideExisting"):
                    normalized.append(arg)
                    normalized.append(maybe_value)
                i += 2
                continue
            i += 1
            continue
        if arg.startswith(f"{_CLAUDE_PERMISSION_MODE_ARG}="):
            maybe_value = arg[len(_CLAUDE_PERMISSION_MODE_ARG) + 1:].strip()
            if maybe_value and not maybe_value.startswith("-"):
                has_permission_mode = True
                if not options or not options.get("overrideExisting"):
                    normalized.append(
                        f"{_CLAUDE_PERMISSION_MODE_ARG}={maybe_value}"
                    )
            i += 1
            continue
        normalized.append(arg)
        i += 1
    if options and options.get("mode") and (
        not has_permission_mode or options.get("overrideExisting")
    ):
        normalized.append(_CLAUDE_PERMISSION_MODE_ARG)
        normalized.append(options["mode"])
    return normalized


def normalize_claude_setting_sources_args(
    args: list[str] | None = None,
) -> list[str] | None:
    if not args:
        return args
    normalized: list[str] = []
    has_setting_sources = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == _CLAUDE_SETTING_SOURCES_ARG:
            maybe_value = args[i + 1] if i + 1 < len(args) else None
            if (
                isinstance(maybe_value, str)
                and maybe_value.strip()
                and not maybe_value.startswith("-")
            ):
                has_setting_sources = True
                normalized.append(arg)
                normalized.append(_CLAUDE_SAFE_SETTING_SOURCES)
                i += 2
                continue
            i += 1
            continue
        if arg.startswith(f"{_CLAUDE_SETTING_SOURCES_ARG}="):
            has_setting_sources = True
            normalized.append(
                f"{_CLAUDE_SETTING_SOURCES_ARG}={_CLAUDE_SAFE_SETTING_SOURCES}"
            )
            i += 1
            continue
        normalized.append(arg)
        i += 1
    if not has_setting_sources:
        normalized.append(_CLAUDE_SETTING_SOURCES_ARG)
        normalized.append(_CLAUDE_SAFE_SETTING_SOURCES)
    return normalized


def map_claude_cli_thinking_level_to_effort(
    thinking_level: str | None = None,
) -> str | None:
    normalized = normalize_optional_lowercase_string(thinking_level)
    if normalized in ("minimal", "low"):
        return "low"
    if normalized in ("adaptive", "medium"):
        return "medium"
    if normalized == "high":
        return "high"
    if normalized == "xhigh":
        return "xhigh"
    if normalized == "max":
        return "max"
    return None


def _strip_claude_effort_args(args: list[str]) -> list[str]:
    normalized: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i] or ""
        if arg == _CLAUDE_EFFORT_ARG:
            maybe_value = args[i + 1] if i + 1 < len(args) else None
            if (
                isinstance(maybe_value, str)
                and maybe_value.strip()
                and not maybe_value.startswith("-")
            ):
                i += 2
                continue
            i += 1
            continue
        if arg.startswith(f"{_CLAUDE_EFFORT_ARG}="):
            i += 1
            continue
        normalized.append(arg)
        i += 1
    return normalized


_CLAUDE_SIDE_QUESTION_VARIADIC_VALUE_ARGS = {
    "--allowedTools",
    "--allowed-tools",
    _CLAUDE_DISALLOWED_TOOLS_ARG,
    "--disallowed-tools",
    _CLAUDE_TOOLS_ARG,
    _CLAUDE_MCP_CONFIG_ARG,
}

_CLAUDE_SIDE_QUESTION_VALUE_ARGS = {
    _CLAUDE_PERMISSION_MODE_ARG,
    _CLAUDE_SESSION_ID_ARG,
    _CLAUDE_RESUME_ARG,
    _CLAUDE_RESUME_SESSION_AT_ARG,
    _CLAUDE_RESUME_SHORT_ARG,
    _CLAUDE_MAX_TURNS_ARG,
}

_CLAUDE_SIDE_QUESTION_BARE_ARGS = {
    _CLAUDE_CONTINUE_ARG,
    _CLAUDE_CONTINUE_SHORT_ARG,
    _CLAUDE_FORK_SESSION_ARG,
    _CLAUDE_BARE_ARG,
    _CLAUDE_SAFE_MODE_ARG,
    _CLAUDE_STRICT_MCP_CONFIG_ARG,
    _CLAUDE_NO_SESSION_PERSISTENCE_ARG,
}


def _strip_claude_side_question_conflicting_args(args: list[str]) -> list[str]:
    normalized: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i] or ""
        equals_index = arg.find("=")
        arg_name = arg[:equals_index] if equals_index > 0 else arg
        if arg_name in _CLAUDE_SIDE_QUESTION_BARE_ARGS:
            i += 1
            continue
        if arg_name in _CLAUDE_SIDE_QUESTION_VARIADIC_VALUE_ARGS:
            if equals_index < 0:
                while i + 1 < len(args) and isinstance(args[i + 1], str) and not args[i + 1].startswith("-"):
                    i += 1
            i += 1
            continue
        if arg_name in _CLAUDE_SIDE_QUESTION_VALUE_ARGS:
            if equals_index < 0:
                maybe_value = args[i + 1] if i + 1 < len(args) else None
                if isinstance(maybe_value, str) and not maybe_value.startswith("-"):
                    i += 1
            i += 1
            continue
        normalized.append(arg)
        i += 1
    return normalized


def _resolve_claude_cli_side_question_execution_args(
    base_args: list[str],
) -> list[str]:
    return [
        *_strip_claude_side_question_conflicting_args(
            _strip_claude_effort_args(base_args)
        ),
        _CLAUDE_SAFE_MODE_ARG,
        _CLAUDE_TOOLS_ARG,
        _CLAUDE_NO_TOOLS_VALUE,
        _CLAUDE_DISALLOWED_TOOLS_ARG,
        _CLAUDE_DENY_MCP_TOOLS_VALUE,
        _CLAUDE_STRICT_MCP_CONFIG_ARG,
        _CLAUDE_NO_SESSION_PERSISTENCE_ARG,
        _CLAUDE_MAX_TURNS_ARG,
        "1",
        _CLAUDE_PERMISSION_MODE_ARG,
        _CLAUDE_DEFAULT_PERMISSION_MODE,
    ]


def resolve_claude_cli_execution_args(
    context: dict[str, Any],
) -> list[str]:
    if context.get("executionMode") == "side-question":
        return _resolve_claude_cli_side_question_execution_args(
            context.get("baseArgs", [])
        )
    effort = map_claude_cli_thinking_level_to_effort(
        context.get("thinkingLevel")
    )
    if not effort:
        return list(context.get("baseArgs", []))
    return [
        *_strip_claude_effort_args(context.get("baseArgs", [])),
        _CLAUDE_EFFORT_ARG,
        effort,
    ]


def normalize_claude_backend_config(
    config: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = config.get("output", "jsonl")
    input_val = config.get("input", "stdin")
    permission = resolve_claude_permission_mode(context)
    args = normalize_claude_permission_args(
        normalize_claude_setting_sources_args(config.get("args")),
        permission,
    )
    resume_args = normalize_claude_permission_args(
        normalize_claude_setting_sources_args(config.get("resumeArgs")),
        permission,
    )
    live_session = config.get("liveSession")
    if live_session is None and output == "jsonl" and input_val == "stdin":
        live_session = "claude-stdio"
    return {
        **config,
        "args": args,
        "resumeArgs": resume_args,
        "output": output,
        "liveSession": live_session,
        "input": input_val,
    }