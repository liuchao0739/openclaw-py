from __future__ import annotations

from typing import Any

from .cli_constants import (
    CLAUDE_CLI_BACKEND_ID,
    CLAUDE_CLI_DEFAULT_ALLOWLIST_REFS,
    CLAUDE_CLI_DEFAULT_MODEL_REF,
    CLAUDE_CLI_MODEL_ALIASES,
    CLAUDE_CLI_SESSION_ID_FIELDS,
)
from .cli_shared import (
    CLAUDE_CLI_CLEAR_ENV,
    normalize_claude_backend_config,
    resolve_claude_cli_execution_args,
)


def build_anthropic_cli_backend() -> dict[str, Any]:
    return {
        "id": CLAUDE_CLI_BACKEND_ID,
        "modelProvider": "anthropic",
        "liveTest": {
            "defaultModelRef": CLAUDE_CLI_DEFAULT_MODEL_REF,
            "defaultImageProbe": True,
            "defaultMcpProbe": True,
            "docker": {
                "npmPackage": "@anthropic-ai/claude-code",
                "binaryName": "claude",
            },
        },
        "bundleMcp": True,
        "bundleMcpMode": "claude-config-file",
        "nativeToolMode": "always-on",
        "sideQuestionToolMode": "disabled",
        "ownsNativeCompaction": True,
        "config": {
            "command": "claude",
            "args": [
                "-p",
                "--output-format",
                "stream-json",
                "--include-partial-messages",
                "--verbose",
                "--setting-sources",
                "user",
                "--allowedTools",
                "mcp__openclaw__*",
                "--disallowedTools",
                "ScheduleWakeup,CronCreate,Bash(run_in_background:true),Monitor",
            ],
            "resumeArgs": [
                "-p",
                "--output-format",
                "stream-json",
                "--include-partial-messages",
                "--verbose",
                "--setting-sources",
                "user",
                "--allowedTools",
                "mcp__openclaw__*",
                "--disallowedTools",
                "ScheduleWakeup,CronCreate,Bash(run_in_background:true),Monitor",
                "--resume",
                "{sessionId}",
            ],
            "output": "jsonl",
            "liveSession": "claude-stdio",
            "input": "stdin",
            "modelArg": "--model",
            "modelAliases": CLAUDE_CLI_MODEL_ALIASES,
            "imageArg": "@",
            "imagePathScope": "workspace",
            "sessionArg": "--session-id",
            "sessionMode": "always",
            "reseedFromRawTranscriptWhenUncompacted": True,
            "sessionIdFields": list(CLAUDE_CLI_SESSION_ID_FIELDS),
            "systemPromptFileArg": "--append-system-prompt-file",
            "systemPromptMode": "append",
            "systemPromptWhen": "always",
            "clearEnv": list(CLAUDE_CLI_CLEAR_ENV),
            "reliability": {
                "watchdog": {
                    "fresh": {
                        "maxIdleMs": 300000,
                        "maxRuntimeMs": 1800000,
                        "maxStartupMs": 60000,
                    },
                    "resume": {
                        "maxIdleMs": 300000,
                        "maxRuntimeMs": 1800000,
                        "maxStartupMs": 120000,
                    },
                },
            },
            "serialize": True,
        },
        "normalizeConfig": normalize_claude_backend_config,
        "resolveExecutionArgs": resolve_claude_cli_execution_args,
    }