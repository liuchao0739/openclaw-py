"""Command-explainer formatting converts parsed executable spans into approval
UI highlight ranges, omitting shells whose parsing semantics differ.

Mirrors src/infra/command-explainer/format.ts. Self-contained port with
basic span validation.
"""

from __future__ import annotations

from typing import Any, Mapping

# POSIX shells that support command highlighting.
POSIX_SHELL_WRAPPERS = frozenset({"sh", "bash", "zsh", "dash", "ksh", "ash"})

# Shells whose parsing semantics differ and should be omitted from highlighting.
UNSUPPORTED_SHELLS = frozenset({"fish", "csh", "tcsh", "powershell", "pwsh", "cmd"})


def span_to_command_span(span: Mapping[str, Any]) -> dict[str, int] | None:
    """Convert a parsed span into an approval command span.

    Approval spans must be strict positive source ranges to avoid broken highlighting.
    """
    start = span.get("startIndex")
    end = span.get("endIndex")
    if not isinstance(start, int) or not isinstance(end, int):
        return None
    if isinstance(start, bool) or isinstance(end, bool):
        return None
    if start < 0 or end <= start:
        return None
    return {"startIndex": start, "endIndex": end}


def _is_unsupported_shell_wrapper_argv(argv: list[str]) -> bool:
    """Check if argv uses an unsupported shell wrapper."""
    if not argv:
        return False
    executable = argv[0]
    if not isinstance(executable, str):
        return False
    # Normalize: take basename
    normalized = executable.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
    return normalized in UNSUPPORTED_SHELLS


def _has_unsupported_shell_wrapper(explanation: Mapping[str, Any]) -> bool:
    commands = explanation.get("topLevelCommands", [])
    if not isinstance(commands, list):
        return False
    for command in commands:
        if isinstance(command, Mapping):
            argv = command.get("argv", [])
            if isinstance(argv, list) and _is_unsupported_shell_wrapper_argv(argv):
                return True
    return False


def format_command_spans(explanation: Mapping[str, Any]) -> list[dict[str, int]]:
    """Convert a parsed command explanation into source spans for approval UI."""
    if _has_unsupported_shell_wrapper(explanation):
        return []
    command_spans: list[dict[str, int]] = []
    top_level = explanation.get("topLevelCommands", [])
    nested = explanation.get("nestedCommands", [])
    if not isinstance(top_level, list):
        top_level = []
    if not isinstance(nested, list):
        nested = []
    for command in [*top_level, *nested]:
        if not isinstance(command, Mapping):
            continue
        span = command.get("executableSpan")
        if isinstance(span, Mapping):
            command_span = span_to_command_span(span)
            if command_span is not None:
                command_spans.append(command_span)
    return command_spans
