"""Custom command config helpers normalize command configuration records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class CustomCommandIssue:
    index: int
    field: str
    message: str


@dataclass
class CustomCommandConfig:
    label: str
    pattern: re.Pattern
    pattern_description: str
    prefix: str = "/"


def _normalize_lowercase_or_empty(value: str) -> str:
    return value.strip().lower()


def normalize_slash_command_name(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return ""
    without_slash = trimmed[1:] if trimmed.startswith("/") else trimmed
    return _normalize_lowercase_or_empty(without_slash).replace("-", "_")


def normalize_command_description(value: str) -> str:
    return value.strip()


def resolve_custom_commands(
    commands: list[dict[str, Any]] | None,
    config: CustomCommandConfig,
    reserved_commands: set[str] | None = None,
    check_reserved: bool = True,
    check_duplicates: bool = True,
) -> tuple[list[dict[str, str]], list[CustomCommandIssue]]:
    if commands is None:
        commands = []
    if reserved_commands is None:
        reserved_commands = set()
    seen: set[str] = set()
    resolved: list[dict[str, str]] = []
    issues: list[CustomCommandIssue] = []
    label = config.label
    prefix = config.prefix

    for index, entry in enumerate(commands):
        normalized = normalize_slash_command_name(entry.get("command", ""))
        if not normalized:
            issues.append(CustomCommandIssue(
                index=index,
                field="command",
                message=f"{label} custom command is missing a command name.",
            ))
            continue
        if not config.pattern.match(normalized):
            issues.append(CustomCommandIssue(
                index=index,
                field="command",
                message=f'{label} custom command "{prefix}{normalized}" is invalid ({config.pattern_description}).',
            ))
            continue
        if check_reserved and normalized in reserved_commands:
            issues.append(CustomCommandIssue(
                index=index,
                field="command",
                message=f'{label} custom command "{prefix}{normalized}" conflicts with a native command.',
            ))
            continue
        if check_duplicates and normalized in seen:
            issues.append(CustomCommandIssue(
                index=index,
                field="command",
                message=f'{label} custom command "{prefix}{normalized}" is duplicated.',
            ))
            continue
        description = normalize_command_description(entry.get("description", ""))
        if not description:
            issues.append(CustomCommandIssue(
                index=index,
                field="description",
                message=f'{label} custom command "{prefix}{normalized}" is missing a description.',
            ))
            continue
        if check_duplicates:
            seen.add(normalized)
        resolved.append({"command": normalized, "description": description})

    return resolved, issues
