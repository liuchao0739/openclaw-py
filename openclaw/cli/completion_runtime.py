from __future__ import annotations

from typing import Any


def resolve_completion_shell(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in ("bash", "zsh", "fish", "powershell"):
        return normalized
    return None


def generate_completion(program_name: str, shell: str) -> str:
    if shell == "fish":
        from openclaw.cli.completion_fish import generate_fish_completion
        return generate_fish_completion(program_name)
    return f"# Completion for {shell} not yet implemented"
