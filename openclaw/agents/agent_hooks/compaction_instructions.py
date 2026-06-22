"""Compaction instruction utilities."""

from __future__ import annotations

DEFAULT_COMPACTION_INSTRUCTIONS = (
    "Write the summary body in the primary language used in the conversation.\n"
    "Focus on factual content: what was discussed, decisions made, and current state.\n"
    "Keep the required summary structure and section headers unchanged.\n"
    "Do not translate or alter code, file paths, identifiers, or error messages."
)

MAX_INSTRUCTION_LENGTH = 800


def _truncate_unicode_safe(s: str, max_code_points: int) -> str:
    chars = list(s)
    if len(chars) <= max_code_points:
        return s
    return "".join(chars[:max_code_points])


def _normalize(s: str | None) -> str | None:
    if s is None:
        return None
    trimmed = s.strip()
    return trimmed if trimmed else None


def resolve_compaction_instructions(
    event_instructions: str | None,
    runtime_instructions: str | None,
) -> str:
    resolved = (
        _normalize(event_instructions)
        or _normalize(runtime_instructions)
        or DEFAULT_COMPACTION_INSTRUCTIONS
    )
    return _truncate_unicode_safe(resolved, MAX_INSTRUCTION_LENGTH)


def compose_split_turn_instructions(
    turn_prefix_instructions: str,
    resolved_instructions: str,
) -> str:
    return f"{turn_prefix_instructions}\n\nAdditional requirements:\n{resolved_instructions}"